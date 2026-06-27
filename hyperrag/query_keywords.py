"""Keyword parsing helpers for query modes."""

import json


def _coerce_keywords(keywords) -> str:
    if isinstance(keywords, list):
        return ", ".join(keywords)
    return keywords or ""


def _load_keywords_json(result: str, kw_prompt: str) -> dict:
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        cleaned = (
            result.replace(kw_prompt[:-1], "")
            .replace("user", "")
            .replace("model", "")
            .strip()
        )
        cleaned = "{" + cleaned.split("{")[1].split("}")[0] + "}"
        return json.loads(cleaned)


def parse_query_keywords(result: str, kw_prompt: str) -> tuple[str, str]:
    """Parse low-level and high-level query keywords from an LLM response."""
    keywords_data = _load_keywords_json(result, kw_prompt)
    entity_keywords = _coerce_keywords(keywords_data.get("low_level_keywords", []))
    relation_keywords = _coerce_keywords(keywords_data.get("high_level_keywords", []))
    return entity_keywords, relation_keywords


def parse_low_level_keywords(result: str, kw_prompt: str) -> str:
    """Parse only low-level query keywords from an LLM response."""
    keywords_data = _load_keywords_json(result, kw_prompt)
    return _coerce_keywords(keywords_data.get("low_level_keywords", []))
