import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(_ROOT))

import re
import json
import numpy as np
from tqdm import tqdm
from openai import OpenAI
from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from hyperrag.env import normalize_proxy_env

from reproduce.pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME

normalize_proxy_env()


def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
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


def extract_queries_and_answers(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        query_list = json.load(file)
    queries = [i["query"] for i in query_list]
    answers = [i["result"] for i in query_list]
    return queries, answers


def extract_queries_and_refs(question_json: Path):
    """与 Step_2 一致：questions/<n>_stage.json 与同级 <n>_stage_ref.json。"""
    ref_file_path = question_json.with_name(f"{question_json.stem}_ref.json")
    with open(question_json, "r", encoding="utf-8") as file:
        queries = json.load(file)
    with open(ref_file_path, "r", encoding="utf-8") as file:
        refs = json.load(file)
    return queries, refs


def exam_by_scoring(queries, answers, refs):

    responses = []
    sys_prompt = """
        ---Role---
        You are an expert tasked with evaluating answers to the questions by using the relevant documents based on five criteria:**Comprehensiveness**, **Diversity**,**Empowerment**, **Logical**,and **Readability** .

        """
    for query, answer, reference in tqdm(
        zip(queries, answers, refs), desc="Evaluating answers", total=len(queries)
    ):
        prompt = f"""
            You will evaluate tht answers to the questions by using the relevant documents based on five criteria:**Comprehensiveness**, **Diversity**,**Empowerment**, **Logical**,and **Readability** .

            - **Comprehensiveness** -
            Measure whether the answer comprehensively covers all key aspects of the question and whether there are omissions.
            Level   | score range | description
            Level 1 | 0-20   | The answer is extremely one-sided, leaving out key parts or important aspects of the question.
            Level 2 | 20-40  | The answer has some content, but it misses many important aspects of the question and is not comprehensive enough.
            Level 3 | 40-60  | The answer is more comprehensive, covering the main aspects of the question, but there are still some omissions.
            Level 4 | 60-80  | The answer is comprehensive, covering most aspects of the question, with few omissions.
            Level 5 | 80-100 | The answer is extremely comprehensive, covering all aspects of the question with no omissions, enabling the reader to gain a complete understanding.

            - **Diversity** -
            Measure the richness of the answer content, including not only the direct answer to the question, but also the background knowledge related to the question, extended information, case studies, etc.
            Level   | score range | description
            Level 1 | 0-20   | The answer is extremely sparse, providing only direct answers to questions without additional information or expansion of relevant knowledge.
            Level 2 | 20-40  | The answer provides a direct answer to the question, but contains only a small amount of relevant knowledge expansion, the content is relatively thin.
            Level 3 | 40-60  | In addition to the direct answers, the answer also provides some relevant background knowledge or supplementary information.
            Level 4 | 60-80  | The answer is rich in content, not only answering the question, but also providing more relevant background knowledge, supplementary information or expanded content, so that readers can understand the question more comprehensively.
            Level 5 | 80-100 | In addition to the direct answers, the answer also provides a lot of relevant knowledge, expanded content and in-depth analysis, so that readers can get a comprehensive and in-depth understanding.

            - **Empowerment** -
            Measure the credibility of the answer and whether it convinces the reader that it is correct. High confidence answers often cite authoritative sources or provide sufficient evidence.
            Level   | score range | description
            Level 1 | 0-20   | The answer lacks credibility, contains obvious errors or false information, and fails to convince the reader.
            Level 2 | 20-40  | The answer has some credibility, but some of the information is not accurate or lacks support, which may cause readers to doubt.
            Level 3 | 40-60  | The answer is credible and provides some supporting information, but there are still some areas that are not clear or authoritative.
            Level 4 | 60-80  | The answer is highly credible, providing sufficient supporting information (such as quotes, data, etc.), so that readers can be more convinced.
            Level 5 | 80-100 | The answer is highly credible, providing sufficient and authoritative supporting information, so that the reader is completely convinced of their correctness.

            - **Logical** -
            Measure whether the answer are coherent, clear, and easy to understand.
            Level   | score range | description
            Level 1 | 0-20   | The answer is illogical, incoherent, and difficult to understand.
            Level 2 | 20-40  | The answer has some logic, but it is incoherent and difficult to understand in parts.
            Level 3 | 40-60  | The answer is logically clear and the sentences are basically coherent, but there are still a few logical loopholes or unclear places.
            Level 4 | 60-80  | The answer is logical, coherent, coherent, and easy to understand.
            Level 5 | 80-100 | The answer is extremely logical, fluent and well-organized, making it easy for the reader to follow the author's thoughts.

            - **Readability** -
            Measure whether the answer is well organized, clear in format, and easy to read.
            Level   | score range | description
            Level 1 | 0-20   | The format of the answer is confused, the writing is poorly organized and difficult to read.
            Level 2 | 20-40  | There are some problems in the format of the answer, the organizational structure of the text is not clear enough, and it is difficult to read.
            Level 3 | 40-60  | The format of the answer is basically clear, the writing structure is good, but there is still room for improvement.
            Level 4 | 60-80  | The format of the answer is clear, the writing is well organized and the reading is smooth.
            Level 5 | 80-100 | The format of the answer is very clear, the writing structure is great, the reading experience is excellent, the format is standardized and easy to understand.

           For each indicator, please give the problem a corresponding Level based on the description of the indicator, and then give a score according to the score range of the level.

       
            
            Here are the relevant documents:
                {reference}

            Here are the questions:
                {query}

            Here are the answers:
                {answer}


            Evaluate all the answers using the six criteria listed above, for each criterion, provide a summary description, give a Level based on the description of the indicator, and then give a score based on the score range of the level.

            Output your evaluation in the following JSON format:

            {{
                "Comprehensiveness": {{
                    "Explanation": "Provide explanation here"
                    "Level": "A level range 1 to 5"  # This should be a single number, not a range
                    "Score": "A value range 0 to 100"  # This should be a single number, not a range
                }},
                "Diversity": {{
                    "Explanation": "Provide explanation here"
                    "Level": "A level range 1 to 5"  # This should be a single number, not a range
                    "Score": "A value range 0 to 100"  # This should be a single number, not a range
                }},
                "Empowerment": {{
                    "Explanation": "Provide explanation here"
                    "Level": "A level range 1 to 5"  # This should be a single number, not a range
                    "Score": "A value range 0 to 100"  # This should be a single number, not a range
                }}
                 "Logical": {{
                    "Explanation": "Provide explanation here"
                    "Level": "A level range 1 to 5"  # This should be a single number, not a range
                    "Score": "A value range 0 to 100"  # This should be a single number, not a range
                }}
                "Readability": {{
                    "Explanation": "Provide explanation here"
                    "Level": "A level range 1 to 5"  # This should be a single number, not a range
                    "Score": "A value range 0 to 100"  # This should be a single number, not a range
                }}
                
            }}

        """
        response = llm_model_func(prompt, sys_prompt)
        responses.append(response)
    print(f"{len(responses)} responses evaluated.\n")

    return responses


def fetch_scoring_results(responses):
    metric_name_list = [
        "Comprehensiveness",
        "Diversity",
        "Empowerment",
        "Logical",
        "Readability",
        "Averaged Score",
    ]
    total_scores = [0] * 5
    for i, response in enumerate(responses):
        scores = re.findall(r'"Score":\s*(?:"?(\d+)"?)', response)
        for i in range(5):
            total_scores[i] += float(scores[i])

    total_scores = np.array(total_scores)
    total_scores = total_scores / len(responses)
    total_scores = np.append(total_scores, np.mean(total_scores))
    for metric_name, score in zip(metric_name_list, total_scores):
        print(f"{metric_name:20}: {score:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="按 LLM 五维指标对 Step_3 答案打分")
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"caches/<name>/questions 与 response（默认 {DEFAULT_DATA_NAME!r}，与 reproduce 一致）",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="naive",
        help="与 Step_3 输出文件名前缀一致，如 naive / hyper / hyper-lite",
    )
    parser.add_argument(
        "--question-stage",
        type=int,
        default=2,
        choices=(1, 2, 3),
        help="问题阶段，对应 <n>_stage.json",
    )
    args = parser.parse_args()
    data_name = args.data_name
    mode, question_stage = args.mode, args.question_stage
    WORKING_DIR = Path("caches") / data_name
    RESPONSE_DIR = WORKING_DIR / "response"
    question_file_path = WORKING_DIR / "questions" / f"{question_stage}_stage.json"
    answer_file_path = RESPONSE_DIR / f"{mode}_{question_stage}_stage_result.json"

    # extract questions, answers and references
    raw_queries, raw_refs = extract_queries_and_refs(question_file_path)
    queries, answers = extract_queries_and_answers(answer_file_path)
    assert len(queries) == len(raw_queries)
    assert len(queries) == len(raw_refs)
    assert len(queries) == len(answers)

    # evaluate the answers
    responses = exam_by_scoring(raw_queries, answers, raw_refs)

    # save the results to a JSON file
    OUT_DIR = WORKING_DIR / "evalation"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file_path = OUT_DIR / f"scoring_{question_stage}_stage_question.json"
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(responses, f, indent=4)
    print(f"Scoring-based evaluation results written to {output_file_path}\n\n")

    # calculate the scores
    print(
        f"Scoring-based evaluation for {question_stage}-stage questions of {mode} model:"
    )
    fetch_scoring_results(responses)
