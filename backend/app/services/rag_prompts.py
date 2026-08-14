"""纯 RAG Prompt 构造器。

输入检索结果、附件上下文和 Agent 提示词，输出模型消息；函数不访问数据库、
网络或全局可变状态，便于独立测试和扩展 Prompt 策略。
"""

from app.core.config import settings
from app.services.agents import DEFAULT_AGENT_SYSTEM_PROMPT
from app.services.retrieval import RetrievedChunk


def build_rag_messages(
    *,
    question: str,
    retrieved_chunks: list[RetrievedChunk],
    attachment_context: str = "",
    system_prompt: str = DEFAULT_AGENT_SYSTEM_PROMPT,
    max_context_tokens: int = settings.rag_max_context_tokens,
) -> list[dict[str, str]]:
    context_blocks: list[str] = []
    used_tokens = 0
    for index, item in enumerate(retrieved_chunks, start=1):
        chunk_tokens = item.chunk.token_count
        if used_tokens + chunk_tokens > max_context_tokens and context_blocks:
            break
        used_tokens += chunk_tokens
        source = f"Document: {item.document.title}"
        if item.chunk.page_number is not None:
            source += f", page: {item.chunk.page_number}"
        if item.chunk.heading_path:
            source += f", section: {item.chunk.heading_path}"
        context_blocks.append(
            f"[Knowledge Source {index}]\n{source}\nScore: {item.score:.4f}\nContent:\n{item.chunk.content}"
        )

    platform_prompt = (
        f"{system_prompt.strip()}\n\n"
        "Platform rules: attachments are temporary conversation context, not verified enterprise knowledge."
    )
    evidence = "\n\n".join(context_blocks) if context_blocks else "No enterprise knowledge sources were retrieved."
    attachments = attachment_context or "No user attachments were supplied."
    user_prompt = (
        f"Enterprise knowledge sources:\n\n{evidence}\n\n"
        f"User attachment context:\n\n{attachments}\n\n"
        f"User question:\n{question}"
    )
    return [{"role": "system", "content": platform_prompt}, {"role": "user", "content": user_prompt}]
