import sys
import asyncio
import json
import re
from datetime import datetime
from typing import Union
from collections import Counter, defaultdict
import warnings


from .utils import (
    logger,
    clean_str,
    compute_mdhash_id,
    decode_tokens_by_tiktoken,
    encode_string_by_tiktoken,
    is_float_regex,
    list_of_list_to_csv,
    pack_user_ass_to_openai_messages,
    split_string_by_multi_markers,
    truncate_list_by_token_size,
    process_combine_contexts,
    deduplicate_by_key,
)
from .base import (
    BaseKVStorage,
    BaseVectorStorage,
    TextChunkSchema,
    QueryParam, BaseHypergraphStorage,
)

from .prompt import GRAPH_FIELD_SEP, PROMPTS

def chunking_by_token_size(
    content: str, overlap_token_size=128, max_token_size=1024, tiktoken_model="gpt-4o"
):
    tokens = encode_string_by_tiktoken(content, model_name=tiktoken_model)
    results = []
    for index, start in enumerate(
        range(0, len(tokens), max_token_size - overlap_token_size)
    ):
        chunk_content = decode_tokens_by_tiktoken(
            tokens[start : start + max_token_size], model_name=tiktoken_model
        )
        results.append(
            {
                "tokens": min(max_token_size, len(tokens) - start),
                "content": chunk_content.strip(),
                "chunk_order_index": index,
            }
        )
    return results

# summarize the descriptions of the entity
async def _handle_entity_summary(
    entity_or_relation_name: str,
    description: str,
    global_config: dict,
) -> str:
    use_llm_func: callable = global_config["llm_model_func"]
    llm_max_tokens = global_config["llm_model_max_token_size"]
    tiktoken_model_name = global_config["tiktoken_model_name"]
    summary_max_tokens = global_config["entity_summary_to_max_tokens"] # 500

    tokens = encode_string_by_tiktoken(description, model_name=tiktoken_model_name)
    if len(tokens) < summary_max_tokens:  # No need for summary
        return description
    prompt_template = PROMPTS["summarize_entity_descriptions"]
    use_description = decode_tokens_by_tiktoken(
        tokens[:llm_max_tokens], model_name=tiktoken_model_name
    )
    context_base = dict(
        entity_name=entity_or_relation_name,
        description_list=use_description.split(GRAPH_FIELD_SEP),
    )
    use_prompt = prompt_template.format(**context_base)
    logger.debug(f"Trigger summary: {entity_or_relation_name}")
    summary = await use_llm_func(use_prompt, max_tokens=summary_max_tokens)
    if summary is None:
        print("entity description summary not found")
        summary = use_description
    return summary

# summarize the additional properties of the entity
async def _handle_entity_additional_properties(
    entity_name: str,
    additional_properties: str,
    global_config: dict,
) -> str:
    use_llm_func: callable = global_config["llm_model_func"]
    llm_max_tokens = global_config["llm_model_max_token_size"]
    tiktoken_model_name = global_config["tiktoken_model_name"]
    summary_max_tokens = global_config["entity_additional_properties_to_max_tokens"] # 可能需要修改 entity_properties_summary_to_max_tokens

    tokens = encode_string_by_tiktoken(additional_properties, model_name=tiktoken_model_name)
    if len(tokens) < summary_max_tokens:  # No need for summary
        return additional_properties
    prompt_template = PROMPTS["summarize_entity_additional_properties"]
    use_additional_properties = decode_tokens_by_tiktoken(
        tokens[:llm_max_tokens], model_name=tiktoken_model_name
    )
    context_base = dict(
        entity_name=entity_name,
        additional_properties_list=use_additional_properties.split(GRAPH_FIELD_SEP),
    )
    use_prompt = prompt_template.format(**context_base)
    logger.debug(f"Trigger summary: {entity_name}")
    summary = await use_llm_func(use_prompt, max_tokens=summary_max_tokens)
    if summary is None:
        print("entity additional_properties summary not found")
        summary = use_additional_properties
    return summary

# summarize the descriptions of the relation
async def _handle_relation_summary(
    relation_name: str,
    description: str,
    global_config: dict,
) -> str:
    use_llm_func: callable = global_config["llm_model_func"]
    llm_max_tokens = global_config["llm_model_max_token_size"]
    tiktoken_model_name = global_config["tiktoken_model_name"]
    summary_max_tokens = global_config["relation_summary_to_max_tokens"]  # 可能需要修改  relation_summary_to_max_tokens

    tokens = encode_string_by_tiktoken(description, model_name=tiktoken_model_name)
    if len(tokens) < summary_max_tokens:  # No need for summary
        return description
    prompt_template = PROMPTS["summarize_relation_descriptions"]
    use_description = decode_tokens_by_tiktoken(
        tokens[:llm_max_tokens], model_name=tiktoken_model_name
    )
    context_base = dict(
        relation_name=relation_name,
        relation_description_list=use_description.split(GRAPH_FIELD_SEP),
    )
    use_prompt = prompt_template.format(**context_base)
    logger.debug(f"Trigger summary: {relation_name}")
    summary = await use_llm_func(use_prompt, max_tokens=summary_max_tokens)
    if summary is None:
        print("relation description summary not found")
        summary = use_description
    return summary

