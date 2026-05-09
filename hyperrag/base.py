from dataclasses import dataclass, field
from typing import TypedDict, Union, Literal, Generic, TypeVar, Any, Tuple, List, Set, Optional, Dict

from .utils import EmbeddingFunc

TextChunkSchema = TypedDict(
    "TextChunkSchema",
    {"tokens": int, "content": str, "full_doc_id": str, "chunk_order_index": int},
)

T = TypeVar("T")


@dataclass
class QueryParam:
    mode: Literal["hyper", "hyper-lite", "graph", "naive", "llm"] = "hyper"
    only_need_context: bool = False
    response_type: str = "Multiple Paragraphs"
    # Number of top-k items to retrieve; corresponds to entities in "local" mode and relationships in "global" mode.
    top_k: int = 60
    # Number of tokens for the original chunks.
    max_token_for_text_unit: int = 1600
    # Number of tokens for the entity descriptions
    max_token_for_entity_context: int = 300
    # Number of tokens for the relationship descriptions
    max_token_for_relation_context: int = 1600
    # return type
    return_type: Literal["json", "text"] = "text"


@dataclass
class StorageNameSpace:
    namespace: str
    global_config: dict

    async def index_done_callback(self):
        """commit the storage operations after indexing"""
        pass

    async def query_done_callback(self):
        """commit the storage operations after querying"""
        pass


@dataclass
class BaseVectorStorage(StorageNameSpace):
    embedding_func: EmbeddingFunc
    meta_fields: set = field(default_factory=set)

    async def query(self, query: str, top_k: int) -> list[dict]:
        raise NotImplementedError

    async def upsert(self, data: dict[str, dict]):
        """Use 'content' field from value for embedding, use key as id.
        If embedding_func is None, use 'embedding' field from value
        """
        raise NotImplementedError


@dataclass
class BaseKVStorage(Generic[T], StorageNameSpace):
    async def all_keys(self) -> list[str]:
        raise NotImplementedError

    async def get_by_id(self, id: str) -> Union[T, None]:
        raise NotImplementedError

    async def get_by_ids(
        self, ids: list[str], fields: Union[set[str], None] = None
    ) -> list[Union[T, None]]:
        raise NotImplementedError

    async def filter_keys(self, data: list[str]) -> set[str]:
        """return un-exist keys"""
        raise NotImplementedError

    async def upsert(self, data: dict[str, T]):
        raise NotImplementedError

    async def drop(self):
        raise NotImplementedError

"""
    The BaseHypergraphStorage based on hypergraph-DB
"""
@dataclass
class BaseHypergraphStorage(StorageNameSpace):
    async def has_vertex(self, v_id: Any) -> bool:
        raise NotImplementedError

    async def has_hyperedge(self, e_tuple: Union[List, Set, Tuple]) -> bool:
        raise NotImplementedError

    async def get_vertex(self, v_id: str, default: Any = None) :
        raise NotImplementedError

    async def get_hyperedge(self, e_tuple: Union[List, Set, Tuple], default: Any = None) :
        raise NotImplementedError

    async def get_all_vertices(self):
        raise NotImplementedError

    async def get_all_hyperedges(self):
        raise NotImplementedError

    async def get_num_of_vertices(self):
        raise NotImplementedError

    async def get_num_of_hyperedges(self):
        raise NotImplementedError

    async def upsert_vertex(self, v_id: Any, v_data: Optional[Dict] = None) :
        raise NotImplementedError

    async def upsert_hyperedge(self, e_tuple: Union[List, Set, Tuple], e_data: Optional[Dict] = None) :
        raise NotImplementedError

    async def remove_vertex(self, v_id: Any) :
        raise NotImplementedError

    async def remove_hyperedge(self, e_tuple: Union[List, Set, Tuple]) :
        raise NotImplementedError

    async def vertex_degree(self, v_id: Any) -> int:
        raise NotImplementedError

    async def hyperedge_degree(self, e_tuple: Union[List, Set, Tuple]) -> int:
        raise NotImplementedError

    async def get_nbr_e_of_vertex(self, v_id: Any) -> list:
        raise NotImplementedError

    async def get_nbr_v_of_hyperedge(self, e_tuple: Union[List, Set, Tuple]) -> list:
        raise NotImplementedError

    async def get_nbr_v_of_vertex(self, v_id: Any, exclude_self=True) -> list:
        raise NotImplementedError
