from __future__ import annotations

import os
import sys

# 在后续可能加载 NumPy / 向量库之前为 Windows 会话设置 OpenMP 重复初始化容忍（可选权宜）。
if sys.platform == "win32":
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import time
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple

import asyncio
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# =============================================================================
# 日志
# =============================================================================
logger = logging.getLogger("hyperrag_api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

# =============================================================================
# 配置（环境变量）
# =============================================================================
DATA_NAME = os.getenv("HYPERRAG_DATA_NAME", "pathology").strip()
MODE = os.getenv("HYPERRAG_MODE", "hyper").strip()  # hyper | hyper-lite | naive | llm
MAX_QPS = float(os.getenv("HYPERRAG_MAX_QPS", "3").strip() or "3")
API_KEY = os.getenv("HYPERRAG_API_KEY", "").strip()
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("HYPERRAG_ALLOWED_ORIGINS", "*").split(",")]

# =============================================================================
# 目录与 import 路径
# =============================================================================
THIS_FILE = Path(__file__).resolve()
ROOT = THIS_FILE.parent
WORKING_DIR = ROOT / "caches" / DATA_NAME

sys.path.append(str(ROOT))

# =============================================================================
# 项目内 import
# =============================================================================
from hyperrag import HyperRAG, QueryParam  # noqa: E402
from hyperrag.utils import EmbeddingFunc  # noqa: E402
from hyperrag.llm import openai_complete_stream_if_cache  # noqa: E402

from reproduce.Step_3_response_question import llm_model_func, embedding_func  # noqa: E402
from my_config import EMB_DIM, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL  # noqa: E402

# =============================================================================
# FastAPI
# =============================================================================
app = FastAPI(title="HyperRAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag: Optional[HyperRAG] = None
query_param: Optional[QueryParam] = None

# =============================================================================
# 请求/响应结构
# =============================================================================
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=6000)
    mode: Optional[str] = Field(default=None, description="覆盖默认模式：hyper / hyper-lite / naive / llm")


class QueryResponse(BaseModel):
    answer: str
    mode: str
    latency_ms: int


# =============================================================================
# 简易限流（单进程有效）
# =============================================================================
_rate_state: Dict[str, Tuple[float, int]] = {}
_RATE_WINDOW_SEC = 1.0


def _rate_limit(ip: str) -> None:
    if MAX_QPS <= 0:
        return
    now = time.time()
    window_start, count = _rate_state.get(ip, (now, 0))
    if now - window_start >= _RATE_WINDOW_SEC:
        _rate_state[ip] = (now, 1)
        return
    if count >= int(MAX_QPS):
        raise HTTPException(status_code=429, detail="请求过于频繁（触发限流），请稍后重试。")
    _rate_state[ip] = (window_start, count + 1)


def _require_api_key(x_api_key: Optional[str]) -> None:
    if not API_KEY:
        return
    if (not x_api_key) or (x_api_key != API_KEY):
        raise HTTPException(status_code=401, detail="未授权：缺少或错误的 X-API-Key")


# =============================================================================
# 启动：初始化 HyperRAG（关键：注入 llm_model_stream_func）
# =============================================================================
@app.on_event("startup")
async def _startup() -> None:
    global rag, query_param
    WORKING_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("启动 HyperRAG 服务")
    logger.info("ROOT=%s", ROOT)
    logger.info("WORKING_DIR=%s", WORKING_DIR)
    logger.info("MODE=%s", MODE)

    async def llm_model_stream_func(prompt, system_prompt=None, history_messages=[], **kwargs):
        # 这里用 hyperrag.llm 里的 openai_complete_stream_if_cache 做真 token streaming
        async for tok in openai_complete_stream_if_cache(
            model=LLM_MODEL,
            prompt=prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL,
            **kwargs,
        ):
            yield tok

    rag = HyperRAG(
        working_dir=WORKING_DIR,
        llm_model_func=llm_model_func,                 # 非流式
        llm_model_stream_func=llm_model_stream_func,   # 流式（关键）
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM,
            max_token_size=8192,
            func=embedding_func,
        ),
    )

    query_param = QueryParam(mode=MODE)
    logger.info("HyperRAG 启动成功")


@app.on_event("shutdown")
async def _shutdown() -> None:
    logger.info("关闭 HyperRAG 服务")


# =============================================================================
# 接口
# =============================================================================
@app.get("/healthz")
async def healthz() -> dict:
    return {
        "status": "ok",
        "data_name": DATA_NAME,
        "mode": MODE,
        "working_dir": str(WORKING_DIR),
        "api_key_required": bool(API_KEY),
    }


@app.post("/query", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> QueryResponse:
    _require_api_key(x_api_key)
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)

    if rag is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪，请稍后重试。")

    mode = (req.mode or MODE).strip()
    if mode not in {"hyper", "hyper-lite", "naive", "llm"}:
        raise HTTPException(status_code=400, detail="mode 参数非法：hyper / hyper-lite / naive / llm")

    qp = QueryParam(mode=mode)

    t0 = time.time()
    try:
        answer = await rag.aquery(req.question, param=qp)
    except Exception as e:
        logger.exception("query 调用失败：%s", e)
        raise HTTPException(status_code=500, detail=str(e))
    latency_ms = int((time.time() - t0) * 1000)
    return QueryResponse(answer=answer, mode=mode, latency_ms=latency_ms)


@app.post("/query_stream")
async def query_stream(
    req: QueryRequest,
    request: Request,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """
    真·HyperRAG 流式输出：
    - 调用 rag.astream_query(...)，由 hyperrag 内部检索/构图/约束后，再由 LLM streaming 输出 token
    - 前端直接按文本流读取即可（你已经实现了 fetch reader）
    """
    _require_api_key(x_api_key)
    ip = request.client.host if request.client else "unknown"
    _rate_limit(ip)

    if rag is None:
        raise HTTPException(status_code=503, detail="服务尚未就绪，请稍后重试。")

    mode = (req.mode or MODE).strip()
    if mode not in {"hyper", "hyper-lite", "naive", "llm"}:
        raise HTTPException(status_code=400, detail="mode 参数非法：hyper / hyper-lite / naive / llm")

    qp = QueryParam(mode=mode)

    async def gen():
        try:
            async for tok in rag.astream_query(req.question, param=qp):
                if tok:
                    yield tok
                await asyncio.sleep(0)
        except Exception as e:
            logger.exception("query_stream 调用失败：%s", e)
            yield f"\n[ERROR] {str(e)}\n"

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")
