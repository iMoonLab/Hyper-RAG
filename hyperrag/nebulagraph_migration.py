from __future__ import annotations

import asyncio
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import pickle
from typing import Any

from .nebulagraph_ids import normalize_id_set


@dataclass(frozen=True)
class HypergraphSnapshot:
    vertices: dict[str, dict[str, Any]]
    hyperedges: dict[tuple[str, ...], dict[str, Any]]


def _copy_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"HypergraphDB payload must be a dict, got {type(value).__name__}.")
    return deepcopy(value)


def _run_sync(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    coro.close()
    if loop.is_running():
        raise RuntimeError(
            "migrate_snapshot_to_storage cannot run inside an active event loop; "
            "use migrate_snapshot_to_storage_async instead."
        )
    return loop.run_until_complete(coro)


def load_hgdb_snapshot(hgdb_file: str | Path) -> HypergraphSnapshot:
    """Load a local trusted HypergraphDB `.hgdb` pickle snapshot."""
    hgdb_path = Path(hgdb_file)
    with hgdb_path.open("rb") as file:
        raw_data = pickle.load(file)

    raw_vertices, raw_hyperedges = _extract_hypergraph_payload(raw_data)

    vertices = {
        normalize_id_set([vertex_id])[0]: _copy_payload(vertex_data)
        for vertex_id, vertex_data in raw_vertices.items()
    }
    hyperedges = {
        normalize_id_set(id_set): _copy_payload(hyperedge_data)
        for id_set, hyperedge_data in raw_hyperedges.items()
    }

    return HypergraphSnapshot(vertices=vertices, hyperedges=hyperedges)


def _extract_hypergraph_payload(raw_data: Any) -> tuple[dict[Any, Any], dict[Any, Any]]:
    if isinstance(raw_data, dict):
        raw_vertices = raw_data.get("v_data", {})
        raw_hyperedges = raw_data.get("e_data", {})
    elif hasattr(raw_data, "_v_data") and hasattr(raw_data, "_e_data"):
        raw_vertices = raw_data._v_data
        raw_hyperedges = raw_data._e_data
    else:
        raise TypeError(
            "HypergraphDB file must contain a dict payload or an object with "
            f"_v_data/_e_data attributes, got {type(raw_data).__name__}."
        )

    if not isinstance(raw_vertices, dict):
        raise TypeError("HypergraphDB v_data must be a dict.")
    if not isinstance(raw_hyperedges, dict):
        raise TypeError("HypergraphDB e_data must be a dict.")
    return raw_vertices, raw_hyperedges


async def migrate_snapshot_to_storage_async(
    snapshot: HypergraphSnapshot, storage
) -> None:
    for vertex_id, vertex_data in snapshot.vertices.items():
        await storage.upsert_vertex(vertex_id, deepcopy(vertex_data))

    for id_set, hyperedge_data in snapshot.hyperedges.items():
        data = deepcopy(hyperedge_data)
        data.setdefault("id_set", list(id_set))
        data.setdefault("arity", len(id_set))
        await storage.upsert_hyperedge(id_set, data)


def migrate_snapshot_to_storage(snapshot: HypergraphSnapshot, storage) -> None:
    _run_sync(migrate_snapshot_to_storage_async(snapshot, storage))


__all__ = [
    "HypergraphSnapshot",
    "load_hgdb_snapshot",
    "migrate_snapshot_to_storage",
    "migrate_snapshot_to_storage_async",
]
