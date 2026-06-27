from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .base import BaseHypergraphStorage
from .nebulagraph_ids import normalize_id_set


@dataclass
class NebulaHypergraphStorage(BaseHypergraphStorage):
    _vertex_data: dict[str, dict] = field(default_factory=dict, init=False)
    _hyperedge_data: dict[tuple[str, ...], dict] = field(default_factory=dict, init=False)

    @staticmethod
    def _normalize_vertex_id(v_id: Any) -> str:
        return normalize_id_set([v_id])[0]

    @staticmethod
    def _copy_data(data: Optional[Dict]) -> dict:
        return deepcopy(dict(data or {}))

    async def has_vertex(self, v_id: Any) -> bool:
        return self._normalize_vertex_id(v_id) in self._vertex_data

    async def has_hyperedge(self, e_tuple: Union[List, Set, Tuple]) -> bool:
        return normalize_id_set(e_tuple) in self._hyperedge_data

    async def get_vertex(self, v_id: str, default: Any = None):
        v_key = self._normalize_vertex_id(v_id)
        if v_key not in self._vertex_data:
            return default
        return self._copy_data(self._vertex_data[v_key])

    async def get_hyperedge(
        self, e_tuple: Union[List, Set, Tuple], default: Any = None
    ):
        e_key = normalize_id_set(e_tuple)
        if e_key not in self._hyperedge_data:
            return default
        return self._copy_data(self._hyperedge_data[e_key])

    async def get_all_vertices(self):
        return sorted(self._vertex_data)

    async def get_all_hyperedges(self):
        return sorted(self._hyperedge_data)

    async def get_num_of_vertices(self):
        return len(self._vertex_data)

    async def get_num_of_hyperedges(self):
        return len(self._hyperedge_data)

    async def upsert_vertex(self, v_id: Any, v_data: Optional[Dict] = None):
        v_key = self._normalize_vertex_id(v_id)
        self._vertex_data[v_key] = self._copy_data(v_data)
        return self._copy_data(self._vertex_data[v_key])

    async def upsert_hyperedge(
        self, e_tuple: Union[List, Set, Tuple], e_data: Optional[Dict] = None
    ):
        e_key = normalize_id_set(e_tuple)
        self._hyperedge_data[e_key] = self._copy_data(e_data)
        return self._copy_data(self._hyperedge_data[e_key])

    async def remove_vertex(self, v_id: Any):
        v_key = self._normalize_vertex_id(v_id)
        removed = self._vertex_data.pop(v_key, None)
        incident_edges = [
            e_key for e_key in self._hyperedge_data if v_key in e_key
        ]
        for e_key in incident_edges:
            self._hyperedge_data.pop(e_key, None)
        return removed

    async def remove_hyperedge(self, e_tuple: Union[List, Set, Tuple]):
        e_key = normalize_id_set(e_tuple)
        return self._hyperedge_data.pop(e_key, None)

    async def vertex_degree(self, v_id: Any) -> int:
        v_key = self._normalize_vertex_id(v_id)
        return sum(1 for e_key in self._hyperedge_data if v_key in e_key)

    async def hyperedge_degree(self, e_tuple: Union[List, Set, Tuple]) -> int:
        e_key = normalize_id_set(e_tuple)
        if e_key not in self._hyperedge_data:
            return 0
        return len(e_key)

    async def get_nbr_e_of_vertex(self, v_id: Any) -> list[tuple[str, ...]]:
        v_key = self._normalize_vertex_id(v_id)
        return sorted(e_key for e_key in self._hyperedge_data if v_key in e_key)

    async def get_nbr_v_of_hyperedge(
        self, e_tuple: Union[List, Set, Tuple]
    ) -> list[str]:
        e_key = normalize_id_set(e_tuple)
        if e_key not in self._hyperedge_data:
            return []
        return list(e_key)

    async def get_nbr_v_of_vertex(self, v_id: Any, exclude_self=True) -> list[str]:
        v_key = self._normalize_vertex_id(v_id)
        neighbors = set()
        for e_key in self._hyperedge_data:
            if v_key in e_key:
                neighbors.update(e_key)
        if exclude_self:
            neighbors.discard(v_key)
        return sorted(neighbors)
