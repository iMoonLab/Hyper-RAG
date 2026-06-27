import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from openai import OpenAI
from tqdm import tqdm

# 允许脚本直接从 reproduce/ 目录外导入项目根目录里的配置文件。
sys.path.append(str(Path(__file__).resolve().parent.parent))

from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from hyperrag.env import normalize_proxy_env
try:
    from .pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME
except ImportError:
    from pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME

normalize_proxy_env()


def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
    """同步 LLM 调用：用于根据 context 生成评测问题。

    这里没有走 hyperrag.llm 的缓存封装，因为 Step_2 只是生成问题数据，
    不参与 HyperRAG 建库或检索流程。
    """
    openai_client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.extend(history_messages)
    messages.append({"role": "user", "content": prompt})

    response = openai_client.chat.completions.create(
        model=LLM_MODEL, messages=messages, **kwargs
    )
    return response.choices[0].message.content


question_prompt = {
    # 一阶段问题：只问一个具体细节，用来测试普通单跳事实检索能力。
    1: """
            You are a professional teacher, and you are now asked to design a question that meets the requirements based on the reference.
            ################
            Reference:
            Given the following fragment of a data set:
            {context}
            ################
            Requirements:
            1. This question should be of the question-and-answer (QA) type, and no answer is required.
            2. This question mainly tests the details of the information and knowledge in the reference. Avoid general and macro question.
            3. The question must not include any conjunctions such as "specifically", "particularly", "and", "or", "and how", "and what" or similar phrases that imply additional inquiries.
            4. The question must focus on a single aspect or detail from the reference, avoiding the combination of multiple inquiries.
            5. Please design question from the professional perspective and domain factors covered by the reference.
            6. This question need to be meaningful and difficult, avoiding overly simplistic inquiries.
            7. This question should be based on the complete context, so that the respondent knows what you are asking and doesn't get confused.
            8. State the question directly in a single sentence, without statements like "How in this reference?" or "What about this data set?" or "as described in the reference."
            ################
            Output the content of question in the following structure:
            {{
                "Question": [question description],
            }}
        """,
    # 二阶段问题：把两个递进子问题放进同一句，测试更复杂的组合检索能力。
    2: """
            You are a professional teacher, and your task is to design a single question that contains two interconnected sub-questions,
            demonstrating a progressive relationship based on the reference.
            ################
            Reference:
            Given the following fragment of a data set:
            {context}
            ################
            Requirements:
            1. This question should be of the question-and-answer (QA) type, and no answer is required.
            2. The question must include two sub-questions connected by transitional phrases such as "and" or "specifically," indicating progression.
            3. Focus on testing the details of the information and knowledge in the reference. Avoid general and macro questions.
            4. Design the question from a professional perspective, considering the domain factors covered by the reference.
            5. Ensure the question is meaningful and challenging, avoiding trivial inquiries.
            6. The question should be based on the complete context, ensuring clarity for the respondent.
            7. State the question directly in a single sentence, without introductory phrases like "How in this reference?" or "What about this data set?".
            ################
            Output the content of the question in the following structure:
            {{
            "Question": [question description],
            }}
        """,
    # 三阶段问题：包含三个递进子问题，进一步提高查询复杂度。
    3: """
            You are a professional teacher, and your task is to design a single question that contains three interconnected sub-questions,
            demonstrating a progressive relationship based on the reference.
            ################
            Reference:
            Given the following fragment of a data set:
            {context}
            ################
            Requirements:
            1. This question should be of the question-and-answer (QA) type, and no answer is required.
            2. The question must include three sub-questions connected by transitional phrases such as "and" or "specifically," indicating progression.
            3. Focus on testing the details of the information and knowledge in the reference. Avoid general and macro questions.
            4. Design the question from a professional perspective, considering the domain factors covered by the reference.
            5. Ensure the question is meaningful and challenging, avoiding trivial inquiries.
            6. The question should be based on the complete context, ensuring clarity for the respondent.
            7. State the question directly in a single sentence, without introductory phrases like "How in this reference?" or "What about this data set?".
            ################
            Output the content of the question in the following structure:
            {{
            "Question": [question description],
            }}
        """,
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="从 context 中抽样调用 LLM 生成评测问题")
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"读取 caches/<name>/contexts（默认 {DEFAULT_DATA_NAME!r}）",
    )
    args = parser.parse_args()
    data_name = args.data_name

    # 当前脚本默认生成二阶段问题；如果要生成 1/3 阶段问题，可以改这里。
    question_stage = 2

    # Step_0 的输出会放在 caches/<data_name>/contexts/ 下。
    WORKING_DIR = Path("caches") / data_name

    # 每次抽取连续 3 个 context 拼接成一个更大的参考片段，
    # 让问题生成器有足够上下文构造递进问题。
    len_big_chunks = 3

    # question_list 保存最终问题；reference_list 保存问题对应的参考原文，
    # 后续 scoring-based 评估可把 reference 当作参考答案材料。
    question_list, reference_list = [], []
    with open(
        f"caches/{data_name}/contexts/{data_name}_unique_contexts.json",
        mode="r",
        encoding="utf-8",
    ) as f:
        # 读取 Step_0 抽出的去重 context 列表。
        unique_contexts = json.load(f)

    # 这里只生成 5 个问题，适合快速复现实验流程。
    # 如果要扩大评测集，可以调大 max_cnt。
    cnt, max_cnt = 0, 5

    # 防止数据量太小时随机索引越界。
    max_idx = max(len(unique_contexts) - len_big_chunks - 1, 1)

    with tqdm(
        total=max_cnt, desc=f"Extracting {question_stage}-stage questions"
    ) as pbar:
        while cnt < max_cnt:
            # 随机选择一个起点，取连续 context 拼成生成问题的 reference。
            idx = np.random.randint(0, max_idx)
            big_chunks = unique_contexts[idx : idx + len_big_chunks]
            context = "".join(big_chunks)

            # 把 reference 填进对应阶段的问题生成 prompt。
            prompt = question_prompt[question_stage].format(context=context)
            response = llm_model_func(prompt)

            # LLM 理想输出是 {"Question": "..."}，但实际可能带解释文本。
            # 这里先从第一个 "{" 开始尝试 JSON 解析。
            question_text = None
            brace = response.find("{")
            if brace != -1:
                try:
                    obj, _ = json.JSONDecoder().raw_decode(response[brace:])
                    if isinstance(obj, dict) and "Question" in obj:
                        q = obj["Question"]
                        if isinstance(q, str) and q.strip():
                            question_text = q.strip()
                except json.JSONDecodeError:
                    pass
            if question_text is None:
                # 兜底：如果 JSON 解析失败，用正则尽量提取 "Question" 字段。
                m = re.search(r'"Question"\s*:\s*"(.*?)"\s*}', response, re.DOTALL)
                if m:
                    question_text = m.group(1).strip()
            if not question_text:
                # 本轮失败不计数，继续抽样生成下一个问题。
                print("No question found in the response.")
                continue

            question_list.append(question_text)
            reference_list.append(context)

            cnt += 1
            pbar.update(1)

    # 保存问题和对应 reference：
    # - questions/2_stage.json 是 Step_3 的输入；
    # - questions/2_stage_ref.json 可供评估脚本使用。
    prefix = f"caches/{data_name}/questions/{question_stage}_stage"
    question_file_path = Path(f"{prefix}.json")
    ref_file_path = Path(f"{prefix}_ref.json")
    question_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{prefix}.json", "w", encoding="utf-8") as f:
        json.dump(question_list, f, ensure_ascii=False, indent=4)
    with open(f"{prefix}_ref.json", "w", encoding="utf-8") as f:
        json.dump(reference_list, f, ensure_ascii=False, indent=4)

    print(f"questions written to {question_file_path}")
