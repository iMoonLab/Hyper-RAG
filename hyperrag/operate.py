"""Compatibility facade for HyperRAG operations.

Implementation lives in focused modules:
- chunking.py: text chunking
- extraction.py: LLM extraction record parsing
- graph_upsert.py: graph merge and upsert helpers
- indexing.py: indexing orchestration
- query_context.py: retrieval context construction
- query_modes.py: non-streaming query modes
- query_stream.py: streaming query modes
"""

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
from .query_context import (
    _build_entity_query_context,
    _build_relation_query_context,
    _find_most_related_edges_from_entities,
    _find_most_related_entities_from_relationships,
    _find_most_related_text_unit_from_entities,
    _find_related_text_unit_from_relationships,
    combine_contexts,
    remove_after_sources,
)
from .query_modes import (
    graph_query,
    hyper_query,
    hyper_query_lite,
    llm_query,
    naive_query,
)
from .query_stream import (
    hyper_query_lite_stream,
    hyper_query_stream,
    llm_query_stream,
    naive_query_stream,
)

__all__ = [
    "chunking_by_token_size",
    "extract_entities",
    "hyper_query",
    "hyper_query_lite",
    "graph_query",
    "naive_query",
    "llm_query",
    "hyper_query_stream",
    "hyper_query_lite_stream",
    "naive_query_stream",
    "llm_query_stream",
    "combine_contexts",
    "remove_after_sources",
    "_handle_single_entity_extraction",
    "_handle_single_relationship_extraction_low",
    "_handle_single_relationship_extraction_high",
    "_handle_entity_summary",
    "_handle_entity_additional_properties",
    "_handle_relation_summary",
    "_handle_relation_keywords_summary",
    "_merge_nodes_then_upsert",
    "_merge_edges_then_upsert",
    "_build_entity_query_context",
    "_find_most_related_text_unit_from_entities",
    "_find_most_related_edges_from_entities",
    "_build_relation_query_context",
    "_find_most_related_entities_from_relationships",
    "_find_related_text_unit_from_relationships",
]