# summarize the keywords of the relation
async def _handle_relation_keywords_summary(
    relation_name: str,
    keywords: str,
    global_config: dict,
) -> str:
    use_llm_func: callable = global_config["llm_model_func"]
    llm_max_tokens = global_config["llm_model_max_token_size"]
    tiktoken_model_name = global_config["tiktoken_model_name"]
    summary_max_tokens = global_config["relation_keywords_to_max_tokens"]  # 可能需要修改relation_keywords_summary_to_max_tokens

    tokens = encode_string_by_tiktoken(keywords, model_name=tiktoken_model_name)
    if len(tokens) < summary_max_tokens:  # No need for summary
        return keywords
    prompt_template = PROMPTS["summarize_relation_keywords"]
    use_keywords = decode_tokens_by_tiktoken(
        tokens[:llm_max_tokens], model_name=tiktoken_model_name
    )
    context_base = dict(
        relation_name=relation_name,
        keywords_list=use_keywords.split(GRAPH_FIELD_SEP),
    )
    use_prompt = prompt_template.format(**context_base)
    logger.debug(f"Trigger summary: {relation_name}")
    summary = await use_llm_func(use_prompt, max_tokens=summary_max_tokens)
    if summary is None:
        print("relation keywords summary not found")
        summary = use_keywords
    return summary

async def _handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    if len(record_attributes) < 4 or record_attributes[0] != '"Entity"' :
        return None
    # add this record as a node in the G
    entity_name = clean_str(record_attributes[1].upper())
    if not entity_name.strip():
        return None
    entity_type = clean_str(record_attributes[2].upper())
    entity_description = clean_str(record_attributes[3])
    entity_source_id = chunk_key
    entity_additional_properties = clean_str(record_attributes[4:])

    return dict(
        entity_name=entity_name,
        entity_type=entity_type,
        description=entity_description,
        source_id=entity_source_id,
        additional_properties=entity_additional_properties,
    )


async def _handle_single_relationship_extraction_low(
    record_attributes: list[str],
    chunk_key: str,
):
    if len(record_attributes) < 6 or record_attributes[0] != '"Low-order Hyperedge"':
        return None
    # add this record as hyperedge
    entity_num = len(record_attributes) - 3
    entities = []
    for i in range(1, entity_num):
        entities.append(clean_str(record_attributes[i].upper()))
    edge_description = clean_str(record_attributes[-3])

    edge_keywords = clean_str(record_attributes[-2])
    edge_source_id = chunk_key
    weight = (
        float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 0.75 # 如果无权重，则默认0.75
    )
    return dict(
        entityN=entities,
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=edge_source_id,
        level_hg="Low-order Hyperedge",
    )

async def _handle_single_relationship_extraction_high(
    record_attributes: list[str],
    chunk_key: str,
):
    if len(record_attributes) < 7 or record_attributes[0] != '"High-order Hyperedge"':
        return None
    # add this record as hyperedge
    entity_num = len(record_attributes) - 4
    entities = []
    for i in range(1, entity_num):
        entities.append(clean_str(record_attributes[i].upper()))
    edge_description = clean_str(record_attributes[-4])
    edge_keywords = clean_str(record_attributes[-2])
    edge_source_id = chunk_key
    weight = (
        float(record_attributes[-1]) if is_float_regex(record_attributes[-1]) else 0.75
    )
    return dict(
        entityN=entities,
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=edge_source_id,
        level_hg="High-order Hyperedge",
    )


async def _merge_nodes_then_upsert(
    entity_name: str,
    nodes_data: list[dict],
    knowledge_hypergraph_inst,
    global_config: dict,
):
    already_entity_types = []
    already_source_ids = []
    already_description = []
    already_additional_properties = []

    already_node = await knowledge_hypergraph_inst.get_vertex(entity_name)
    if already_node is not None:
    #     """------------------------------------------------------------------"""
    #     if already_node["entity_type"] is None:
    #         print(f"The entity_type of {already_node['entity_name']} is None")
    #     if already_node["description"] is None:
    #         print(f"The description of {already_node['entity_name']} is None")
    #     if already_node["additional_properties"] is None:
    #         print(f"The additional_properties of {already_node['entity_name']} is None")
    #     """------------------------------------------------------------------"""
        already_entity_types.append(already_node["entity_type"])
        already_source_ids.extend(
            split_string_by_multi_markers(already_node["source_id"], [GRAPH_FIELD_SEP])
        )
        already_description.append(already_node["description"])
        already_additional_properties.append(already_node["additional_properties"])

    entity_type = sorted(
        Counter(
            [dp["entity_type"] for dp in nodes_data] + already_entity_types
        ).items(),
        key=lambda x: x[1],
        reverse=True,
    )[0][0]
    # """------------------------------------------------------------------"""
    # for node in nodes_data:
    #     if node["entity_type"] is None:
    #         print(f"The entity_type of {entity_name} is None")
    #     if node["description"] is None:
    #         print(f"The description of {entity_name} is None")
    #     if node["additional_properties"] is None:
    #         print(f"The additional_properties of {entity_name} is None")
    # """------------------------------------------------------------------"""

    # nodes_data = [dp["description"] for dp in nodes_data if dp["description"] is not None]
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in nodes_data] + already_description))
    )
    additional_properties = GRAPH_FIELD_SEP.join(
        sorted(set(
            prop
            for dp in nodes_data
            for prop in dp["additional_properties"]
        ) | set(already_additional_properties))
    )
    source_id = GRAPH_FIELD_SEP.join(
        set([dp["source_id"] for dp in nodes_data] + already_source_ids)
    )
    description = await _handle_entity_summary(
        entity_name, description, global_config
    )
    additional_properties = await _handle_entity_additional_properties(  # 应该新建一个合并附属信息的函数，以及prompt
        entity_name, additional_properties, global_config
    )
    node_data = dict(
        entity_type=entity_type,
        description=description,
        source_id=source_id,
        additional_properties=additional_properties,
    )
    await knowledge_hypergraph_inst.upsert_vertex(
        entity_name,
        node_data,
    )
    node_data["entity_name"] = entity_name
    return node_data


