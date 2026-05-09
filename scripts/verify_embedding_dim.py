"""一次调用嵌入 API，核对向量维度与 my_config.EMB_DIM 是否一致。"""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from my_config import EMB_API_KEY, EMB_BASE_URL, EMB_DIM, EMB_MODEL
from hyperrag.llm import openai_embedding


async def main() -> None:
    arr = await openai_embedding(
        ["dimension check"],
        model=EMB_MODEL,
        base_url=EMB_BASE_URL,
        api_key=EMB_API_KEY,
    )
    actual = int(arr.shape[-1])
    ok = actual == EMB_DIM
    print(f"actual_dim={actual} EMB_DIM={EMB_DIM} match={ok}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
