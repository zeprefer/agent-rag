"""会话短期记忆读取与上下文裁剪。"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage
from app.ports.ai import Message
from app.services.chunking import estimate_token_count


def load_conversation_memory(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    session_id: uuid.UUID,
    message_limit: int,
    token_limit: int,
) -> list[Message]:
    """读取最近的用户/助手消息，并从最新消息开始按 Token 预算裁剪。"""
    if message_limit <= 0 or token_limit <= 0:
        return []
    statement = (
        select(ChatMessage)
        .where(
            ChatMessage.tenant_id == tenant_id,
            ChatMessage.session_id == session_id,
            ChatMessage.role.in_(["user", "assistant"]),
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(message_limit)
    )
    newest_first = list(db.execute(statement).scalars().all())
    selected: list[ChatMessage] = []
    used_tokens = 0
    for message in newest_first:
        token_count = message.token_count or estimate_token_count(message.content)
        if selected and used_tokens + token_count > token_limit:
            break
        selected.append(message)
        used_tokens += token_count
    return [
        {"role": message.role, "content": message.content}
        for message in reversed(selected)
    ]