async def _merge_edges_then_upsert(
    id_set: tuple,
    edges_data: list[dict],
    knowledge_hypergraph_inst,
    global_config: dict,
):
    already_weights = []
    already_source_ids = []
    already_description = []
    already_keywords = []

    if await knowledge_hypergraph_inst.has_hyperedge(id_set):
        already_edge = await knowledge_hypergraph_inst.get_hyperedge(id_set)
        already_weights.append(already_edge["weight"])
        already_source_ids.extend(
            split_string_by_multi_markers(already_edge["source_id"], [GRAPH_FIELD_SEP])
        )
        already_description.append(already_edge["description"])
        already_keywords.extend(
            split_string_by_multi_markers(already_edge["keywords"], [GRAPH_FIELD_SEP])
        )

    weight = sum([dp["weight"] for dp in edges_data] + already_weights)
    description = GRAPH_FIELD_SEP.join(
        sorted(set([dp["description"] for dp in edges_data] + already_description))
    )
    keywords = GRAPH_FIELD_SEP.join(
        sorted(set([dp["keywords"] for dp in edges_data] + already_keywords))
    )
    source_id = GRAPH_FIELD_SEP.join(
        set([dp["source_id"] for dp in edges_data] + already_source_ids)
    )

    for need_insert_id in id_set:
        if not (await knowledge_hypergraph_inst.has_vertex(need_insert_id)):
            await knowledge_hypergraph_inst.upsert_vertex(
                need_insert_id,
                {
                    "source_id": source_id,
                    "description": "UNKNOWN", # 超边描述
                    "additional_properties": "UNKNOWN", # 超边关键词
                    "entity_type": "UNKNOWN",
                },
            )
    description = await _handle_relation_summary(  # 应该重新写一个针对超边描述进行合并的函数
        id_set, description, global_config
    )

    filter_keywords = await _handle_relation_keywords_summary(  # 应该重新写一个针对超边的关键词进行合并的函数
        id_set, keywords, global_config
    )

    await knowledge_hypergraph_inst.upsert_hyperedge(
        id_set,
        dict(
            description=description,
            keywords=filter_keywords,
            source_id=source_id,
            weight=weight
        ),
    )

    edge_data = dict(
        id_set=id_set,
        description=description,
        keywords=filter_keywords,
    )

    return edge_data


async def extract_entities(
    chunks: dict[str, TextChunkSchema],
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entity_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    global_config: dict,
) -> BaseHypergraphStorage | None:
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
        now_ticks = PROMPTS["process_tickers"][
            already_processed % len(PROMPTS["process_tickers"])
        ]

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
        bar = '█' * bar_length + '-' * (50 - bar_length)
        sys.stdout.write(
            f'\n\r|{bar}| {percent:.2f}% |{hours:02}:{minutes:02}:{seconds:02}| {now_ticks} Processed, {already_entities} entities, {already_relations} relations, {already_relations_low} relations_low, {already_relations_high} relations_high \n')
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


async def _build_entity_query_context(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
):
    results = await entities_vdb.query(query, top_k=query_param.top_k)
    if not len(results):
        return None
    node_datas = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_vertex(r["entity_name"]) for r in results]
    )

    if not all([n is not None for n in node_datas]):
        logger.warning("Some nodes are missing, maybe the storage is damaged")
    node_degrees = await asyncio.gather(
        *[knowledge_hypergraph_inst.vertex_degree(r["entity_name"]) for r in results]
    )

    node_datas = [
        {**n, "entity_name": k["entity_name"], "rank": d}
        for k, n, d in zip(results, node_datas, node_degrees)
        if n is not None
    ]

    use_text_units = await _find_most_related_text_unit_from_entities(
        node_datas, query_param, text_chunks_db, knowledge_hypergraph_inst
    )

    use_relations = await _find_most_related_edges_from_entities(
        node_datas, query_param, knowledge_hypergraph_inst
    )

    logger.info(
        f"entity query uses {len(node_datas)} entites, {len(use_relations)} relations, {len(use_text_units)} text units"
    )
    entities_section_list = [["id", "entity", "type", "description", "additional properties", "rank"]]
    for i, n in enumerate(node_datas):
        entities_section_list.append(
            [
                i,
                n["entity_name"],
                n.get("entity_type", "UNKNOWN"),
                n.get("description", "UNKNOWN"),
                n.get("additional_properties", "UNKNOWN"),
                n["rank"],
            ]
        )

    entities_context = list_of_list_to_csv(entities_section_list)

    relations_section_list = [
        ["id", "entity set", "description", "keywords", "weight", "rank"]
    ]
    for i, e in enumerate(use_relations):
        relations_section_list.append(
            [
                i,
                e["src_tgt"],
                e["description"],
                e["keywords"],
                e["weight"],
                e["rank"],
            ]
        )

    relations_context = list_of_list_to_csv(relations_section_list)

    text_units_section_list = [["id", "content"]]
    for i, t in enumerate(use_text_units):
        text_units_section_list.append([i, t["content"]])
    text_units_context = list_of_list_to_csv(text_units_section_list)

    context_string = f"""
-----Entities-----
```csv
{entities_context}
```
-----Relationships-----
```csv
{relations_context}
```
-----Sources-----
```csv
{text_units_context}
```
"""
    
    # 返回包含上下文字符串和结构化数据的字典
    return {
        "context": context_string,
        "entities": [
            {
                "id": i,
                "entity_name": n["entity_name"],
                "entity_type": n.get("entity_type", "UNKNOWN"),
                "description": n.get("description", "UNKNOWN"),
                "additional_properties": n.get("additional_properties", "UNKNOWN"),
                "rank": n["rank"]
            }
            for i, n in enumerate(node_datas)
        ],
        "hyperedges": [
            {
                "id": i,
                "entity_set": e["src_tgt"],
                "description": e["description"],
                "keywords": e["keywords"],
                "weight": e["weight"],
                "rank": e["rank"]
            }
            for i, e in enumerate(use_relations)
        ],
        "text_units": [
            {
                "id": i,
                "content": t["content"]
            }
            for i, t in enumerate(use_text_units)
        ]
    }



