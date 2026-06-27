import argparse
import json
from pathlib import Path

try:
    from .pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME
except ImportError:
    from pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME


def extract_unique_contexts(input_directory, output_directory):
    """从原始 jsonl 数据集中抽出不重复的 context 文本。

    输入目录默认是 datasets/<data_name>/，里面通常放一个或多个 jsonl 文件。
    每一行是一个 JSON 对象，本脚本只关心其中的 "context" 字段。
    输出目录默认是 caches/<data_name>/contexts/，供 Step_1 建库使用。
    """
    in_dir, out_dir = Path(input_directory), Path(output_directory)

    # 确保输出目录存在；如果目录已经存在，不会报错。
    out_dir.mkdir(parents=True, exist_ok=True)

    # 一个数据集目录下可能有多个 jsonl 文件，这里逐个处理。
    jsonl_files = list(in_dir.glob("*.jsonl"))
    print(f"Found {len(jsonl_files)} JSONL files.")

    for file_path in jsonl_files:
        # 输出文件名和输入文件 stem 保持一致：
        # datasets/neurology/neurology.jsonl
        # -> caches/neurology/contexts/neurology_unique_contexts.json
        output_path = out_dir / f"{file_path.stem}_unique_contexts.json"
        if output_path.exists():
            # 已经生成过的文件直接跳过，避免重复预处理覆盖旧结果。
            continue

        # 用 dict 当有序集合：key 是 context，value 无意义。
        # 这样既能去重，又能保留首次出现的大致顺序。
        unique_contexts_dict = {}

        print(f"Processing file: {file_path.name}")

        try:
            with open(file_path, "r", encoding="utf-8") as infile:
                for line_number, line in enumerate(infile, start=1):
                    # 清理内容2边无关字符
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        # 原始数据每行一个 JSON；这里只取 context 作为建库语料。
                        json_obj = json.loads(line)
                        context = json_obj.get("context")
                        # 去重
                        if context and context not in unique_contexts_dict:
                            unique_contexts_dict[context] = None
                    except json.JSONDecodeError as e:
                        print(
                            f"JSON decoding error in file {file_path.name} at line {line_number}: {e}"
                        )
        except FileNotFoundError:
            print(f"File not found: {file_path.name}")
            continue
        except Exception as e:
            print(f"An error occurred while processing file {file_path.name}: {e}")
            continue

        # Step_1 会把这个 list 整体读入，再交给 HyperRAG.insert 建索引。
        unique_contexts_list = list(unique_contexts_dict.keys())
        print(
            f"There are {len(unique_contexts_list)} unique `context` entries in the file {file_path.name}."
        )

        try:
            # ensure_ascii=False 保留中文等非 ASCII 内容，便于后续阅读和 LLM 处理。
            with open(output_path, "w", encoding="utf-8") as outfile:
                json.dump(unique_contexts_list, outfile, ensure_ascii=False, indent=4)
            print(f"Unique `context` entries have been saved to: {output_path.name}")
        except Exception as e:
            print(f"An error occurred while saving to the file {output_path.name}: {e}")

    print("All files have been processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="从 datasets 中的 jsonl 去重抽取 context，写入 caches/<data_name>/contexts/"
    )
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"数据集目录名（默认 {DEFAULT_DATA_NAME!r}），用于默认输入/输出路径",
    )
    parser.add_argument(
        "-i",
        "--input_dir",
        type=str,
        default=None,
        help="输入目录（默认 datasets/<data-name>）",
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        type=str,
        default=None,
        help="输出目录（默认 caches/<data-name>/contexts）",
    )

    args = parser.parse_args()
    data_name = args.data_name

    # 如果没有显式传 -i/-o，就按复现实验的标准目录约定推导路径。
    input_dir = args.input_dir or f"datasets/{data_name}"
    output_dir = args.output_dir or f"caches/{data_name}/contexts"

    extract_unique_contexts(input_dir, output_dir)
