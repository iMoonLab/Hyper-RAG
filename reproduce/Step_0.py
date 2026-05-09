import json
import argparse
from pathlib import Path

from pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME


def extract_unique_contexts(input_directory, output_directory):
    in_dir, out_dir = Path(input_directory), Path(output_directory)
    out_dir.mkdir(parents=True, exist_ok=True)

    jsonl_files = list(in_dir.glob("*.jsonl"))
    print(f"Found {len(jsonl_files)} JSONL files.")

    for file_path in jsonl_files:
        output_path = out_dir / f"{file_path.stem}_unique_contexts.json"
        if output_path.exists():
            continue

        unique_contexts_dict = {}

        print(f"Processing file: {file_path.name}")

        try:
            with open(file_path, "r", encoding="utf-8") as infile:
                for line_number, line in enumerate(infile, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        json_obj = json.loads(line)
                        context = json_obj.get("context")
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

        unique_contexts_list = list(unique_contexts_dict.keys())
        print(
            f"There are {len(unique_contexts_list)} unique `context` entries in the file {file_path.name}."
        )

        try:
            with open(output_path, "w", encoding="utf-8") as outfile:
                json.dump(unique_contexts_list, outfile, ensure_ascii=False, indent=4)
            print(f"Unique `context` entries have been saved to: {output_path.name}")
        except Exception as e:
            print(f"An error occurred while saving to the file {output_path.name}: {e}")

    print("All files have been processed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="从 datasets 下 jsonl 去重 context，写入 caches/<data_name>/contexts/"
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
    input_dir = args.input_dir or f"datasets/{data_name}"
    output_dir = args.output_dir or f"caches/{data_name}/contexts"

    extract_unique_contexts(input_dir, output_dir)
