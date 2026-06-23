"""HyperRAG 的通用工具函数。

这里放的是跨模块复用的小工具：
- 日志初始化
- embedding 函数包装
- JSON 读写
- tiktoken 编解码
- LLM 并发限制
- CSV 上下文拼装/去重
"""

import asyncio
import html
import io
import csv
import json
import logging
import os
import re
from dataclasses import dataclass
from functools import wraps
from hashlib import md5
from typing import Any, Union, List
import xml.etree.ElementTree as ET

import numpy as np
import tiktoken

ENCODER = None

logger = logging.getLogger("hyper_rag")


def set_logger(log_file: str):
    """把 hyper_rag logger 输出到 working_dir/HyperRAG.log。"""
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)


@dataclass
class EmbeddingFunc:
    """给 embedding 函数附加维度和最大 token 信息的轻量包装。

    NanoVectorDB 初始化时需要 embedding_dim；
    建库/查询时仍然通过 func 真正调用 embedding 模型。
    """
    embedding_dim: int
    max_token_size: int
    func: callable

    async def __call__(self, *args, **kwargs) -> np.ndarray:
        return await self.func(*args, **kwargs)


def locate_json_string_body_from_string(content: str) -> Union[str, None]:
    """从 LLM 输出中截取最外层 JSON 字符串。"""
    maybe_json_str = re.search(r"{.*}", content, re.DOTALL)
    if maybe_json_str is not None:
        return maybe_json_str.group(0)
    else:
        return None


def convert_response_to_json(response: str) -> dict:
    """把 LLM 输出解析成 JSON dict；解析失败会抛错。"""
    json_str = locate_json_string_body_from_string(response)
    assert json_str is not None, f"Unable to parse JSON from response: {response}"
    try:
        data = json.loads(json_str)
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {json_str}")
        raise e from None


def compute_args_hash(*args):
    """根据调用参数生成 hash，用作 LLM cache 的 key。"""
    return md5(str(args).encode()).hexdigest()


def compute_mdhash_id(content, prefix: str = ""):
    """根据文本内容生成稳定 ID；同样内容会得到同样 ID。"""
    return prefix + md5(content.encode()).hexdigest()


def limit_async_func_call(max_size: int, waitting_time: float = 0.0001):
    """限制异步函数的最大并发数，主要用于 LLM 和 embedding API。"""

    def final_decro(func):
        """Not using async.Semaphore to aovid use nest-asyncio"""
        __current_size = 0

        @wraps(func)
        async def wait_func(*args, **kwargs):
            nonlocal __current_size
            while __current_size >= max_size:
                await asyncio.sleep(waitting_time)
            __current_size += 1
            result = await func(*args, **kwargs)
            __current_size -= 1
            return result

        return wait_func

    return final_decro

def limit_async_gen_call(max_size: int):
    """
    限制“异步生成器（async generator）”并发数的装饰器。
    适用于 stream 场景：func(*args, **kwargs) 返回一个 async generator，
    不能对其 await，只能 async for 迭代。
    """
    sem = asyncio.Semaphore(max_size)

    def final_decro(func):
        @wraps(func)
        async def gen_wrapper(*args, **kwargs):
            await sem.acquire()
            try:
                agen = func(*args, **kwargs)  # 注意：这里不要 await
                async for item in agen:
                    yield item
            finally:
                sem.release()

        return gen_wrapper

    return final_decro


def wrap_embedding_func_with_attrs(**kwargs):
    """把普通 embedding 函数包装成 EmbeddingFunc。"""

    def final_decro(func) -> EmbeddingFunc:
        new_func = EmbeddingFunc(**kwargs, func=func)
        return new_func

    return final_decro


def load_json(file_name):
    """读取 JSON 文件；不存在时返回 None。"""
    if not os.path.exists(file_name):
        return None
    with open(file_name, encoding="utf-8") as f:
        return json.load(f)


def write_json(json_obj, file_name):
    """以 UTF-8 写 JSON，保留中文字符。"""
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, indent=2, ensure_ascii=False)


def encode_string_by_tiktoken(content: str, model_name: str = "gpt-4o"):
    """把文本编码成 token id 列表，用于切块和 token 长度控制。"""
    global ENCODER
    if ENCODER is None:
        ENCODER = tiktoken.encoding_for_model(model_name)
    tokens = ENCODER.encode(content)
    return tokens


def decode_tokens_by_tiktoken(tokens: list[int], model_name: str = "gpt-4o"):
    """把 token id 列表还原成文本。"""
    global ENCODER
    if ENCODER is None:
        ENCODER = tiktoken.encoding_for_model(model_name)
    content = ENCODER.decode(tokens)
    return content


def pack_user_ass_to_openai_messages(*args: str):
    """把 user/assistant 交替文本包装成 OpenAI messages 历史。"""
    roles = ["user", "assistant"]
    return [
        {"role": roles[i % 2], "content": content} for i, content in enumerate(args) #if content is not None
    ]


def split_string_by_multi_markers(content: str, markers: list[str]) -> list[str]:
    """按多个分隔符切分字符串，并清理空片段。"""
    if not markers:
        return [content]
    results = re.split("|".join(re.escape(marker) for marker in markers), content)
    return [r.strip() for r in results if r.strip()]


# Refer the utils functions of the official GraphRAG implementation:
# https://github.com/microsoft/graphrag
def clean_str(input: Any) -> str:
    """清理 HTML 转义和控制字符，主要用于 LLM 抽取结果标准化。"""
    # 非字符串直接返回，避免破坏上游传入的结构。
    if not isinstance(input, str):
        return input

    result = html.unescape(input.strip())
    # https://stackoverflow.com/questions/4324790/removing-control-characters-from-a-string-in-python
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", result)


