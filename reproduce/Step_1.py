import argparse
import sys
import time
from pathlib import Path

import numpy as np

# reproduce/ 目录里的脚本需要导入项目根目录下的 hyperrag 包。
# 直接运行 `python reproduce/Step_1.py` 时，默认 import 路径不一定包含项目根目录，
# 所以这里把父目录加入 sys.path。
sys.path.append(str(Path(__file__).resolve().parent.parent))

from hyperrag import HyperRAG
from hyperrag.llm import openai_complete_if_cache, openai_embedding
from hyperrag.utils import EmbeddingFunc
from my_config import EMB_API_KEY, EMB_BASE_URL, EMB_DIM, EMB_MODEL
from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
try:
    from .pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME
except ImportError:
    from pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME


async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    """给 HyperRAG 注入的 LLM 调用函数。

    HyperRAG 在实体抽取、关系抽取、摘要和最终回答时会调用这个函数。
    具体模型、base_url、api_key 都来自 my_config.py。
    """
    return await openai_complete_if_cache(
        LLM_MODEL,
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL,
        **kwargs,
    )


async def embedding_func(texts: list[str]) -> np.ndarray:
    """给 HyperRAG 注入的 embedding 函数。

    Step_1 建库时会把 chunks、实体、关系写入向量库；
    Step_3 查询时也会用同一套 embedding 配置做相似度检索。
    """
    return await openai_embedding(
        texts,
        model=EMB_MODEL,
        api_key=EMB_API_KEY,
        base_url=EMB_BASE_URL,
    )


def insert_text(rag, file_path, retries=0, max_retries=3):
    """读取 Step_0 生成的 context 文件，并调用 HyperRAG.insert 建索引。

    file_path 默认形如：
    caches/<data_name>/contexts/<data_name>_unique_contexts.json

    rag.insert 内部会完成：
    1. 文本切块；
    2. chunk 向量入库；
    3. LLM 抽取实体和低阶/高阶超边；
    4. 写入实体向量库、关系向量库和 hypergraph hgdb 文件。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        # 注意：这里读出来的是 JSON 文件的原始字符串，而不是 json.load 后的 list。
        # 当前脚本把整个 JSON 文本作为一个大文档交给 HyperRAG.insert。
        unique_contexts = f.read()

    while retries < max_retries:
        try:
            # 这是本脚本最关键的一行：真正进入 hyperrag/ 方法本体。
            rag.insert(unique_contexts)
            break
        except Exception as e:
            # 建库阶段会访问外部 LLM/embedding 服务，可能遇到限流或临时网络错误。
            # 这里用简单重试避免一次失败直接中断整条复现流水线。
            retries += 1
            print(f"Insertion failed, retrying ({retries}/{max_retries}), error: {e}")
            time.sleep(30)
    if retries == max_retries:
        print("Insertion failed after exceeding the maximum number of retries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将 Step_0 生成的 context JSON 写入 HyperRAG 索引")
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"工作目录 caches/<name>（默认 {DEFAULT_DATA_NAME!r}）",
    )
    data_name = parser.parse_args().data_name

    # HyperRAG 的所有持久化产物都会落在这个目录下：
    # kv_store_full_docs.json、kv_store_text_chunks.json、vdb_*.json、
    # hypergraph_chunk_entity_relation.hgdb、HyperRAG.log 等。
    WORKING_DIR = Path("caches") / data_name
    WORKING_DIR.mkdir(parents=True, exist_ok=True)

    # 实例化核心方法类。Step_1 的职责不是实现算法，而是把配置和输入语料
    # 交给 hyperrag.HyperRAG，让它完成建库。
    rag = HyperRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM, max_token_size=8192, func=embedding_func
        ),
        # 更大的 chunk 会减少 chunk 数量，从而降低全量 Neurology 建库时
        # 实体/超边抽取所需的 LLM 调用次数。
        chunk_token_size=2400,
        chunk_overlap_token_size=120,
        # 降低 LLM 并发，减轻 SiliconFlow 等兼容网关的 429 / RetryError 风险。
        llm_model_max_async=1,
        embedding_func_max_async=4,
    )

    # 读取 Step_0 的输出，并开始构建 HyperRAG 所需的全部索引和超图数据。
    insert_text(rag, f"caches/{data_name}/contexts/{data_name}_unique_contexts.json")