async def _find_most_related_text_unit_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    knowledge_hypergraph_inst: BaseHypergraphStorage,
):
    text_units = [
        split_string_by_multi_markers(dp["source_id"], [GRAPH_FIELD_SEP])
        for dp in node_datas
    ]

    edges = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_nbr_e_of_vertex(dp['entity_name']) for dp in node_datas]
    )

    all_one_hop_nodes = set()
    for this_edges in edges:
        if not this_edges:
            continue
        all_one_hop_nodes.update([e for e in this_edges])

    all_one_hop_nodes = list(all_one_hop_nodes)
    all_one_hop_nodes_data = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_vertex(e) for e in all_one_hop_nodes]
    )
    
    # Add null check for node data
    all_one_hop_text_units_lookup = {
        k: set(split_string_by_multi_markers(v["source_id"], [GRAPH_FIELD_SEP]))
        for k, v in zip(all_one_hop_nodes, all_one_hop_nodes_data)
        if v is not None and "source_id" in v  # Add source_id check
    }

    all_text_units_lookup = {}
    for index, (this_text_units, this_edges) in enumerate(zip(text_units, edges)):
        for c_id in this_text_units:
            if c_id in all_text_units_lookup:
                continue
            relation_counts = 0
            if this_edges:  # Add check for None edges
                for e in this_edges:
                    if (
                        e in all_one_hop_text_units_lookup
                        and c_id in all_one_hop_text_units_lookup[e]
                    ):
                        relation_counts += 1
            
            chunk_data = await text_chunks_db.get_by_id(c_id)
            if chunk_data is not None and "content" in chunk_data:  # Add content check
                all_text_units_lookup[c_id] = {
                    "data": chunk_data,
                    "order": index,
                    "relation_counts": relation_counts,
                }

    # Filter out None values and ensure data has content
    all_text_units = [
        {"id": k, **v} 
        for k, v in all_text_units_lookup.items() 
        if v is not None and v.get("data") is not None and "content" in v["data"]
    ]

    if not all_text_units:
        logger.warning("No valid text units found")
        return []

    all_text_units = sorted(
        all_text_units, 
        key=lambda x: (x["order"], -x["relation_counts"])
    )

    all_text_units = truncate_list_by_token_size(
        all_text_units,
        key=lambda x: x["data"]["content"],
        max_token_size=query_param.max_token_for_text_unit,
    )

    all_text_units = [t["data"] for t in all_text_units]
    return all_text_units


async def _find_most_related_edges_from_entities(
    node_datas: list[dict],
    query_param: QueryParam,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
):
    all_related_edges = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_nbr_e_of_vertex(dp['entity_name']) for dp in node_datas]
    )

    all_edges = set()
    for this_edges in all_related_edges:
        all_edges.update([tuple(sorted(e)) for e in this_edges])
    all_edges = list(all_edges)
    all_edges_pack = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_hyperedge(e) for e in all_edges]
    )

    all_edges_degree = await asyncio.gather(
        *[knowledge_hypergraph_inst.hyperedge_degree(e) for e in all_edges]
    )
    all_edges_data = [
        {"src_tgt": k, "rank": d, **v}
        for k, v, d in zip(all_edges, all_edges_pack, all_edges_degree)
        if v !=[]
    ]

    all_edges_data = sorted(
        all_edges_data, key=lambda x: (x["rank"], x["weight"]), reverse=True
    )
    all_edges_data = truncate_list_by_token_size(
        all_edges_data,
        key=lambda x: x["description"],
        max_token_size=query_param.max_token_for_relation_context,
    )
    return all_edges_data


