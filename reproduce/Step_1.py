import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME

import time
import numpy as np

from hyperrag import HyperRAG
from hyperrag.utils import EmbeddingFunc
from hyperrag.llm import openai_embedding, openai_complete_if_cache

from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from my_config import EMB_API_KEY, EMB_BASE_URL, EMB_MODEL, EMB_DIM


async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
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
    return await openai_embedding(
        texts,
        model=EMB_MODEL,
        api_key=EMB_API_KEY,
        base_url=EMB_BASE_URL,
    )


def insert_text(rag, file_path, retries=0, max_retries=3):
    with open(file_path, "r", encoding="utf-8") as f:
        unique_contexts = f.read()

    while retries < max_retries:
        try:
            rag.insert(unique_contexts)
            break
        except Exception as e:
            retries += 1
            print(f"Insertion failed, retrying ({retries}/{max_retries}), error: {e}")
            time.sleep(30)
    if retries == max_retries:
        print("Insertion failed after exceeding the maximum number of retries")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将唯一 context JSON 写入 HyperRAG 索引")
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"工作目录 caches/<name>（默认 {DEFAULT_DATA_NAME!r}）",
    )
    data_name = parser.parse_args().data_name
    WORKING_DIR = Path("caches") / data_name
    WORKING_DIR.mkdir(parents=True, exist_ok=True)
    rag = HyperRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM, max_token_size=8192, func=embedding_func
        ),
        # 更大块 → 更少 chunk，降低全量 Neurology 上实体抽取的 LLM 调用量（仍与默认 tiktoken 分块一致）
        chunk_token_size=2400,
        chunk_overlap_token_size=120,
        # 降低并发，减轻 SiliconFlow 等网关的 429 / RetryError
        llm_model_max_async=1,
        embedding_func_max_async=4,
    )
    insert_text(rag, f"caches/{data_name}/contexts/{data_name}_unique_contexts.json")
