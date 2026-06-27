"""LLM extraction record parsers."""

from .utils import clean_str, is_float_regex


async def _handle_single_entity_extraction(
    record_attributes: list[str],
    chunk_key: str,
):
    """把 LLM 抽取结果中的 Entity 记录转换成实体 dict。"""
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
    """把 Low-order Hyperedge 记录转换成低阶超边 dict。"""
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
    """把 High-order Hyperedge 记录转换成高阶超边 dict。"""
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
