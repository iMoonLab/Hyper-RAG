"""Graph merge, summary, and upsert helpers for indexing."""

from collections import Counter

from .prompt import GRAPH_FIELD_SEP, PROMPTS
from .utils import (
    decode_tokens_by_tiktoken,
    encode_string_by_tiktoken,
    logger,
    split_string_by_multi_markers,
)


async def _handle_entity_summary(
    entity_or_relation_name: str,
    description: str,
    global_config: dict,
) -> str:
    """当同名实体描述过长时，用 LLM 压缩实体 description。"""
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
    """当实体附加属性过长时，用 LLM 压缩 additional_properties。"""
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
    """当关系/超边描述过长时，用 LLM 压缩 relation description。"""
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
    """当关系关键词过长时，用 LLM 压缩 keywords。"""
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

async def _merge_nodes_then_upsert(
    entity_name: str,
    nodes_data: list[dict],
    knowledge_hypergraph_inst,
    global_config: dict,
):
    """合并同名实体并写入超图 vertex。

    输入是同一个 entity_name 在多个 chunk 中抽到的多条实体记录。
    输出会用于 entities_vdb：调用方会把实体描述组装成可 embedding 文本。
    """
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
    """合并同一个实体集合的关系并写入超图 hyperedge。

    id_set 是超边连接的实体集合，例如 ("A", "B", "C")。
    如果某些实体还不存在，会先补 UNKNOWN vertex，保证超边可以挂载。
    """
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
