"""Non-streaming query modes for HyperRAG."""

import asyncio
import json

from .base import BaseHypergraphStorage, BaseKVStorage, BaseVectorStorage, QueryParam, TextChunkSchema
from .prompt import GRAPH_FIELD_SEP, PROMPTS
from .query_context import (
    _build_entity_query_context,
    _build_relation_query_context,
    combine_contexts,
)
from .query_keywords import parse_low_level_keywords, parse_query_keywords
from .utils import (
    deduplicate_by_key,
    list_of_list_to_csv,
    logger,
    split_string_by_multi_markers,
    truncate_list_by_token_size,
)


async def hyper_query(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    relationships_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    """完整 Hyper-RAG 查询。

    同时走两条线：
    - low_level_keywords -> 实体向量库 -> 超图 vertex 扩展；
    - high_level_keywords -> 关系向量库 -> 超图 hyperedge 扩展。
    两条线合并后，把 Entities / Relationships / Sources 交给 LLM 回答。
    """
    entity_context = None
    relation_context = None
    use_model_func = global_config["llm_model_func"]

    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)

    # 第一步：先让 LLM 从用户问题里抽两类关键词。
    # low_level_keywords 偏实体；high_level_keywords 偏关系/主题。
    result = await use_model_func(kw_prompt)

    try:
        entity_keywords, relation_keywords = parse_query_keywords(result, kw_prompt)
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
        # 实体线输入：低阶关键词字符串。
        # 实体线输出：相关实体、这些实体连接的超边、以及 source_id 对应的原文 chunk。
        entity_context = await _build_entity_query_context(
            entity_keywords,
            knowledge_hypergraph_inst,
            entities_vdb,
            text_chunks_db,
            query_param,
        )

    if relation_keywords:
        # 关系线输入：高阶关键词字符串。
        # 关系线输出：相关超边、超边连接的实体、以及 source_id 对应的原文 chunk。
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

    # 保留结构化结果，供 Web-UI 展示检索证据和超图关系。
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
    """轻量 Hyper-RAG 查询。

    主要走实体线：low_level_keywords -> entities_vdb -> vertex/邻接超边/source chunks。
    相比 hyper_query，它不主动走 high_level_keywords 的关系向量检索。
    """

    entity_context = None
    use_model_func = global_config["llm_model_func"]

    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)

    result = await use_model_func(kw_prompt)

    try:
        entity_keywords = parse_low_level_keywords(result, kw_prompt)
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
    # Graph-RAG 对照查询：只保留二元关系，模拟传统图 RAG 的 pairwise 边。
    """
    检索和返回 hypergraph db 中的成对关系
    """
    use_model_func = global_config["llm_model_func"]
    kw_prompt_temp = PROMPTS["keywords_extraction"]
    kw_prompt = kw_prompt_temp.format(query=query)
    result = await use_model_func(kw_prompt)
    try:
        entity_keywords, relation_keywords = parse_query_keywords(result, kw_prompt)
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

async def naive_query(
    query,
    chunks_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
    global_config: dict,
):
    """普通 RAG 查询：query -> chunks_vdb -> text_chunks_db -> LLM。"""
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
    # 纯 LLM 查询：不检索任何本地数据，作为无 RAG 基线。
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
