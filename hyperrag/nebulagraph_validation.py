from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from .nebulagraph_ids import normalize_id_set


@dataclass
class ParityReport:
    passed: bool
    failures: list[str] = field(default_factory=list)


def _format_hyperedge(id_set: Iterable[str]) -> str:
    return repr(tuple(id_set))


def _sorted_hyperedges(edges: Iterable[Iterable[Any]]) -> list[tuple[str, ...]]:
    return sorted(normalize_id_set(edge) for edge in edges)


def _sorted_vertices(vertices: Iterable[Any]) -> list[str]:
    return list(normalize_id_set(vertices))


async def compare_storage_backends(
    left,
    right,
    sample_vertices: Iterable[str],
    sample_hyperedges: Iterable[tuple[str, ...]],
) -> ParityReport:
    failures: list[str] = []

    left_vertex_count = await left.get_num_of_vertices()
    right_vertex_count = await right.get_num_of_vertices()
    if left_vertex_count != right_vertex_count:
        failures.append(
            "vertex count mismatch: "
            f"left={left_vertex_count} right={right_vertex_count}"
        )

    left_hyperedge_count = await left.get_num_of_hyperedges()
    right_hyperedge_count = await right.get_num_of_hyperedges()
    if left_hyperedge_count != right_hyperedge_count:
        failures.append(
            "hyperedge count mismatch: "
            f"left={left_hyperedge_count} right={right_hyperedge_count}"
        )

    for vertex_id in sample_vertices:
        normalized_vertex_id = normalize_id_set([vertex_id])[0]

        left_vertex = await left.get_vertex(normalized_vertex_id)
        right_vertex = await right.get_vertex(normalized_vertex_id)
        if left_vertex != right_vertex:
            failures.append(
                "vertex payload mismatch: "
                f"vertex={normalized_vertex_id!r} left={left_vertex!r} right={right_vertex!r}"
            )

        left_degree = await left.vertex_degree(normalized_vertex_id)
        right_degree = await right.vertex_degree(normalized_vertex_id)
        if left_degree != right_degree:
            failures.append(
                "vertex degree mismatch: "
                f"vertex={normalized_vertex_id!r} left={left_degree} right={right_degree}"
            )

        left_neighbor_edges = _sorted_hyperedges(
            await left.get_nbr_e_of_vertex(normalized_vertex_id)
        )
        right_neighbor_edges = _sorted_hyperedges(
            await right.get_nbr_e_of_vertex(normalized_vertex_id)
        )
        if left_neighbor_edges != right_neighbor_edges:
            failures.append(
                "vertex neighbor hyperedges mismatch: "
                f"vertex={normalized_vertex_id!r} "
                f"left={left_neighbor_edges!r} right={right_neighbor_edges!r}"
            )

    for sample_hyperedge in sample_hyperedges:
        normalized_hyperedge = normalize_id_set(sample_hyperedge)
        hyperedge_label = _format_hyperedge(normalized_hyperedge)

        left_hyperedge = await left.get_hyperedge(normalized_hyperedge)
        right_hyperedge = await right.get_hyperedge(normalized_hyperedge)
        if left_hyperedge != right_hyperedge:
            failures.append(
                "hyperedge payload mismatch: "
                f"id_set={hyperedge_label} left={left_hyperedge!r} right={right_hyperedge!r}"
            )

        left_degree = await left.hyperedge_degree(normalized_hyperedge)
        right_degree = await right.hyperedge_degree(normalized_hyperedge)
        if left_degree != right_degree:
            failures.append(
                "hyperedge degree mismatch: "
                f"id_set={hyperedge_label} left={left_degree} right={right_degree}"
            )

        left_neighbor_vertices = _sorted_vertices(
            await left.get_nbr_v_of_hyperedge(normalized_hyperedge)
        )
        right_neighbor_vertices = _sorted_vertices(
            await right.get_nbr_v_of_hyperedge(normalized_hyperedge)
        )
        if left_neighbor_vertices != right_neighbor_vertices:
            failures.append(
                "hyperedge neighbors mismatch: "
                f"id_set={hyperedge_label} "
                f"left={left_neighbor_vertices!r} right={right_neighbor_vertices!r}"
            )

    return ParityReport(passed=not failures, failures=failures)


__all__ = ["ParityReport", "compare_storage_backends"]
