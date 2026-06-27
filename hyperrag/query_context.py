"""Query context builders for HyperRAG retrieval."""

import asyncio
import re
import warnings

from .base import BaseHypergraphStorage, BaseKVStorage, BaseVectorStorage, QueryParam, TextChunkSchema
from .prompt import GRAPH_FIELD_SEP
from .utils import (
    list_of_list_to_csv,
    logger,
    process_combine_contexts,
    split_string_by_multi_markers,
    truncate_list_by_token_size,
)


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
