import os
import sys

# ------------------------------------------------------------------
# 1. 代理设置 (如果你之前的脚本里要加，这里也要加)
# ------------------------------------------------------------------
# 请根据你的实际情况取消注释并修改端口
# os.environ["http_proxy"] = "http://127.0.0.1:1080"
# os.environ["https_proxy"] = "http://127.0.0.1:1080"

# ------------------------------------------------------------------
# 2. 导入配置
# ------------------------------------------------------------------
try:
    from my_config import (
        LLM_API_KEY, LLM_BASE_URL, LLM_MODEL,
        EMB_API_KEY, EMB_BASE_URL, EMB_MODEL, EMB_DIM,
    )
    print("✅ 成功读取 my_config.py 配置")
except ImportError:
    print("❌ 错误: 找不到 my_config.py，请先复制 config_temp.py 并重命名！")
    sys.exit(1)

# ------------------------------------------------------------------
# 3. 开始测试
# ------------------------------------------------------------------
from openai import OpenAI

def test_llm():
    print(f"\n[1/2] 正在测试 LLM 接口 ({LLM_MODEL})...")
    print(f"      Base URL: {LLM_BASE_URL}")
    
    client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
    
    try:
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": "你好，请回复'连接成功'这四个字。"}],
            timeout=10, # 设置10秒超时，避免死等
            extra_body={"enable_thinking": False}
        )
        content = response.choices[0].message.content
        print(f"✅ LLM 测试通过！模型回复: {content}")
        return True
    except Exception as e:
        print(f"❌ LLM 测试失败: {e}")
        return False

def test_embedding():
    print(f"\n[2/2] 正在测试 Embedding 接口 ({EMB_MODEL})...")
    # 注意：有时候 Embedding 的 Key/BaseURL 和 LLM 不一样，取决于你的配置
    client = OpenAI(api_key=EMB_API_KEY, base_url=EMB_BASE_URL)
    
    try:
        response = client.embeddings.create(
            input="测试文本",
            model=EMB_MODEL,
            dimensions=EMB_DIM,
            timeout=10
        )
        # 只要能拿回数据且向量长度大于0就算成功
        vec_len = len(response.data[0].embedding)
        print(f"✅ Embedding 测试通过！向量维度: {vec_len}")
        return True
    except Exception as e:
        print(f"❌ Embedding 测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 开始连接性测试...")
    
    llm_ok = test_llm()
    emb_ok = test_embedding()
    
    print("\n------------------------------------------------")
    if llm_ok and emb_ok:
        print("🎉 恭喜！所有接口连接正常，可以放心地跑 build_db.py 了！")
    else:
        print("⚠️ 警告：存在连接问题，请检查 my_config.py 或 代理设置。")
        print("   (常见原因：代理端口不对、Key 余额不足、模型名称填错)")