async def _build_relation_query_context(
    keywords,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
):
    results = await relationships_vdb.query(keywords, top_k=query_param.top_k)

    if not len(results):
        return None

    edge_datas = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_hyperedge(r['id_set']) for r in results]
    )

    if not all([n is not None for n in edge_datas]):
        logger.warning("Some edges are missing, maybe the storage is damaged")
    edge_degree = await asyncio.gather(
        *[knowledge_hypergraph_inst.hyperedge_degree(e['id_set']) for e in results]
    )

    edge_datas = [
        {"id_set": k["id_set"], "rank": d, **v}
        for k, v, d in zip(results, edge_datas, edge_degree)
        if v is not None
    ]
    edge_datas = sorted(
        edge_datas, key=lambda x: (x["rank"], x["weight"]), reverse=True
    )
    edge_datas = truncate_list_by_token_size(
        edge_datas,
        key=lambda x: x["description"],
        max_token_size=query_param.max_token_for_relation_context,
    )

    use_entities = await _find_most_related_entities_from_relationships(
        edge_datas, query_param, knowledge_hypergraph_inst
    )
    use_text_units = await _find_related_text_unit_from_relationships(
        edge_datas, query_param, text_chunks_db, knowledge_hypergraph_inst
    )
    logger.info(
        f"relation query uses {len(use_entities)} entites, {len(edge_datas)} relations, {len(use_text_units)} text units"
    )
    relations_section_list = [
        ["id", "entity set", "description", "keywords", "weight", "rank"]
    ]
    for i, e in enumerate(edge_datas):
        relations_section_list.append(
            [
                i,
                e["id_set"],
                e["description"],
                e["keywords"],
                e["weight"],
                e["rank"],
            ]
        )
    relations_context = list_of_list_to_csv(relations_section_list)

    entites_section_list = [["id", "entity", "type", "description", "additional properties", "rank"]]
    for i, n in enumerate(use_entities):
        entites_section_list.append(
            [
                i,
                n["entity_name"],
                n.get("entity_type", "UNKNOWN"),
                n.get("description", "UNKNOWN"),
                n.get("additional properties", "UNKNOWN"),
                n["rank"],
            ]
        )
    entities_context = list_of_list_to_csv(entites_section_list)

    text_units_section_list = [["id", "content"]]
    for i, t in enumerate(use_text_units):
        text_units_section_list.append([i, t["content"]])
    text_units_context = list_of_list_to_csv(text_units_section_list)

    context_string = f"""
-----Entities-----
```csv
{entities_context}
```
-----Relationships-----
```csv
{relations_context}
```
-----Sources-----
```csv
{text_units_context}
```
"""

    # 返回包含上下文字符串和结构化数据的字典
    return {
        "context": context_string,
        "entities": [
            {
                "id": i,
                "entity_name": n["entity_name"],
                "entity_type": n.get("entity_type", "UNKNOWN"),
                "description": n.get("description", "UNKNOWN"),
                "additional_properties": n.get("additional properties", "UNKNOWN"),
                "rank": n["rank"]
            }
            for i, n in enumerate(use_entities)
        ],
        "hyperedges": [
            {
                "id": i,
                "entity_set": e["id_set"],
                "description": e["description"],
                "keywords": e["keywords"],
                "weight": e["weight"],
                "rank": e["rank"]
            }
            for i, e in enumerate(edge_datas)
        ],
        "text_units": [
            {
                "id": i,
                "content": t["content"]
            }
            for i, t in enumerate(use_text_units)
        ]
    }

async def _find_most_related_entities_from_relationships(
    edge_datas: list[dict],
    query_param: QueryParam,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
):
    entity_names = set()
    for e in edge_datas:
        for f in e["id_set"]:
            if await knowledge_hypergraph_inst.has_vertex(f):
                entity_names.add(f)

    node_datas = await asyncio.gather(
        *[knowledge_hypergraph_inst.get_vertex(entity_name) for entity_name in entity_names]
    )

    node_degrees = await asyncio.gather(
        *[knowledge_hypergraph_inst.vertex_degree(entity_name) for entity_name in entity_names]
    )

    node_datas = [
        {**n, "entity_name": k, "rank": d}
        for k, n, d in zip(entity_names, node_datas, node_degrees)
    ]

    node_datas = truncate_list_by_token_size(
        node_datas,
        key=lambda x: x["description"],
        max_token_size=query_param.max_token_for_entity_context,
    )

    return node_datas


async def _find_related_text_unit_from_relationships(
    edge_datas: list[dict],
    query_param: QueryParam,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    knowledge_hypergraph_inst: BaseHypergraphStorage,
):
    text_units = [
        split_string_by_multi_markers(dp["source_id"], [GRAPH_FIELD_SEP])
        for dp in edge_datas
    ]

    all_text_units_lookup = {}

    for index, unit_list in enumerate(text_units):
        for c_id in unit_list:
            if c_id not in all_text_units_lookup:
                all_text_units_lookup[c_id] = {
                    "data": await text_chunks_db.get_by_id(c_id),
                    "order": index,
                }

    if any([v is None for v in all_text_units_lookup.values()]):
        logger.warning("Text chunks are missing, maybe the storage is damaged")
    all_text_units = [
        {"id": k, **v} for k, v in all_text_units_lookup.items() if v is not None
    ]
    all_text_units = sorted(all_text_units, key=lambda x: x["order"])
    all_text_units = truncate_list_by_token_size(
        all_text_units,
        key=lambda x: x["data"]["content"],
        max_token_size=query_param.max_token_for_text_unit,
    )
    all_text_units: list[TextChunkSchema] = [t["data"] for t in all_text_units]

    return all_text_units


