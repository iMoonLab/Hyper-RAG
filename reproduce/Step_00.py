import json
import re
from pathlib import Path

def clean_text(text):
    """
    清洗 PDF 转出来的文本：
    1. 把连续的空白字符替换成一个空格
    2. 尝试把断行的句子拼起来 (这一步比较激进，视情况而定)
    """
    # 替换掉所有看不见的特殊字符
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def chunk_text(text, chunk_size=1000, overlap=200):
    """
    按固定长度切分文本，带重叠
    """
    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        # 截取一段
        end = start + chunk_size
        
        chunk = text[start:end]
        
        if len(text) - end < chunk_size * 0.1:
            chunk = text[start:]
            chunks.append(chunk)
            break
            
        chunks.append(chunk)
        
        # 下一块的起点 = 当前终点 - 重叠量
        start += (chunk_size - overlap)
    
    return chunks

def generate_context_json_robust(data_name="ClientDemoData"):
    input_dir = Path("../raw_markdowns")
    output_dir = Path(f"caches/{data_name}/contexts")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{data_name}_unique_contexts.json"
    
    all_chunks = []
    
    files = list(input_dir.glob("*.md")) + list(input_dir.glob("*.txt"))
    print(f"找到 {len(files)} 个文件，开始处理...")
    
    for f in files:
        print(f"正在读取: {f.name}")
        with open(f, 'r', encoding='utf-8') as infile:
            raw_text = infile.read()
            
            # 1. 清洗：把 PDF 的换行变成空格，拼成一行长文本
            clean_content = clean_text(raw_text)
            
            if not clean_content:
                continue

            # 2. 切片：按 1000 字符切分，重叠 200
            file_chunks = chunk_text(clean_content, chunk_size=1000, overlap=200)
            
            print(f"  -> 生成了 {len(file_chunks)} 个切片")
            all_chunks.extend(file_chunks)
            
    # 3. 保存
    with open(output_file, 'w', encoding='utf-8') as outfile:
        json.dump(all_chunks, outfile, ensure_ascii=False, indent=4)
        
    print(f"\n✅ 处理完成！")
    print(f"总共生成 {len(all_chunks)} 个上下文片段。")
    print(f"已保存至: {output_file}")

if __name__ == "__main__":
    generate_context_json_robust(data_name="test")