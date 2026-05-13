import argparse
import re
import sys
import json
import numpy as np
from tqdm import tqdm
from pathlib import Path
from openai import OpenAI

sys.path.append(str(Path(__file__).resolve().parent.parent))

from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

from pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME


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


question_prompt = {
    # one-stage question
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
    # two-stage question
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
    # three-stage question
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
    parser = argparse.ArgumentParser(description="从 context 抽样调用 LLM 生成评测问题")
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"读取 caches/<name>/contexts（默认 {DEFAULT_DATA_NAME!r}）",
    )
    args = parser.parse_args()
    data_name = args.data_name
    question_stage = 2
    WORKING_DIR = Path("caches") / data_name
    # number of question stages to extract, which can be 1, 2, or 3
    len_big_chunks = 3
    question_list, reference_list = [], []
    with open(
        f"caches/{data_name}/contexts/{data_name}_unique_contexts.json",
        mode="r",
        encoding="utf-8",
    ) as f:
        unique_contexts = json.load(f)

    cnt, max_cnt = 0, 5
    max_idx = max(len(unique_contexts) - len_big_chunks - 1, 1)

    with tqdm(
        total=max_cnt, desc=f"Extracting {question_stage}-stage questions"
    ) as pbar:
        while cnt < max_cnt:
            # randomly select a context
            idx = np.random.randint(0, max_idx)
            big_chunks = unique_contexts[idx : idx + len_big_chunks]
            context = "".join(big_chunks)

            prompt = question_prompt[question_stage].format(context=context)
            response = llm_model_func(prompt)

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
                m = re.search(r'"Question"\s*:\s*"(.*?)"\s*}', response, re.DOTALL)
                if m:
                    question_text = m.group(1).strip()
            if not question_text:
                print("No question found in the response.")
                continue

            question_list.append(question_text)
            reference_list.append(context)

            cnt += 1
            pbar.update(1)

    # save the questions and references to a JSON file
    prefix = f"caches/{data_name}/questions/{question_stage}_stage"
    question_file_path = Path(f"{prefix}.json")
    ref_file_path = Path(f"{prefix}_ref.json")
    question_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(f"{prefix}.json", "w", encoding="utf-8") as f:
        json.dump(question_list, f, ensure_ascii=False, indent=4)
    with open(f"{prefix}_ref.json", "w", encoding="utf-8") as f:
        json.dump(reference_list, f, ensure_ascii=False, indent=4)

    print(f"questions written to {question_file_path}")
