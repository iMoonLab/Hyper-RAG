import os
import sys

# Windows：多个依赖（如 NumPy MKL 与其它库）可能各自链接 Intel OpenMP，
# 易触发 “libiomp5md.dll already initialized”。在加载本包子模块前设置，便于本会话内继续运行。
if sys.platform == "win32":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from .hyperrag import HyperRAG, QueryParam


__version__ = "0.0.1"

__all__ = {
    HyperRAG,
    QueryParam,
}
