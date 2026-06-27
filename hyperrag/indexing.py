"""Indexing orchestration for entity and hyperedge extraction."""

import asyncio
import re
import sys
from collections import defaultdict
from datetime import datetime

from .base import BaseHypergraphStorage, BaseVectorStorage, TextChunkSchema
from .extraction import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction_high,
    _handle_single_relationship_extraction_low,
)
from .graph_upsert import _merge_edges_then_upsert, _merge_nodes_then_upsert
from .prompt import PROMPTS
from .utils import (
    compute_mdhash_id,
    logger,
    pack_user_ass_to_openai_messages,
    split_string_by_multi_markers,
)


async def extract_entities(
    chunks: dict[str, TextChunkSchema],
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict,
) -> BaseHypergraphStorage | None:
    """建库阶段的实体/超边抽取总入口。

    对每个 chunk：
    1. 用 LLM 按 prompt 抽 Entity、Low-order Hyperedge、High-order Hyperedge。
    2. 解析 LLM 输出记录。
    3. 合并同名实体、同 id_set 关系。
    4. 写入 HypergraphDB，并把实体/关系描述写入向量库。
    """
    use_llm_func: callable = global_config["llm_model_func"]
    entity_extract_max_gleaning = global_config["entity_extract_max_gleaning"]

    ordered_chunks = list(chunks.items())

    entity_extract_prompt = PROMPTS["entity_extraction"]
    # We can choose the example what we want from the prompt.
    example_base = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"]
    )
    example_prompt = PROMPTS["entity_extraction_examples"][3]
    example_str = example_prompt.format(**example_base)

    context_base = dict(
        language=PROMPTS["DEFAULT_LANGUAGE"],
        entity_types=",".join(PROMPTS["DEFAULT_ENTITY_TYPES"]),
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        examples = example_str
    )
    continue_prompt = PROMPTS["entity_continue_extraction"]
    if_loop_prompt = PROMPTS["entity_if_loop_extraction"]

    already_processed = 0
    already_entities = 0
    already_relations = 0
    already_relations_low = 0
    already_relations_high = 0

    async def _process_single_content(chunk_key_dp: tuple[str, TextChunkSchema]):
        nonlocal already_processed, already_entities, already_relations, already_relations_low, already_relations_high
        chunk_key = chunk_key_dp[0]
        chunk_dp = chunk_key_dp[1]
        content = chunk_dp["content"]
        hint_prompt = entity_extract_prompt.format(**context_base, input_text=content)

        final_result = await use_llm_func(hint_prompt)
        if final_result is None:
            return None,None,None,None

        history = pack_user_ass_to_openai_messages(hint_prompt, final_result)
        for now_glean_index in range(entity_extract_max_gleaning):
            glean_result = await use_llm_func(continue_prompt, history_messages=history)
            if glean_result is None:
                break

            history += pack_user_ass_to_openai_messages(continue_prompt, glean_result)
            final_result += glean_result
            if now_glean_index == entity_extract_max_gleaning - 1:
                break

            if_loop_result: str = await use_llm_func(
                if_loop_prompt, history_messages=history
            )
            if_loop_result = if_loop_result.strip().strip('"').strip("'").lower()
            if if_loop_result != "yes":
                break

        records = split_string_by_multi_markers(
            final_result,
            [context_base["record_delimiter"], context_base["completion_delimiter"]],
        )

        maybe_nodes = defaultdict(list)
        maybe_edges = defaultdict(list)
        maybe_edges_low = defaultdict(list)
        maybe_edges_high = defaultdict(list)
        for record in records:
            record = re.search(r"\((.*)\)", record)
            if record is None:
                continue
            record = record.group(1)
            record_attributes = split_string_by_multi_markers(
                record, [context_base["tuple_delimiter"]]
            )
            if_entities = await _handle_single_entity_extraction(
                record_attributes, chunk_key
            )
            if if_entities is not None:
                maybe_nodes[if_entities["entity_name"]].append(if_entities)
                continue

            if_relation = await _handle_single_relationship_extraction_low(
                record_attributes, chunk_key
            )
            if if_relation is not None:
                maybe_edges[tuple((if_relation["entityN"]))].append(
                    if_relation
                )
                maybe_edges_low[tuple((if_relation["entityN"]))].append(
                    if_relation
                )

            if_relation = await _handle_single_relationship_extraction_high(
                record_attributes, chunk_key
            )
            if if_relation is not None:
                maybe_edges[tuple((if_relation["entityN"]))].append(
                    if_relation
                )
                maybe_edges_high[tuple((if_relation["entityN"]))].append(
                    if_relation
                )

        already_processed += 1
        already_entities += len(maybe_nodes)
        already_relations += len(maybe_edges)
        already_relations_low += len(maybe_edges_low)
        already_relations_high += len(maybe_edges_high)
        # ASCII-only progress (Windows cp936/gbk consoles cannot print Braille/spinner glyphs)
        spinner = "|/-\\"[already_processed % 4]

        # 计算用时
        current_time = datetime.now()
        time = current_time - begin_time
        total_seconds = int(time.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        # 进度条
        percent = (already_processed / len(ordered_chunks)) * 100
        bar_length = int(50 * already_processed // len(ordered_chunks))
        bar = "#" * bar_length + "-" * (50 - bar_length)
        sys.stdout.write(
            f'\n\r|{bar}| {percent:.2f}% |{hours:02}:{minutes:02}:{seconds:02}| {spinner} Processed, {already_entities} entities, {already_relations} relations, {already_relations_low} relations_low, {already_relations_high} relations_high \n')
        sys.stdout.flush()
        return dict(maybe_nodes), dict(maybe_edges), dict(maybe_edges_low), dict(maybe_edges_high)

    # ----------------------------------------------------------------------------
    # use_llm_func is wrapped in ascynio.Semaphore, limiting max_async callings
    begin_time = datetime.now()
    results = await asyncio.gather(
        *[_process_single_content(c) for c in ordered_chunks ]
    )

    # print()  # clear the progress bar
    maybe_nodes = defaultdict(list)
    maybe_edges = defaultdict(list)
    high = defaultdict(list)
    low = defaultdict(list)
    for m_nodes, m_edges, low_edge, high_edge in results:
        if m_nodes is not None:
            for k, v in m_nodes.items():
                maybe_nodes[k].extend(v)
        if m_edges is not None:
            for k, v in m_edges.items():
                maybe_edges[tuple(sorted(k))].extend(v)
        if low_edge is not None:
            for k, v in low_edge.items():
                low[tuple(sorted(k))].extend(v)
        if high_edge is not None:
            for k, v in high_edge.items():
                high[tuple(sorted(k))].extend(v)
        if m_nodes is None or m_edges is None or low_edge is None or high_edge is None:
            print("extract a element that is None")
    # ----------------------------------------------------------------------------
    """
        update the hypergraph database
    """
    all_entities_data = await asyncio.gather(
        *[
            _merge_nodes_then_upsert(k, v, knowledge_hypergraph_inst, global_config)
            for k, v in maybe_nodes.items()
        ]
    )

    all_relationships_data = await asyncio.gather(
        *[
            _merge_edges_then_upsert(k, v, knowledge_hypergraph_inst, global_config)
            for k, v in maybe_edges.items()
        ]
    )
    if not len(all_entities_data):
        logger.warning("Didn't extract any entities, maybe your LLM is not working")
        return None
    if not len(all_relationships_data):
        logger.warning(
            "Didn't extract any relationships, maybe your LLM is not working"
        )
        return None

    if entity_vdb is not None:
        data_for_vdb = {
            compute_mdhash_id(dp["entity_name"], prefix="ent-"): {
                "content": dp["entity_name"] + dp["description"],
                "entity_name": dp["entity_name"],
            }
            for dp in all_entities_data
        }
        await entity_vdb.upsert(data_for_vdb)

    if relationships_vdb is not None:
        data_for_vdb = {
            compute_mdhash_id(str(sorted(dp["id_set"])), prefix="rel-"): {
                "id_set": dp["id_set"],
                "content": dp["keywords"]
                           + str(dp["id_set"])
                           + dp["description"],
            }
            for dp in all_relationships_data
        }
        await relationships_vdb.upsert(data_for_vdb)

    return knowledge_hypergraph_inst
