import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import re
import json
import numpy as np
from tqdm import tqdm
from openai import OpenAI
from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from hyperrag.env import normalize_proxy_env

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


# Deal with one by one
def exam_by_selection(queries, A_answers, B_answers):

    responses = []
    sys_prompt = """
        ---Role---
        You will evaluate two answers to the same question based on eight criteria: *Comprehensiveness**, **Empowerment**, **Accuracy**,**Relevance**,**Coherence**,
        **Clarity**,**Logical**,and **Flexibility**.
        """
    for query, answer1, answer2 in tqdm(
        zip(queries, A_answers, B_answers),
        desc="Evaluating answers",
        total=len(queries),
    ):
        prompt = f"""
            You will evaluate two answers to the same question by using the relevant documents based on eight criteria:*Comprehensiveness**, **Empowerment**, **Accuracy**,**Relevance**,**Coherence**,
        **Clarity**,**Logical**,and **Flexibility**.
        
        - **Comprehensiveness**: How much detail does the answer provide to cover all aspects and details of the question?
        - **Empowerment**: How well does the answer help the reader understand and make informed judgments about the topic?
        - **Accuracy**: How well does the answer align with factual truth and avoid hallucination based on the retrieved context?
        - **Relevance**: How precisely does the answer address the core aspects of the question without including unnecessary information?
        - **Coherence**: How well does the system integrate and synthesize information from multiple sources into a logically flowing response?
        - **Clarity**: How well does the system provide complete information while avoiding unnecessary verbosity and redundancy?
        - **Logical**: How well does the system maintain consistent logical arguments without contradicting itself across the response?
        - **Flexibility**: How well does the system handle various question formats, tones, and levels of complexity?
   
     For each criterion, choose the better answer (either Answer 1 or Answer 2) and explain why. Then, select an overall winner based on these ten categories.

     

        Here are the questions:
        {query}

        Here are the two answers:

        **Answer 1:**
        {answer1}

        **Answer 2:**
        {answer2}

        Evaluate both answers using the eight criteria listed above and provide detailed explanations for each criterion.

        Output your evaluation in the following JSON format:

        {{
            "Comprehensiveness": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},
            "Empowerment": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},
            "Accuracy": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},            
            "Relevance": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},            
            "Coherence": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},                     
            "Clarity": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},                      
            "Logical": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},   
            "Flexibility": {{
                "Winner": "[Answer 1 or Answer 2]",
                "Explanation": "[Provide explanation here]"
            }},                      
        }}   

        """
        response = llm_model_func(prompt, sys_prompt)
        responses.append(response)
    print(f"{len(responses)} responses evaluated.\n")

    return responses


def fetch_selection_results(responses):
    metric_name_list = [
        "Comprehensiveness",
        "Empowerment",
        "Accuracy",
        "Relevance",
        "Coherence",
        "Clarity",
        "Logical",
        "Flexibility",
        "Averaged Score",
    ]
    total_scores = [0] * 8
    for i, response in enumerate(responses):
        # response = response.replace('```json\\n', '').replace('```', '').strip()
        # response = response.strip('"').replace('\\n', '\n').replace('\\"', '"')
        scores = re.findall(r'"Winner":\s*"([^"]+)"', response)
        for i in range(8):
            if scores[i].lower() == "answer 1":
                total_scores[i] += 1

    total_scores = np.array(total_scores)
    total_scores = total_scores / len(responses)
    total_scores = np.append(total_scores, np.mean(total_scores))
    for metric_name, score in zip(metric_name_list, total_scores):
        print(f"{metric_name:20}: {score:.2f} vs. {1 - score:.2f}")


if __name__ == "__main__":
    data_name = "mix"
    question_stage = 2
    # Note: we noticted that the position of the answer (first position or second position)
    # will effect the results. Thus, we suggest to average the results of
    # (A_mode vs. B_mode) and (B_mode vs. A_mode) as the final results.
    A_mode, B_mode = "hyper", "naive"
    WORKING_DIR = Path("caches") / data_name
    RESPONSE_DIR = WORKING_DIR / "response"
    A_answer_file_path = RESPONSE_DIR / f"{A_mode}_{question_stage}_stage_result.json"
    B_answer_file_path = RESPONSE_DIR / f"{B_mode}_{question_stage}_stage_result.json"

    # extract questions, answers and references
    A_queries, A_answers = extract_queries_and_answers(A_answer_file_path)
    B_queries, B_answers = extract_queries_and_answers(B_answer_file_path)
    assert len(A_queries) == len(B_queries)
    assert len(A_answers) == len(B_answers)

    # evaluate the answers
    responses = exam_by_selection(A_queries, A_answers, B_answers)

    # save the results to a JSON file
    OUT_DIR = WORKING_DIR / "evalation"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file_path = (
        OUT_DIR / f"selection_{question_stage}_stage_question_{A_mode}_vs_{B_mode}.json"
    )
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(responses, f, indent=4)
    print(f"Selection-based evaluation results written to {output_file_path}\n\n")

    # calculate the scores
    print(
        f"Selection-based evaluation for {question_stage}-stage questions of {A_mode} vs. {B_mode}:"
    )
    fetch_selection_results(responses)
