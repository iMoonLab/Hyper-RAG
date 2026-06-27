"""Token-window text chunking helpers."""

from .utils import decode_tokens_by_tiktoken, encode_string_by_tiktoken


def chunking_by_token_size(
    content: str, overlap_token_size=128, max_token_size=1024, tiktoken_model="gpt-4o"
):
    """按 token 长度切块。

    注意：这里不是语义切分，而是固定 token 窗口 + overlap。
    返回的每个 chunk 会带 tokens、content、chunk_order_index。
    """
    tokens = encode_string_by_tiktoken(content, model_name=tiktoken_model)
    results = []
    for index, start in enumerate(
        range(0, len(tokens), max_token_size - overlap_token_size)
    ):
        chunk_content = decode_tokens_by_tiktoken(
            tokens[start : start + max_token_size], model_name=tiktoken_model
        )
        results.append(
            {
                "tokens": min(max_token_size, len(tokens) - start),
                "content": chunk_content.strip(),
                "chunk_order_index": index,
            }
        )
    return results
