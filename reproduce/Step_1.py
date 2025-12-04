import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

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
        extra_body={"enable_thinking": False},
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
            time.sleep(10)
    if retries == max_retries:
        print("Insertion failed after exceeding the maximum number of retries")


if __name__ == "__main__":
    data_name = "mix"
    WORKING_DIR = Path("caches") / data_name
    WORKING_DIR.mkdir(parents=True, exist_ok=True)
    rag = HyperRAG(
        working_dir=WORKING_DIR,
        embedding_batch_num=8,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM, max_token_size=8192, func=embedding_func
        ),
    )
    insert_text(rag, f"caches/{data_name}/contexts/{data_name}_unique_contexts.json")
