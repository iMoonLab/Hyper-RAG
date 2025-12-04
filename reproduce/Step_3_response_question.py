import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import json
import numpy as np
from tqdm import tqdm

from hyperrag import HyperRAG, QueryParam
from hyperrag.utils import always_get_an_event_loop, EmbeddingFunc
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
        extra_body={"enable_thinking": False},
        **kwargs,
    )


async def embedding_func(texts: list[str]) -> np.ndarray:
    return await openai_embedding(
        texts,
        model=EMB_MODEL,
        api_key=EMB_API_KEY,
        base_url=EMB_BASE_URL,
    )


def extract_queries(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        query_list = json.load(file)
    return query_list


async def process_query(query_text, rag_instance, query_param):
    try:
        result = await rag_instance.aquery(query_text, param=query_param)
        return {"query": query_text, "result": result}, None
    except Exception as e:
        print("error", e)
        return None, {"query": query_text, "error": str(e)}


def run_queries_and_save_to_json(
    queries, rag_instance, query_param, output_file, error_file
):
    loop = always_get_an_event_loop()

    with open(output_file, "a", encoding="utf-8") as result_file, open(
        error_file, "a", encoding="utf-8"
    ) as err_file:
        result_file.write("[\n")
        first_entry = True

        for query_text in tqdm(queries, desc="Processing queries", unit="query"):
            result, error = loop.run_until_complete(
                process_query(query_text, rag_instance, query_param)
            )
            if result:
                if not first_entry:
                    result_file.write(",\n")
                json.dump(result, result_file, ensure_ascii=False, indent=4)
                first_entry = False
            elif error:
                json.dump(error, err_file, ensure_ascii=False, indent=4)
                err_file.write("\n")

        result_file.write("\n]")


if __name__ == "__main__":
    data_name = "test"
    question_stage = 2
    WORKING_DIR = Path("caches") / data_name
    # input questions
    question_file_path = Path(
        WORKING_DIR / f"questions/{question_stage}_stage.json"
    )
    queries = extract_queries(question_file_path)
    # init HyperRAG
    rag = HyperRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_batch_num=8,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM, max_token_size=8192, func=embedding_func
        ),
    )
    # configure query parameters
    mode = "naive"
    # mode = "hyper"
    # mode = "hyper-lite"
    query_param = QueryParam(mode=mode)

    OUT_DIR = WORKING_DIR / "response"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    run_queries_and_save_to_json(
        queries,
        rag,
        query_param,
        OUT_DIR / f"{mode}_{question_stage}_stage_result.json",
        OUT_DIR / f"{mode}_{question_stage}_stage_errors.json",
    )
