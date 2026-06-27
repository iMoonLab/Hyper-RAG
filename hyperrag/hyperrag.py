"""HyperRAG 的核心门面类。

阅读建议：
1. 先看 `__post_init__`：理解项目启动时会创建哪些存储对象。
2. 再看 `ainsert`：理解原始文本如何变成 chunk、向量库和超图。
3. 最后看 `aquery` / `astream_query`：理解不同查询模式如何路由到 operate.py。

这个文件本身更像“调度器”，真正的算法细节在 operate.py，
真正的落盘实现细节在 storage.py。
"""

import os
import asyncio
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import partial
from typing import Type, cast

from .chunking import chunking_by_token_size
from .indexing import extract_entities
from .query_modes import graph_query, hyper_query, hyper_query_lite, llm_query, naive_query
from .query_stream import (
    hyper_query_lite_stream,
    hyper_query_stream,
    llm_query_stream,
    naive_query_stream,
)
from .llm import (
    gpt_4o_mini_complete,
    openai_embedding,
)

from .storage import (
    JsonKVStorage,
    NanoVectorDBStorage,
    HypergraphStorage,
)


from .utils import (
    EmbeddingFunc,
    compute_mdhash_id,
    limit_async_func_call,
    convert_response_to_json,
    logger,
    set_logger,
    limit_async_gen_call
)
from .base import (
    BaseKVStorage,
    BaseVectorStorage,
    StorageNameSpace,
    QueryParam,
    BaseHypergraphStorage,
)

def always_get_an_event_loop() -> asyncio.AbstractEventLoop:
    """同步 API 调异步逻辑时使用的事件循环兜底函数。"""
    try:
        return asyncio.get_event_loop()

    except RuntimeError:
        logger.info("Creating a new event loop in main thread.")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        return loop


