import argparse
import json
import sys
from pathlib import Path

import numpy as np
from tqdm import tqdm

# 让脚本可以直接导入项目根目录下的 hyperrag 包和 my_config.py。
sys.path.append(str(Path(__file__).resolve().parent.parent))

from hyperrag import HyperRAG, QueryParam
from hyperrag.llm import openai_complete_if_cache, openai_embedding
from hyperrag.utils import EmbeddingFunc, always_get_an_event_loop
from my_config import EMB_API_KEY, EMB_BASE_URL, EMB_DIM, EMB_MODEL
from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
try:
    from .pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME
except ImportError:
    from pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME


async def llm_model_func(
    prompt, system_prompt=None, history_messages=[], **kwargs
) -> str:
    """给 HyperRAG 查询阶段注入的 LLM 调用函数。

    查询时 LLM 会被用于关键词抽取、上下文组织后的最终回答生成等步骤。
    openai_complete_if_cache 会结合 HyperRAG 的 llm_response_cache 做缓存。
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
    """给 HyperRAG 查询阶段注入的 embedding 函数。

    查询问题会被 embedding 后拿去查 chunks/entities/relationships 向量库。
    这里的 EMB_DIM 必须和 Step_1 建库时使用的 embedding 维度一致。
    """
    return await openai_embedding(
        texts,
        model=EMB_MODEL,
        api_key=EMB_API_KEY,
        base_url=EMB_BASE_URL,
    )


def extract_queries(file_path):
    """读取 Step_2 生成的问题列表。"""
    with open(file_path, "r", encoding="utf-8") as file:
        query_list = json.load(file)
    return query_list


async def process_query(query_text, rag_instance, query_param):
    """对单个问题调用 HyperRAG.aquery，并把成功/失败结果拆开返回。"""
    try:
        # 这是 Step_3 进入核心方法本体的位置。
        # query_param.mode 决定会走 hyper、hyper-lite 还是 naive。
        result = await rag_instance.aquery(query_text, param=query_param)
        return {"query": query_text, "result": result}, None
    except Exception as e:
        print("error", e)
        return None, {"query": query_text, "error": str(e)}


def run_queries_and_save_to_json(
    queries, rag_instance, query_param, output_file, error_file
):
    """批量执行问题，并把正常结果和错误结果分别写入文件。

    输出目录默认是 caches/<data_name>/response/。
    例如 mode=hyper 时，会写出 hyper_2_stage_result.json 和
    hyper_2_stage_errors.json。
    """
    loop = always_get_an_event_loop()

    with open(output_file, "w", encoding="utf-8") as result_file, open(
        error_file, "w", encoding="utf-8"
    ) as err_file:
        # 手动流式写 JSON 数组，避免所有结果都积在内存里。
        result_file.write("[\n")
        first_entry = True

        for query_text in tqdm(queries, desc="Processing queries", unit="query"):
            result, error = loop.run_until_complete(
                process_query(query_text, rag_instance, query_param)
            )
            if result:
                # 正常回答写入 result 文件。
                if not first_entry:
                    result_file.write(",\n")
                json.dump(result, result_file, ensure_ascii=False, indent=4)
                first_entry = False
            elif error:
                # 单题失败不会中断整个批处理，而是写入 errors 文件方便排查。
                json.dump(error, err_file, ensure_ascii=False, indent=4)
                err_file.write("\n")

        result_file.write("\n]")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="对 questions 调用 HyperRAG.aquery，并写入 response/")
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"HyperRAG working_dir = caches/<name>（默认 {DEFAULT_DATA_NAME!r}）",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="naive",
        choices=["naive", "hyper", "hyper-lite"],
        help="QueryParam.mode（可多次运行本脚本，分别生成各 mode 结果）",
    )
    args = parser.parse_args()
    data_name = args.data_name
    mode = args.mode

    # 与 Step_2 保持一致：当前默认读取二阶段问题。
    question_stage = 2

    # Step_1 建好的全部索引和超图都在这个目录。
    WORKING_DIR = Path("caches") / data_name

    # Step_2 生成的问题文件，是本脚本的输入。
    question_file_path = Path(
        WORKING_DIR / f"questions/{question_stage}_stage.json"
    )
    queries = extract_queries(question_file_path)

    # 重新实例化 HyperRAG 时，storage 会从 WORKING_DIR 里加载已有的
    # kv_store_*.json、vdb_*.json 和 hypergraph_*.hgdb，而不是重新建库。
    rag = HyperRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM, max_token_size=8192, func=embedding_func
        ),
        llm_model_max_async=32,
        embedding_func_max_async=4,
    )

    # mode 是实验对照的核心开关：
    # - naive：只查 chunk 向量库；
    # - hyper：查实体、关系和超图上下文；
    # - hyper-lite：只查实体相关上下文，速度更轻。
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
