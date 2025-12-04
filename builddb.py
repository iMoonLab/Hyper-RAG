import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

from hyperrag import HyperRAG
from hyperrag.utils import EmbeddingFunc
from hyperrag.llm import openai_embedding, openai_complete_if_cache
from my_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from my_config import EMB_API_KEY, EMB_BASE_URL, EMB_MODEL, EMB_DIM

async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
    call_params = {}
    if "qwen" in LLM_MODEL.lower():
        call_params["extra_body"] = {"enable_thinking": False}
    return await openai_complete_if_cache(
        LLM_MODEL, prompt, system_prompt=system_prompt, 
        history_messages=history_messages, api_key=LLM_API_KEY,
        base_url=LLM_BASE_URL, **call_params, **kwargs
    )

async def embedding_func(texts: list[str]):
    return await openai_embedding(
        texts, model=EMB_MODEL, api_key=EMB_API_KEY, base_url=EMB_BASE_URL,dimensions=EMB_DIM
    )

if __name__ == "__main__":
    target_dir = "web-ui/backend/hyperrag_cache/testzh"
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    
    rag = HyperRAG(
        working_dir=target_dir,
        llm_model_func=llm_model_func,
        embedding_func=EmbeddingFunc(
            embedding_dim=EMB_DIM, max_token_size=8192, func=embedding_func
        ),
        embedding_batch_num=8,
    )

    raw_data_dir = Path("./raw_markdowns")
    files = list(raw_data_dir.glob("*.md")) + list(raw_data_dir.glob("*.txt"))
    print(f"使用模型: {LLM_MODEL}")
    print(f"Embedding 模型: {EMB_MODEL} (维度: {EMB_DIM})")
    
    print(f"开始处理 {len(files)} 个文件...")
    
    for f in files:
        print(f"正在读取并插入: {f.name}")
        with open(f, "r", encoding="utf-8") as file:
            content = file.read()
            if not content.strip():
                continue
                
            rag.insert(content)
            
    print(f"处理完成！数据已保存至: {target_dir}")