@dataclass
class HyperRAG:
    """Hyper-RAG 方法的核心入口类。

    一个 HyperRAG 实例对应一个 working_dir。这个目录下会保存：
    - kv_store_full_docs.json：完整文档
    - kv_store_text_chunks.json：切块后的文本
    - kv_store_llm_response_cache.json：LLM 调用缓存
    - vdb_chunks.json：chunk 向量库
    - vdb_entities.json：实体向量库
    - vdb_relationships.json：关系/超边向量库
    - hypergraph_chunk_entity_relation.hgdb：实体-关系超图
    """
    working_dir: str = field(
        default_factory=lambda: f"./HyperRAG_cache_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
    )
    # print(working_dir)

    current_log_level = logger.level
    log_level: str = field(default=current_log_level)

    # 文本切块配置：按 token 数切 chunk，不是语义切分。
    chunk_token_size: int = 1200
    chunk_overlap_token_size: int = 100
    tiktoken_model_name: str = "gpt-4o-mini"

    # 实体/关系抽取配置：控制 LLM 抽取、补抽和摘要压缩长度。
    entity_extract_max_gleaning: int = 1
    entity_summary_to_max_tokens: int = 500
    entity_additional_properties_to_max_tokens: int = 250
    relation_summary_to_max_tokens: int = 750
    relation_keywords_to_max_tokens: int = 100

    embedding_func: EmbeddingFunc = field(default_factory=lambda: openai_embedding)
    embedding_batch_num: int = 8
    embedding_func_max_async: int = 16

    # LLM 配置：用于实体抽取、关键词抽取、关系摘要和最终回答。
    llm_model_func: callable = gpt_4o_mini_complete  # hf_model_complete#
    # llm_model_name: str = "meta-llama/Llama-3.2-1B-Instruct"  #'meta-llama/Llama-3.2-1B'#'google/gemma-2-2b-it'
    llm_model_name: str = ""
    llm_model_max_token_size: int = 32768
    llm_model_max_async: int = 16
    llm_model_kwargs: dict = field(default_factory=dict)

    llm_model_stream_func: callable = None

    # 存储实现类：默认使用本地 JSON KV、NanoVectorDB 和 HypergraphDB。
    key_string_value_json_storage_cls: Type[BaseKVStorage] = JsonKVStorage
    vector_db_storage_cls: Type[BaseVectorStorage] = NanoVectorDBStorage
    vector_db_storage_cls_kwargs: dict = field(default_factory=dict)
    hypergraph_storage_cls: Type[BaseHypergraphStorage] = HypergraphStorage
    enable_llm_cache: bool = True

    # 扩展参数：保留给外部增强逻辑或替换 JSON 解析函数。
    addon_params: dict = field(default_factory=dict)
    convert_response_to_json_func: callable = convert_response_to_json

    def __post_init__(self):
        """初始化日志、KV 存储、向量库、超图库，并包装 LLM/embedding 并发限制。"""
        log_file = os.path.join(self.working_dir, "HyperRAG.log")
        set_logger(log_file)
        logger.setLevel(self.log_level)

        logger.info(f"Logger initialized for working directory: {self.working_dir}")

        _print_config = ",\n  ".join([f"{k} = {v}" for k, v in asdict(self).items()])
        logger.debug(f"HyperRAG init with param:\n  {_print_config}\n")

        if not os.path.exists(self.working_dir):
            logger.info(f"Creating working directory {self.working_dir}")
            os.makedirs(self.working_dir)

        # 完整文档 KV：doc-id -> {"content": 原始输入文本}
        self.full_docs = self.key_string_value_json_storage_cls(
            namespace="full_docs", global_config=asdict(self)
        )

        # 切块文本 KV：chunk-id -> {"content", "tokens", "full_doc_id", ...}
        # 查询阶段最终会根据 source_id 回到这里取原文片段。
        self.text_chunks = self.key_string_value_json_storage_cls(
            namespace="text_chunks", global_config=asdict(self)
        )

        # LLM 调用缓存：prompt/message hash -> LLM 返回值。
        # 实体抽取、关键词抽取、最终回答都可能复用这个缓存。
        self.llm_response_cache = (
            self.key_string_value_json_storage_cls(
                namespace="llm_response_cache", global_config=asdict(self)
            )
            if self.enable_llm_cache
            else None
        )
        """
            download from hgdb_path
        """
        # 超图存储：实体是 vertex，实体之间的低阶/高阶关系是 hyperedge。
        self.chunk_entity_relation_hypergraph = self.hypergraph_storage_cls(
            namespace="chunk_entity_relation", global_config=asdict(self)
        )

        # 给 embedding 函数套并发限制，避免批量建库时把外部 embedding 服务打爆。
        self.embedding_func = limit_async_func_call(self.embedding_func_max_async)(
            self.embedding_func
        )

        # 实体向量库：内容来自实体描述，额外保留 entity_name 方便回超图查 vertex。
        self.entities_vdb = self.vector_db_storage_cls(
            namespace="entities",
            global_config=asdict(self),
            embedding_func=self.embedding_func,
            meta_fields={"entity_name"},
        )
        self.relationships_vdb = self.vector_db_storage_cls(
            namespace="relationships",
            global_config=asdict(self),
            embedding_func=self.embedding_func,
            meta_fields={"id_set"},
        )
        # 原文 chunk 向量库：naive RAG 模式会直接查它。
        self.chunks_vdb = self.vector_db_storage_cls(
            namespace="chunks",
            global_config=asdict(self),
            embedding_func=self.embedding_func,
        )

        self.llm_model_func = limit_async_func_call(self.llm_model_max_async)(
            partial(
                self.llm_model_func,
                hashing_kv=self.llm_response_cache,
                **self.llm_model_kwargs,
            )
        )

        if getattr(self, "llm_model_stream_func", None) is not None:
            # 先把 hashing_kv 注入到 stream func（供 openai_complete_stream_if_cache 使用）
            self.llm_model_stream_func = limit_async_gen_call(self.llm_model_max_async)(
                partial(
                    self.llm_model_stream_func,
                    hashing_kv=self.llm_response_cache,
                    **self.llm_model_kwargs,
                )
            )

    def insert(self, string_or_strings):
        """同步建库入口；内部转调异步 ainsert。"""
        loop = always_get_an_event_loop()
        return loop.run_until_complete(self.ainsert(string_or_strings))

    async def ainsert(self, string_or_strings):
        """异步建库入口：原文 -> chunk -> 向量库 -> 实体/超边抽取 -> 超图落盘。"""
        try:
            if isinstance(string_or_strings, str):
                string_or_strings = [string_or_strings]

            # 用内容 hash 生成稳定 doc-id；重复插入同一段文本会被过滤。
            new_docs = {
                compute_mdhash_id(c.strip(), prefix="doc-"): {"content": c.strip()}
                for c in string_or_strings
            }
            _add_doc_keys = await self.full_docs.filter_keys(list(new_docs.keys()))
            new_docs = {k: v for k, v in new_docs.items() if k in _add_doc_keys}
            if not len(new_docs):
                logger.warning("All docs are already in the storage")
                return
            # ----------------------------------------------------------------------------
            logger.info(f"[New Docs] inserting {len(new_docs)} docs")

            # 按 token 长度切块，并为每个 chunk 生成稳定 chunk-id。
            inserting_chunks = {}
            for doc_key, doc in new_docs.items():
                chunks = {
                    compute_mdhash_id(dp["content"], prefix="chunk-"): {
                        **dp,
                        "full_doc_id": doc_key,
                    }
                    for dp in chunking_by_token_size(
                        doc["content"],
                        overlap_token_size=self.chunk_overlap_token_size,
                        max_token_size=self.chunk_token_size,
                        tiktoken_model=self.tiktoken_model_name,
                    )
                }
                inserting_chunks.update(chunks)
            _add_chunk_keys = await self.text_chunks.filter_keys(
                list(inserting_chunks.keys())
            )
            inserting_chunks = {
                k: v for k, v in inserting_chunks.items() if k in _add_chunk_keys
            }
            if not len(inserting_chunks):
                logger.warning("All chunks are already in the storage")
                return
            # ----------------------------------------------------------------------------
            logger.info(f"[New Chunks] inserting {len(inserting_chunks)} chunks")

            # chunk 先进入向量库，支撑 naive 模式的“问题 -> 原文片段”检索。
            await self.chunks_vdb.upsert(inserting_chunks)
            # ----------------------------------------------------------------------------
            logger.info("[Entity Extraction]...")
            # 从 chunk 中抽实体和低阶/高阶关系：
            # - 实体写入超图 vertex 和 entities_vdb
            # - 关系写入超图 hyperedge 和 relationships_vdb
            maybe_new_kg = await extract_entities(
                inserting_chunks,
                knowledge_hypergraph_inst=self.chunk_entity_relation_hypergraph,
                entity_vdb=self.entities_vdb,
                relationships_vdb=self.relationships_vdb,
                global_config=asdict(self),
            )
            if maybe_new_kg is None:
                logger.warning("No new entities and relationships found")
                return
            # ----------------------------------------------------------------------------
            self.chunk_entity_relation_hypergraph = maybe_new_kg
            # 抽取成功后再提交 full docs 和 chunks，避免半成品数据污染索引。
            await self.full_docs.upsert(new_docs)
            await self.text_chunks.upsert(inserting_chunks)
        finally:
            await self._insert_done()

    async def _insert_done(self):
        """建库阶段统一提交各类存储：JSON 写盘、向量库保存、超图保存。"""
        tasks = []
        for storage_inst in [
            self.full_docs,
            self.text_chunks,
            self.llm_response_cache,
            self.entities_vdb,
            self.relationships_vdb,
            self.chunks_vdb,
            self.chunk_entity_relation_hypergraph,
        ]:
            if storage_inst is None:
                continue
            tasks.append(cast(StorageNameSpace, storage_inst).index_done_callback())
        await asyncio.gather(*tasks)

    def query(self, query: str, param: QueryParam = QueryParam()):
        """同步查询入口；内部转调异步 aquery。"""
        loop = always_get_an_event_loop()
        return loop.run_until_complete(self.aquery(query, param))

    async def aquery(self, query: str, param: QueryParam = QueryParam()):
        """异步查询入口，根据 mode 路由到不同检索策略。"""
        
        if param.mode == "hyper":
            response = await hyper_query(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.relationships_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif param.mode == "hyper-lite":
            response = await hyper_query_lite(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif param.mode == "graph":
            response = await graph_query(
                query,
                self.chunk_entity_relation_hypergraph,
                self.entities_vdb,
                self.relationships_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif param.mode == "naive":
            response = await naive_query(
                query,
                self.chunks_vdb,
                self.text_chunks,
                param,
                asdict(self),
            )
        elif param.mode == "llm":
            response = await llm_query(
                query,
                param,
                asdict(self),
            )
        else:
            raise ValueError(f"Unknown mode {param.mode}")
        await self._query_done()
        return response

    async def astream_query(self, query: str, param: QueryParam = QueryParam()):
        """
        流式查询：返回 async generator（逐 token / 逐块）
        依赖 self.llm_model_stream_func，不提供则抛错。
        """
        if self.llm_model_stream_func is None:
            raise AttributeError("llm_model_stream_func is not set, streaming is unavailable.")

        # 把 stream func 放进 global_config
        cfg = asdict(self)
        cfg["llm_model_stream_func"] = self.llm_model_stream_func

        if param.mode == "hyper":
            async for tok in hyper_query_stream(
                    query,
                    self.chunk_entity_relation_hypergraph,
                    self.entities_vdb,
                    self.relationships_vdb,
                    self.text_chunks,
                    param,
                    cfg,
            ):
                yield tok

        elif param.mode == "hyper-lite":
            async for tok in hyper_query_lite_stream(
                    query,
                    self.chunk_entity_relation_hypergraph,
                    self.entities_vdb,
                    self.text_chunks,
                    param,
                    cfg,
            ):
                yield tok

        elif param.mode == "naive":
            async for tok in naive_query_stream(
                    query,
                    self.chunks_vdb,
                    self.text_chunks,
                    param,
                    cfg,
            ):
                yield tok

        elif param.mode == "llm":
            async for tok in llm_query_stream(query, param, cfg):
                yield tok

        else:
            raise ValueError(f"Unknown mode {param.mode}")

        await self._query_done()


    async def _query_done(self):
        """查询结束后提交查询侧可能产生的状态，目前主要是 LLM cache。"""
        tasks = []
        for storage_inst in [self.llm_response_cache]:
            if storage_inst is None:
                continue
            tasks.append(cast(StorageNameSpace, storage_inst).query_done_callback())
        await asyncio.gather(*tasks)