async def hyper_query(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    entity_context = None
    relation_context = None
    use_model_func = global_config["llm_model_func"]

    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)

    result = await use_model_func(kw_prompt)

    try:
        keywords_data = json.loads(result)
        entity_keywords = keywords_data.get("low_level_keywords", [])
        relation_keywords = keywords_data.get("high_level_keywords", [])
        entity_keywords = ", ".join(entity_keywords)
        relation_keywords = ", ".join(relation_keywords)
    except json.JSONDecodeError:
        try:
            result = (
                result.replace(kw_prompt[:-1], "")
                .replace("user", "")
                .replace("model", "")
                .strip()
            )
            result = "{" + result.split("{")[1].split("}")[0] + "}"
            keywords_data = json.loads(result)
            relation_keywords = keywords_data.get("high_level_keywords", [])
            entity_keywords = keywords_data.get("low_level_keywords", [])
            relation_keywords = ", ".join(relation_keywords)
            entity_keywords = ", ".join(entity_keywords)
        # Handle parsing error
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return PROMPTS["fail_response"]
    """
        Perform different actions based on keywords:
            ll_keywords: Find information based on low-level keywords.
            hl_keywords: Define topic information based on high-level keywords.
    """
    if entity_keywords:
        """
        low_level_context: Retrieves vertices and their first-order neighbor hyperedges.
        high_level_context: Retrieves hyperedges and their first-order neighbor vertices.
        """
        entity_context = await _build_entity_query_context(
            entity_keywords,
            knowledge_hypergraph_inst,
            entities_vdb,
            text_chunks_db,
            query_param,
        )

    if relation_keywords:
        relation_context = await _build_relation_query_context(
            relation_keywords,
            knowledge_hypergraph_inst,
            entities_vdb,
            relationships_vdb,
            text_chunks_db,
            query_param,
        )
    """
        combine the information from the local_query and global_query,
        so that we can have the final retrieval information.
    """
    context = combine_contexts(relation_context.get("context"), entity_context.get("context"))

    contextJson = {
        "entities": deduplicate_by_key(entity_context.get("entities", []) + relation_context.get("entities", []), "entity_name"),
        "hyperedges": deduplicate_by_key(entity_context.get("hyperedges", []) + relation_context.get("hyperedges", []), "entity_set"),
        "text_units": deduplicate_by_key(entity_context.get("text_units", []) + relation_context.get("text_units", []), "content")
    }

    if query_param.only_need_context:
        return context
    if context is None:
        return PROMPTS["fail_response"]
    define_str = ""
    if entity_keywords or relation_keywords:
        """
        High-level keywords serve as qualifiers to the topic information
        """
        entity_keywords = entity_keywords if entity_keywords else ""
        relation_keywords = relation_keywords if relation_keywords else ""
        define_str = PROMPTS["rag_define"]
        define_str = define_str.format(ll_keywords=entity_keywords,hl_keywords=relation_keywords)
    sys_prompt_temp = PROMPTS["rag_response"]
    sys_prompt = sys_prompt_temp.format(
        context_data=context, response_type=query_param.response_type
    )
    response = await use_model_func(
        query + define_str,
        system_prompt=sys_prompt,
    )
    if len(response) > len(sys_prompt):
        response = (
            response.replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )
    if query_param.return_type == "json":
        contextJson["response"] = response
        response = contextJson
    return response 


async def hyper_query_lite(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
) -> str:

    entity_context = None
    use_model_func = global_config["llm_model_func"]

    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)

    result = await use_model_func(kw_prompt)

    try:
        keywords_data = json.loads(result)
        entity_keywords = keywords_data.get("low_level_keywords", [])
        entity_keywords = ", ".join(entity_keywords)
    except json.JSONDecodeError:
        try:
            result = (
                result.replace(kw_prompt[:-1], "")
                .replace("user", "")
                .replace("model", "")
                .strip()
            )
            result = "{" + result.split("{")[1].split("}")[0] + "}"
            keywords_data = json.loads(result)
            entity_keywords = keywords_data.get("low_level_keywords", [])
            entity_keywords = ", ".join(entity_keywords)
        # Handle parsing error
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return PROMPTS["fail_response"]
    """
        Perform different actions based on keywords:
            ll_keywords: Find information based on low-level keywords.
    """
    if entity_keywords:
        """
        low_level_context: Retrieves vertices and their first-order neighbor hyperedges.
        high_level_context: Retrieves hyperedges and their first-order neighbor vertices.
        """
        entity_context = await _build_entity_query_context(
            entity_keywords,
            knowledge_hypergraph_inst,
            entities_vdb,
            text_chunks_db,
            query_param,
        )
    """
        combine the information from the local_query and global_query,
        so that we can have the final retrieval information.
    """
    context = entity_context.get("context")

    if query_param.only_need_context:
        return context
    if context is None:
        return PROMPTS["fail_response"]
    define_str = ""
    if entity_keywords:
        """
        High-level keywords serve as qualifiers to the topic information
        """
        entity_keywords = entity_keywords if entity_keywords else ""
        define_str = PROMPTS["rag_define"]
        define_str = define_str.format(ll_keywords=entity_keywords, hl_keywords="")
    sys_prompt_temp = PROMPTS["rag_response"]
    sys_prompt = sys_prompt_temp.format(
        context_data=context, response_type=query_param.response_type
    )
    response = await use_model_func(
        query + define_str,
        system_prompt=sys_prompt,
    )
    if len(response) > len(sys_prompt):
        response = (
            response.replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )
    if query_param.return_type == "json":
        entity_context["response"] = response
        response = entity_context
    return response


