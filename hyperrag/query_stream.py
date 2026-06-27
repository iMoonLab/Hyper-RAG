"""Streaming query modes for HyperRAG."""

import json

from .base import BaseHypergraphStorage, BaseKVStorage, BaseVectorStorage, QueryParam, TextChunkSchema
from .prompt import PROMPTS
from .query_context import _build_entity_query_context, _build_relation_query_context, combine_contexts
from .query_keywords import parse_low_level_keywords, parse_query_keywords
from .utils import deduplicate_by_key, truncate_list_by_token_size


async def hyper_query_stream(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    """完整 Hyper-RAG 的流式回答版本。

    检索上下文仍然先完整构造，最后 LLM 生成阶段改为 async generator。
    """
    entity_context = None
    relation_context = None
    use_model_func = global_config["llm_model_func"]
    use_model_stream_func = global_config.get("llm_model_stream_func", None)
    if use_model_stream_func is None:
        raise AttributeError("llm_model_stream_func not found; streaming is unavailable.")

    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)

    result = await use_model_func(kw_prompt)

    try:
        entity_keywords, relation_keywords = parse_query_keywords(result, kw_prompt)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        yield PROMPTS["fail_response"]
        return

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
        yield context or ""
        return

    if context is None:
        yield PROMPTS["fail_response"]
        return

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
    # ====== 1) 流式接口不建议支持 json（json 必须完整结构，不适合边吐边返回）======
    if query_param.return_type == "json":
        raise ValueError("Streaming does not support return_type='json'. Use return_type='text'.")

    # ====== 2) 真流式输出：逐 token 产出 ======
    async for tok in use_model_stream_func(query + define_str, system_prompt=sys_prompt,):
        if tok:
            yield tok

    return

async def hyper_query_lite_stream(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    # hyper_query_lite 的流式回答版本：检索逻辑相同，最终 LLM 逐块 yield。
    """
    hyper_query_lite 的流式版本：逻辑与 hyper_query_lite 相同，只把最后一步 LLM 生成改成 yield token
    """
    entity_context = None
    use_model_func = global_config["llm_model_func"]
    use_model_stream_func = global_config.get("llm_model_stream_func", None)
    if use_model_stream_func is None:
        raise AttributeError("llm_model_stream_func not found; streaming is unavailable.")

    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)

    result = await use_model_func(kw_prompt)

    try:
        entity_keywords = parse_low_level_keywords(result, kw_prompt)
    except json.JSONDecodeError:
        yield PROMPTS["fail_response"]
        return

    if entity_keywords:
        entity_context = await _build_entity_query_context(
            entity_keywords,
            knowledge_hypergraph_inst,
            entities_vdb,
            text_chunks_db,
            query_param,
        )

    context = entity_context.get("context") if entity_context else None

    if query_param.only_need_context:
        yield context or ""
        return

    if context is None:
        yield PROMPTS["fail_response"]
        return

    define_str = ""
    if entity_keywords:
        define_str = PROMPTS["rag_define"].format(ll_keywords=entity_keywords, hl_keywords="")

    sys_prompt = PROMPTS["rag_response"].format(
        context_data=context,
        response_type=query_param.response_type,
    )

    if query_param.return_type == "json":
        raise ValueError("Streaming does not support return_type='json'. Use return_type='text'.")

    async for tok in use_model_stream_func(
        query + define_str,
        system_prompt=sys_prompt,
    ):
        if tok:
            yield tok
    return

async def naive_query_stream(
    query,
    chunks_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    # naive_query 的流式回答版本：先检索 chunk，再流式生成答案。
    """
    naive_query 的流式版本：先做 chunk 检索拿到 section，然后用 LLM stream 输出答案
    """
    use_model_func = global_config["llm_model_func"]
    use_model_stream_func = global_config.get("llm_model_stream_func", None)
    if use_model_stream_func is None:
        raise AttributeError("llm_model_stream_func not found; streaming is unavailable.")

    results = await chunks_vdb.query(query, top_k=query_param.top_k)
    if not len(results):
        yield PROMPTS["fail_response"]
        return

    chunks_ids = [r["id"] for r in results]
    chunks = await text_chunks_db.get_by_ids(chunks_ids)

    maybe_trun_chunks = truncate_list_by_token_size(
        chunks,
        key=lambda x: x["content"],
        max_token_size=query_param.max_token_for_text_unit,
    )

    section = "--New Chunk--\n".join([c["content"] for c in maybe_trun_chunks])

    if query_param.only_need_context:
        yield section or ""
        return

    sys_prompt = PROMPTS["naive_rag_response"].format(
        content_data=section,
        response_type=query_param.response_type,
    )

    if query_param.return_type == "json":
        raise ValueError("Streaming does not support return_type='json'. Use return_type='text'.")

    async for tok in use_model_stream_func(
        query,
        system_prompt=sys_prompt,
    ):
        if tok:
            yield tok
    return

async def llm_query_stream(
    query,
    query_param: QueryParam,
    global_config: dict,
):
    # llm_query 的流式回答版本：不检索，直接让 LLM 流式回答。
    """
    llm_query 的流式版本：不检索，直接按 rag_response（空 context）走流式输出
    """
    use_model_stream_func = global_config.get("llm_model_stream_func", None)
    if use_model_stream_func is None:
        raise AttributeError("llm_model_stream_func not found; streaming is unavailable.")

    sys_prompt = PROMPTS["rag_response"].format(
        context_data="",
        response_type=query_param.response_type,
    )

    if query_param.return_type == "json":
        raise ValueError("Streaming does not support return_type='json'. Use return_type='text'.")

    async for tok in use_model_stream_func(
        query,
        system_prompt=sys_prompt,
    ):
        if tok:
            yield tok
    return
