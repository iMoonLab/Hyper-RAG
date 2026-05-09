# -*- coding: utf-8 -*-
"""验证 Neurology 流水线约定下的原始 jsonl（默认 datasets/neurology/neurology.jsonl）。

检查：文件存在、文件名 stem 与 data_name 一致、每行合法 JSON 且含非空字符串 context。
不调用 API；供手动下载数据后本地自检。"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from reproduce.pipeline_defaults import DATA_NAME as DEFAULT_DATA_NAME


def verify_jsonl(path: Path, expected_stem: str) -> int:
    if path.suffix.lower() != ".jsonl":
        print(f"错误：期望 .jsonl 扩展名，得到 {path.suffix!r}")
        return 1
    if path.stem != expected_stem:
        print(
            f"错误：文件名 stem 为 {path.stem!r}，与 data_name={expected_stem!r} 不一致；"
            f"Step_1 会读取 caches/{expected_stem}/contexts/{expected_stem}_unique_contexts.json。"
        )
        return 1
    if not path.is_file():
        print(f"错误：文件不存在：{path}")
        return 1

    total = 0
    bad: list[tuple[int, str]] = []

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            raw = line.strip()
            if not raw:
                continue
            total += 1
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as e:
                bad.append((line_no, f"JSON 解析失败: {e}"))
                continue
            if not isinstance(obj, dict):
                bad.append((line_no, "根类型不是 JSON 对象"))
                continue
            ctx = obj.get("context")
            if not isinstance(ctx, str) or not ctx.strip():
                bad.append(
                    (line_no, "缺少非空字符串字段 context（Step_0 按 context 去重）")
                )

    if total == 0:
        print("错误：无有效数据行（跳过空行后条数为 0）")
        return 1

    print(f"通过：{path}")
    print(f"  data_name / stem: {expected_stem!r}")
    print(f"  有效 JSON 行数: {total}")
    if bad:
        print(f"错误：{len(bad)} 行不符合约定（仅列出前 10 处）")
        for ln, msg in bad[:10]:
            print(f"  第 {ln} 行: {msg}")
        return 1

    print("  抽样：全部行均含非空 context。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-name",
        type=str,
        default=DEFAULT_DATA_NAME,
        help=f"与 jsonl 文件名 stem 一致（默认 {DEFAULT_DATA_NAME!r}）",
    )
    parser.add_argument(
        "--jsonl",
        type=str,
        default=None,
        help="jsonl 路径（默认 datasets/<data-name>/<data-name>.jsonl）",
    )
    args = parser.parse_args()
    name = args.data_name
    path = (
        Path(args.jsonl).resolve()
        if args.jsonl
        else (ROOT / "datasets" / name / f"{name}.jsonl").resolve()
    )
    return verify_jsonl(path, name)


if __name__ == "__main__":
    sys.exit(main())