def is_float_regex(value):
    """判断字符串是否可解析为浮点数。"""
    return bool(re.match(r"^[-+]?[0-9]*\.?[0-9]+$", value))


def truncate_list_by_token_size(list_data: list, key: callable, max_token_size: int):
    """按 token 总量截断列表，避免拼给 LLM 的上下文过长。"""
    if max_token_size <= 0:
        return []
    tokens = 0
    for i, data in enumerate(list_data):
        tokens += len(encode_string_by_tiktoken(key(data)))
        if tokens > max_token_size:
            return list_data[:i]
    return list_data


def list_of_list_to_csv(data: List[List[str]]) -> str:
    """把二维列表转成 CSV 字符串；operate.py 用它拼检索上下文。"""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(data)
    return output.getvalue()


def csv_string_to_list(csv_string: str) -> List[List[str]]:
    """把 CSV 字符串还原成二维列表。"""
    output = io.StringIO(csv_string)
    reader = csv.reader(output)
    return [row for row in reader]


def save_data_to_file(data, file_name):
    """保存调试/中间数据到 JSON 文件。"""
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def xml_to_json(xml_file):
    """把 GraphML/XML 图数据转换成 nodes/edges JSON。

    这是兼容/迁移工具函数，不是 HyperRAG 主流程必经路径。
    """
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Print the root element's tag and attributes to confirm the file has been correctly loaded
        print(f"Root element: {root.tag}")
        print(f"Root attributes: {root.attrib}")

        data = {"nodes": [], "edges": []}

        # Use namespace
        namespace = {"": "http://graphml.graphdrawing.org/xmlns"}

        for node in root.findall(".//node", namespace):
            node_data = {
                "id": node.get("id").strip('"'),
                "entity_type": node.find("./data[@key='d0']", namespace).text.strip('"')
                if node.find("./data[@key='d0']", namespace) is not None
                else "",
                "description": node.find("./data[@key='d1']", namespace).text
                if node.find("./data[@key='d1']", namespace) is not None
                else "",
                "source_id": node.find("./data[@key='d2']", namespace).text
                if node.find("./data[@key='d2']", namespace) is not None
                else "",
            }
            data["nodes"].append(node_data)

        for edge in root.findall(".//edge", namespace):
            edge_data = {
                "source": edge.get("source").strip('"'),
                "target": edge.get("target").strip('"'),
                "weight": float(edge.find("./data[@key='d3']", namespace).text)
                if edge.find("./data[@key='d3']", namespace) is not None
                else 0.0,
                "description": edge.find("./data[@key='d4']", namespace).text
                if edge.find("./data[@key='d4']", namespace) is not None
                else "",
                "keywords": edge.find("./data[@key='d5']", namespace).text
                if edge.find("./data[@key='d5']", namespace) is not None
                else "",
                "source_id": edge.find("./data[@key='d6']", namespace).text
                if edge.find("./data[@key='d6']", namespace) is not None
                else "",
            }
            data["edges"].append(edge_data)

        # Print the number of nodes and edges found
        print(f"Found {len(data['nodes'])} nodes and {len(data['edges'])} edges")

        return data
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def process_combine_contexts(hl, ll):
    """合并 high-level 和 low-level 检索上下文中的 CSV section。

    hyper_query 会分别构造实体线和关系线的上下文，最后用这个函数去重合并。
    """
    header = None
    list_hl = csv_string_to_list(hl.strip())
    list_ll = csv_string_to_list(ll.strip())

    if list_hl:
        header = list_hl[0]
        list_hl = list_hl[1:]
    if list_ll:
        header = list_ll[0]
        list_ll = list_ll[1:]
    if header is None:
        return ""

    if list_hl:
        list_hl = [",".join(item[1:]) for item in list_hl if item]
    if list_ll:
        list_ll = [",".join(item[1:]) for item in list_ll if item]

    combined_sources_set = set(filter(None, list_hl + list_ll))

    combined_sources = [",\t".join(header)]

    for i, item in enumerate(combined_sources_set, start=1):
        combined_sources.append(f"{i},\t{item}")

    combined_sources = "\n".join(combined_sources)

    return combined_sources


def always_get_an_event_loop() -> asyncio.AbstractEventLoop:
    """
    Ensure that there is always an event loop available.

    This function tries to get the current event loop. If the current event loop is closed or does not exist,
    it creates a new event loop and sets it as the current event loop.

    Returns:
        asyncio.AbstractEventLoop: The current or newly created event loop.
    """
    try:
        # Try to get the current event loop
        current_loop = asyncio.get_event_loop()
        if current_loop.is_closed():
            raise RuntimeError("Event loop is closed.")
        return current_loop

    except RuntimeError:
        # If no event loop exists or it is closed, create a new one
        logger.info("Creating a new event loop in main thread.")
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        return new_loop

def deduplicate_by_key(data_list, key_string):
    """按指定字段对结构化检索结果去重。

    用于合并实体线和关系线结果，例如 entity_name / entity_set / content。
    """
    unique_data = []
    seen_keys = set()

    def make_hashable(value):
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, list):
            try:
                return tuple(sorted(make_hashable(v) for v in value))
            except TypeError:
                return json.dumps(value, ensure_ascii=False, sort_keys=True)
        if isinstance(value, dict):
            return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
        return str(value)

    for item in data_list:
        raw_key = item.get(key_string)
        if raw_key is None:
            continue
        key = make_hashable(raw_key)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_data.append(item)
    return unique_data  
