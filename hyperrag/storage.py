import asyncio
import html
import os
from dataclasses import dataclass
from typing import Any, Union, cast, List, Set, Tuple, Optional, Dict
import numpy as np
from nano_vectordb import NanoVectorDB
from hyperdb import HypergraphDB
from .utils import load_json, logger, write_json
from .base import (
    BaseKVStorage,
    BaseVectorStorage,
    BaseHypergraphStorage
)


@dataclass
class JsonKVStorage(BaseKVStorage):
    def __post_init__(self):
        working_dir = self.global_config["working_dir"]
        self._file_name = os.path.join(working_dir, f"kv_store_{self.namespace}.json")
        self._data = load_json(self._file_name) or {}
        logger.info(f"Load KV {self.namespace} with {len(self._data)} data")

    async def all_keys(self) -> list[str]:
        return list(self._data.keys())

    async def index_done_callback(self):
        write_json(self._data, self._file_name)

    async def get_by_id(self, id):
        return self._data.get(id, None)

    async def get_by_ids(self, ids, fields=None):
        if fields is None:
            return [self._data.get(id, None) for id in ids]
        return [
            (
                {k: v for k, v in self._data[id].items() if k in fields}
                if self._data.get(id, None)
                else None
            )
            for id in ids
        ]

    async def filter_keys(self, data: list[str]) -> set[str]:
        return set([s for s in data if s not in self._data])

    async def upsert(self, data: dict[str, dict]):
        left_data = {k: v for k, v in data.items() if k not in self._data}
        self._data.update(left_data)
        return left_data

    async def drop(self):
        self._data = {}


@dataclass
class NanoVectorDBStorage(BaseVectorStorage):
    cosine_better_than_threshold: float = 0.2

    def __post_init__(self):
        self._client_file_name = os.path.join(
            self.global_config["working_dir"], f"vdb_{self.namespace}.json"
        )
        self._max_batch_size = self.global_config["embedding_batch_num"]
        self._client = NanoVectorDB(
            self.embedding_func.embedding_dim, storage_file=self._client_file_name
        )
        self.cosine_better_than_threshold = self.global_config.get(
            "cosine_better_than_threshold", self.cosine_better_than_threshold
        )

    async def upsert(self, data: dict[str, dict]):
        logger.info(f"Inserting {len(data)} vectors to {self.namespace}")
        if not len(data):
            logger.warning("You insert an empty data to vector DB")
            return []
        list_data = [
            {
                "__id__": k,
                **{k1: v1 for k1, v1 in v.items() if k1 in self.meta_fields},
            }
            for k, v in data.items()
        ]
        contents = [v["content"] for v in data.values()]
        batches = [
            contents[i : i + self._max_batch_size]
            for i in range(0, len(contents), self._max_batch_size)
        ]
        embeddings_list = await asyncio.gather(
            *[self.embedding_func(batch) for batch in batches]
        )
        embeddings = np.concatenate(embeddings_list)
        for i, d in enumerate(list_data):
            d["__vector__"] = embeddings[i]
        results = self._client.upsert(datas=list_data)
        return results

    async def query(self, query: str, top_k=5):
        embedding = await self.embedding_func([query])
        embedding = embedding[0]
        results = self._client.query(
            query=embedding,
            top_k=top_k,
            better_than_threshold=self.cosine_better_than_threshold,
        )
        results = [
            {**dp, "id": dp["__id__"], "distance": dp["__metrics__"]} for dp in results
        ]
        return results

    async def index_done_callback(self):
        self._client.save()


@dataclass
class HypergraphStorage(BaseHypergraphStorage):

    @staticmethod
    def load_hypergraph(file_name) -> HypergraphDB:
        if os.path.exists(file_name):
            pre_hypergraph = HypergraphDB()
            pre_hypergraph.load(file_name)
            return pre_hypergraph
        return None

    @staticmethod
    def write_hypergraph(hypergraph: HypergraphDB, file_name):
        logger.info(
            f"Writing hypergraph with {hypergraph.num_v} vertices, {hypergraph.num_e} hyperedges"
        )
        hypergraph.save(file_name)

    def __post_init__(self):
        self._hgdb_file = os.path.join(
            self.global_config["working_dir"], f"hypergraph_{self.namespace}.hgdb"
        )
        preloaded_hypergraph = HypergraphStorage.load_hypergraph(self._hgdb_file)
        if preloaded_hypergraph is not None:
            logger.info(
                f"Loaded hypergraph from {self._hgdb_file} with {preloaded_hypergraph.num_v} vertices, {preloaded_hypergraph.num_e} hyperedges"
            )
        self._hg = preloaded_hypergraph or HypergraphDB()

    async def index_done_callback(self):
        HypergraphStorage.write_hypergraph(self._hg, self._hgdb_file)

    async def has_vertex(self, v_id: Any) -> bool:
        return self._hg.has_v(v_id)

    async def has_hyperedge(self, e_tuple: Union[List, Set, Tuple]) -> bool:
        return self._hg.has_e(e_tuple)

    async def get_vertex(self, v_id: str, default: Any = None) :
        return self._hg.v(v_id)

    async def get_hyperedge(self, e_tuple: Union[List, Set, Tuple], default: Any = None) :
        return self._hg.e(e_tuple)

    async def get_all_vertices(self):
        return self._hg.all_v

    async def get_all_hyperedges(self):
        return self._hg.all_e

    async def get_num_of_vertices(self):
        return self._hg.num_v

    async def get_num_of_hyperedges(self):
        return self._hg.num_e

    async def upsert_vertex(self, v_id: Any, v_data: Optional[Dict] = None) :
        return self._hg.add_v(v_id, v_data)

    async def upsert_hyperedge(self, e_tuple: Union[List, Set, Tuple], e_data: Optional[Dict] = None) :
        return self._hg.add_e(e_tuple, e_data)

    async def remove_vertex(self, v_id: Any) :
        return self._hg.remove_v(v_id)

    async def remove_hyperedge(self, e_tuple: Union[List, Set, Tuple]) :
        return self._hg.remove_e(e_tuple)

    async def vertex_degree(self, v_id: Any) -> int:
        return self._hg.degree_v(v_id)

    async def hyperedge_degree(self, e_tuple: Union[List, Set, Tuple]) -> int:
        return self._hg.degree_e(e_tuple)

    async def get_nbr_e_of_vertex(self, e_tuple: Union[List, Set, Tuple]) -> list:
        """
            Return the incident hyperedges of the vertex.
        """
        return self._hg.nbr_e_of_v(e_tuple)

    async def get_nbr_v_of_hyperedge(self, v_id: Any, exclude_self=True) -> list:
        """
            Return the incident vertices of the hyperedge.
        """
        return self._hg.nbr_v_of_e(v_id)

    async def get_nbr_v_of_vertex(self, v_id: Any, exclude_self=True) -> list:
        """
            Return the neighbors of the vertex.
        """
        return self._hg.nbr_v(v_id)