async def graph_query(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    """
    检索和返回 hypergraph db 中的成对关系
    """
    use_model_func = global_config["llm_model_func"]
    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)
    result = await use_model_func(kw_prompt)
    try:
        keywords_data = json.loads(result)
        entity_keywords = keywords_data.get("low_level_keywords", [])
        relation_keywords = keywords_data.get("high_level_keywords", [])
        entity_keywords = ", ".join(entity_keywords)
        relation_keywords = ", ".join(relation_keywords)
    except json.JSONDecodeError:
        try:
            result = (
                result.replace(kw_prompt[:-1], "")
                .replace("user", "")
                .replace("model", "")
                .strip()
            )
            result = "{" + result.split("{")[1].split("}")[0] + "}"
            keywords_data = json.loads(result)
            relation_keywords = keywords_data.get("high_level_keywords", [])
            entity_keywords = keywords_data.get("low_level_keywords", [])
            relation_keywords = ", ".join(relation_keywords)
            entity_keywords = ", ".join(entity_keywords)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            return PROMPTS["fail_response"]

    # 只处理二元关系
    def filter_pairwise_edges(edges):
        return [e for e in edges if isinstance(e.get("id_set"), (list, tuple)) and len(e["id_set"]) == 2]

    # 获取所有相关的二元关系
    relation_context = None
    if relation_keywords:
        results = await relationships_vdb.query(relation_keywords, top_k=query_param.top_k)
        if not len(results):
            return PROMPTS["fail_response"]
        edge_datas = await asyncio.gather(
            *[knowledge_hypergraph_inst.get_hyperedge(r['id_set']) for r in results]
        )
        edge_degree = await asyncio.gather(
            *[knowledge_hypergraph_inst.hyperedge_degree(e['id_set']) for e in results]
        )
        edge_datas = [
            {"id_set": k["id_set"], "rank": d, **v}
            for k, v, d in zip(results, edge_datas, edge_degree)
            if v is not None
        ]
        # 只保留二元关系
        edge_datas = filter_pairwise_edges(edge_datas)
        edge_datas = sorted(
            edge_datas, key=lambda x: (x["rank"], x["weight"]), reverse=True
        )
        edge_datas = truncate_list_by_token_size(
            edge_datas,
            key=lambda x: x["description"],
            max_token_size=query_param.max_token_for_relation_context,
        )
        # 相关实体
        entity_names = set()
        for e in edge_datas:
            for f in e["id_set"]:
                if await knowledge_hypergraph_inst.has_vertex(f):
                    entity_names.add(f)
        node_datas = await asyncio.gather(
            *[knowledge_hypergraph_inst.get_vertex(entity_name) for entity_name in entity_names]
        )
        node_degrees = await asyncio.gather(
            *[knowledge_hypergraph_inst.vertex_degree(entity_name) for entity_name in entity_names]
        )
        node_datas = [
            {**n, "entity_name": k, "rank": d}
            for k, n, d in zip(entity_names, node_datas, node_degrees)
            if n is not None
        ]
        node_datas = truncate_list_by_token_size(
            node_datas,
            key=lambda x: x["description"],
            max_token_size=query_param.max_token_for_entity_context,
        )
        # 相关文本
        text_units = [
            split_string_by_multi_markers(dp["source_id"], [GRAPH_FIELD_SEP])
            for dp in edge_datas
        ]
        all_text_units_lookup = {}
        for index, unit_list in enumerate(text_units):
            for c_id in unit_list:
                if c_id not in all_text_units_lookup:
                    all_text_units_lookup[c_id] = {
                        "data": await text_chunks_db.get_by_id(c_id),
                        "order": index,
                    }
        all_text_units = [
            {"id": k, **v} for k, v in all_text_units_lookup.items() if v is not None and v["data"] is not None
        ]
        all_text_units = sorted(all_text_units, key=lambda x: x["order"])
        all_text_units = truncate_list_by_token_size(
            all_text_units,
            key=lambda x: x["data"]["content"],
            max_token_size=query_param.max_token_for_text_unit,
        )
        all_text_units = [t["data"] for t in all_text_units]
        # 格式化 context
        relations_section_list = [
            ["id", "entity set", "description", "keywords", "weight", "rank"]
        ]
        for i, e in enumerate(edge_datas):
            relations_section_list.append(
                [
                    i,
                    e["id_set"],
                    e["description"],
                    e["keywords"],
                    e["weight"],
                    e["rank"],
                ]
            )
        relations_context = list_of_list_to_csv(relations_section_list)
        entites_section_list = [["id", "entity", "type", "description", "additional properties", "rank"]]
        for i, n in enumerate(node_datas):
            entites_section_list.append(
                [
                    i,
                    n["entity_name"],
                    n.get("entity_type", "UNKNOWN"),
                    n.get("description", "UNKNOWN"),
                    n.get("additional_properties", "UNKNOWN"),
                    n["rank"],
                ]
            )
        entities_context = list_of_list_to_csv(entites_section_list)
        text_units_section_list = [["id", "content"]]
        for i, t in enumerate(all_text_units):
            text_units_section_list.append([i, t["content"]])
        text_units_context = list_of_list_to_csv(text_units_section_list)
        context_string = f"""
-----Entities-----
```csv
{entities_context}
```
-----Relationships-----
```csv
{relations_context}
```
-----Sources-----
```csv
{text_units_context}
```
"""
        contextJson = {
            "context": context_string,
            "entities": [
                {
                    "id": i,
                    "entity_name": n["entity_name"],
                    "entity_type": n.get("entity_type", "UNKNOWN"),
                    "description": n.get("description", "UNKNOWN"),
                    "additional_properties": n.get("additional_properties", "UNKNOWN"),
                    "rank": n["rank"]
                }
                for i, n in enumerate(node_datas)
            ],
            "hyperedges": [
                {
                    "id": i,
                    "entity_set": e["id_set"],
                    "description": e["description"],
                    "keywords": e["keywords"],
                    "weight": e["weight"],
                    "rank": e["rank"]
                }
                for i, e in enumerate(edge_datas)
            ],
            "text_units": [
                {
                    "id": i,
                    "content": t["content"]
                }
                for i, t in enumerate(all_text_units)
            ]
        }
        if query_param.only_need_context:
            return context_string
        if context_string is None:
            return PROMPTS["fail_response"]
        define_str = ""
        if entity_keywords or relation_keywords:
            entity_keywords = entity_keywords if entity_keywords else ""
            relation_keywords = relation_keywords if relation_keywords else ""
            define_str = PROMPTS["rag_define"]
            define_str = define_str.format(ll_keywords=entity_keywords,hl_keywords=relation_keywords)
        sys_prompt_temp = PROMPTS["rag_response"]
        sys_prompt = sys_prompt_temp.format(
            context_data=context_string, response_type=query_param.response_type
        )
        response = await use_model_func(
            query + define_str,
            system_prompt=sys_prompt,
        )
        if len(response) > len(sys_prompt):
            response = (
                response.replace(sys_prompt, "")
                .replace("user", "")
                .replace("model", "")
                .replace(query, "")
                .replace("<system>", "")
                .replace("</system>", "")
                .strip()
            )
        if query_param.return_type == "json":
            contextJson["response"] = response
            response = contextJson
        return response
    else:
        return PROMPTS["fail_response"]


