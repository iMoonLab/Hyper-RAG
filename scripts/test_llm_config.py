"""从 my_config 读取 LLM 配置，发一条 chat 请求做连通性测试。

用法（在项目根目录执行）:
  python scripts/test_llm_config.py
  python scripts/test_llm_config.py 用一句话介绍你自己
"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from hyperrag.env import normalize_proxy_env
from openai import AsyncOpenAI

normalize_proxy_env()


async def main() -> None:
    prompt = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "请用一句话确认你能正常回复。"
    client = AsyncOpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
    try:
        r = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        text = (r.choices[0].message.content or "").strip()
        print("OK — LLM 调用成功")
        print("base_url:", LLM_BASE_URL)
        print("model:", LLM_MODEL)
        print("--- 回复 ---")
        print(text)
    except Exception as e:
        print("FAIL — 调用失败:", type(e).__name__, file=sys.stderr)
        print(e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
