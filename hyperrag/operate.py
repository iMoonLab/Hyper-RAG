"""HyperRAG 的核心算法流程。

这个文件负责两条主链路：

1. 建库链路：
   原文 -> token 切块 -> LLM 抽实体/低阶超边/高阶超边
   -> 合并实体和关系 -> 写入超图 + 实体/关系向量库。

2. 查询链路：
   问题 -> LLM 抽 low/high keywords
   -> low keywords 查实体向量库，high keywords 查关系向量库
   -> 回 HypergraphDB 扩展 vertex/hyperedge/neighbor/source_id
   -> 回 text_chunks KV 找原文 chunk
   -> 拼 Entities/Relationships/Sources 给 LLM 回答。
"""

import asyncio
import json
import re
from typing import Union
import warnings


from .utils import (
    logger,
    list_of_list_to_csv,
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

from .chunking import chunking_by_token_size
from .extraction import (
    _handle_single_entity_extraction,
    _handle_single_relationship_extraction_high,
    _handle_single_relationship_extraction_low,
)
from .graph_upsert import (
    _handle_entity_additional_properties,
    _handle_entity_summary,
    _handle_relation_keywords_summary,
    _handle_relation_summary,
    _merge_edges_then_upsert,
    _merge_nodes_then_upsert,
)
from .indexing import extract_entities

async def _build_entity_query_context(
    query,
    knowledge_hypergraph_inst: BaseHypergraphStorage,
    entities_vdb: BaseVectorStorage,
    text_chunks_db: BaseKVStorage[TextChunkSchema],
    query_param: QueryParam,
):
    """实体线查询：low_level_keywords -> entities_vdb -> vertex/超边/source chunks。

    输入 query 是低阶关键词字符串。
    输出是包含 context、entities、hyperedges、text_units 的结构化上下文包。
    """
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
    """根据实体 source_id 和邻接关系找最相关的原文 chunk。"""
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
        for edge_tuple in this_edges:
            all_one_hop_nodes.update(edge_tuple)

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
                for edge_tuple in this_edges:
                    for e in edge_tuple:                    
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
    """从命中的实体出发，找它们连接的相关超边。"""
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
    """关系线查询：high_level_keywords -> relationships_vdb -> hyperedge/entity/source chunks。

    输入 keywords 是高阶关键词字符串。
    输出同样是包含 context、entities、hyperedges、text_units 的结构化上下文包。
    """
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
    """根据命中的超边找其连接的实体，并按度数和 token 限制筛选。"""
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
    """根据超边 source_id 找相关原文 chunk。"""
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
    # Graph-RAG 对照查询：只保留二元关系，模拟传统图 RAG 的 pairwise 边。
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
    """合并关系线和实体线的 CSV 上下文。"""
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
    # 截断 Sources 之后的内容，供部分展示/清理场景使用。
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

# =========================
# Streaming versions (END)
# =========================

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
        except json.JSONDecodeError as e:
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