def combine_contexts(relation_context, entity_context):
    # Function to extract entities, relationships, and sources from context strings

    def extract_sections(context):
        entities_match = re.search(
            r"-----Entities-----\s*```csv\s*(.*?)\s*```", context, re.DOTALL
        )
        relationships_match = re.search(
            r"-----Relationships-----\s*```csv\s*(.*?)\s*```", context, re.DOTALL
        )
        sources_match = re.search(
            r"-----Sources-----\s*```csv\s*(.*?)\s*```", context, re.DOTALL
        )

        entities = entities_match.group(1) if entities_match else ""
        relationships = relationships_match.group(1) if relationships_match else ""
        sources = sources_match.group(1) if sources_match else ""

        return entities, relationships, sources

    # Extract sections from both contexts

    if relation_context is None:
        warnings.warn(
            "High Level context is None. Return empty High_Level entity/relationship/source"
        )
        hl_entities, hl_relationships, hl_sources = "", "", ""
    else:
        hl_entities, hl_relationships, hl_sources = extract_sections(relation_context)

    if entity_context is None:
        warnings.warn(
            "Low Level context is None. Return empty Low_Level entity/relationship/source"
        )
        ll_entities, ll_relationships, ll_sources = "", "", ""
    else:
        ll_entities, ll_relationships, ll_sources = extract_sections(entity_context)

    # Combine and deduplicate the entities
    combined_entities = process_combine_contexts(hl_entities, ll_entities)

    # Combine and deduplicate the relationships
    combined_relationships = process_combine_contexts(
        hl_relationships, ll_relationships
    )

    # Combine and deduplicate the sources
    combined_sources = process_combine_contexts(hl_sources, ll_sources)

    # Format the combined context
    return f"""
-----Entities-----
```csv
{combined_entities}
```
-----Relationships-----
```csv
{combined_relationships}
```
-----Sources-----
```csv
{combined_sources}
```
"""

def remove_after_sources(input_string: str) -> str:
    """
    删除字符串中 '-----Sources-----' 及其之后的所有内容。
    """
    # 找到 '-----Sources-----' 的起始位置
    index = input_string.find("-----Sources-----")
    if index != -1:  # 如果找到了该字符串
        return input_string[:index]  # 返回该位置之前的内容
    return input_string  # 如果没有找到，返回原始字符串

async def naive_query(
    query,
    chunks_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    use_model_func = global_config["llm_model_func"]
    results = await chunks_vdb.query(query, top_k=query_param.top_k)
    if not len(results):
        return PROMPTS["fail_response"]
    chunks_ids = [r["id"] for r in results]
    chunks = await text_chunks_db.get_by_ids(chunks_ids)

    maybe_trun_chunks = truncate_list_by_token_size(
        chunks,
        key=lambda x: x["content"],
        max_token_size=query_param.max_token_for_text_unit,
    )
    logger.info(f"Truncate {len(chunks)} to {len(maybe_trun_chunks)} chunks")
    section = "--New Chunk--\n".join([c["content"] for c in maybe_trun_chunks])
    if query_param.only_need_context:
        return section
    sys_prompt_temp = PROMPTS["naive_rag_response"]
    sys_prompt = sys_prompt_temp.format(
        content_data=section, response_type=query_param.response_type
    )
    response = await use_model_func(
        query,
        system_prompt=sys_prompt,
    )

    if len(response) > len(sys_prompt):
        response = (
            response[len(sys_prompt) :]
            .replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )
    if query_param.return_type == "json":
        response = {
            "response": response,
        }
    return response


async def llm_query(
    query,
    query_param: QueryParam,
    global_config: dict,
):
    """
    只调用 LLM，不进行任何数据查询。
    """
    use_model_func = global_config["llm_model_func"]
    sys_prompt_temp = PROMPTS["rag_response"]
    sys_prompt = sys_prompt_temp.format(
        context_data="", response_type=query_param.response_type
    )
    response = await use_model_func(
        query,
        system_prompt=sys_prompt,
    )
    if len(response) > len(sys_prompt):
        response = (
            response.replace(sys_prompt, "")
            .replace("user", "")
            .replace("model", "")
            .replace(query, "")
            .replace("<system>", "")
            .replace("</system>", "")
            .strip()
        )
    if query_param.return_type == "json":
        response = {
            "response": response,
        }
    return response


