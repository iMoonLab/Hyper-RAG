# -*- coding: utf-8 -*-
"""
复现流水线共享默认：与 `datasets/<DATA_NAME>/<DATA_NAME>.jsonl` 的 stem 一致，
以便 Step_0 写出 `caches/<DATA_NAME>/contexts/<DATA_NAME>_unique_contexts.json`，
与 Step_1 读取路径一致。切换数据集时改此处或各脚本 `--data-name`。
"""

DATA_NAME = "neurology"
