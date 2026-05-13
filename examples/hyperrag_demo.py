import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

# 在 import numpy 之前设置，避免 Windows 上与其它 OpenMP 运行库冲突（见 hyperrag/__init__.py 说明）。
if sys.platform == "win32":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import time
import numpy as np

from hyperrag import HyperRAG, QueryParam
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


def insert_texts_with_retry(rag, texts, retries=3, delay=5):
    for _ in range(retries):
        try:
            rag.insert(texts)
            return
        except Exception as e:
            print(
                f"Error occurred during insertion: {e}. Retrying in {delay} seconds..."
            )
            time.sleep(delay)
    raise RuntimeError("Failed to insert texts after multiple retries.")


if __name__ == "__main__":
    data_name = "mock"
    WORKING_DIR = Path("caches") / data_name
    WORKING_DIR.mkdir(parents=True, exist_ok=True)
    # 嵌入走公网：较大 batch + 适中并发，减轻 403/429；自建 chat 可提高 llm_model_max_async。
    rag = HyperRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM, max_token_size=8192, func=embedding_func
        ),
        embedding_batch_num=64,
        embedding_func_max_async=4,
        llm_model_max_async=16,
    )

    # read the text file
    mock_data_file_path = Path("examples/mock_data.txt")
    with open(mock_data_file_path, "r", encoding="utf-8") as file:
        texts = file.read()
    # 默认可跑全书；设 HYPERRAG_DEMO_TRUNCATE_BYTES=15000 等可缩短输入，便于阶段 A 快速冒烟（仍走 insert + 三模式 query）。
    _trunc = os.environ.get("HYPERRAG_DEMO_TRUNCATE_BYTES", "").strip()
    if _trunc.isdigit():
        texts = texts[: int(_trunc)]

    # Insert the text into the RAG
    insert_texts_with_retry(rag, texts)

    # Perform different types of queries and handle potential errors
    try:
        print("\n\n\nPerforming Naive RAG...")
        print(
            rag.query(
                "What are the top themes in this story?", 
                param=QueryParam(mode="naive")
            )
        )
    except Exception as e:
        print(f"Error performing naive-rag search: {e}")

    try:
        print("\n\n\nPerforming Hyper-RAG...")
        print(
            rag.query(
                "What are the top themes in this story?", 
                param=QueryParam(mode="hyper")
            )
        )
    except Exception as e:
        print(f"Error performing hyper-rag search: {e}")

    try:
        print("\n\n\nPerforming Hyper-RAG-Lite...")
        print(
            rag.query(
                "What are the top themes in this story?",
                param=QueryParam(mode="hyper-lite"),
            )
        )
    except Exception as e:
        print(f"Error performing hyper-rag-lite search: {e}")
