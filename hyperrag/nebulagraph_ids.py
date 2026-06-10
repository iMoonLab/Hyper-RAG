from __future__ import annotations

from collections.abc import Iterable
from hashlib import sha256


def _canonical_text(value: object) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("Canonical text must not be empty.")
    return text


def _stable_hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:32]


def canonical_entity_vid(database_name: str, entity_name: object) -> str:
    scope = _canonical_text(database_name)
    name = _canonical_text(entity_name)
    payload = scope + "\x1f" + name
    return "ent:" + _stable_hash(payload)


def normalize_id_set(id_set: Iterable[object]) -> tuple[str, ...]:
    normalized = tuple(sorted({_canonical_text(item) for item in id_set}))
    if not normalized:
        raise ValueError("id_set must contain at least one ID.")
    return normalized


def canonical_hyperedge_vid(database_name: str, id_set: Iterable[object]) -> str:
    scope = _canonical_text(database_name)
    member_ids = normalize_id_set(id_set)
    payload = scope + "\x1f" + "\x1e".join(member_ids)
    return "hedge:" + _stable_hash(payload)


__all__ = [
    "canonical_entity_vid",
    "canonical_hyperedge_vid",
    "normalize_id_set",
]
