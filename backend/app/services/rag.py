"""旧版 RAG 服务兼容门面。

新代码应直接使用 ``chat_sessions``、``retrieval``、``rag_prompts`` 和
``chat_answers``。本文件保留原导入路径并从组合根补齐默认依赖，让已有调用方
能够渐进迁移；不要在此继续新增业务逻辑。
"""

import uuid

from sqlalchemy.orm import Session

from app.bootstrap import get_chat_provider, get_embedding_provider, get_object_storage
from app.models.user import User
from app.services import attachments as attachment_service
from app.services.agent_runtime import (
    KnowledgeBaseAccessError,
    build_agent_config as _agent_config,
    build_agent_metadata as _agent_metadata,
    effective_knowledge_base_ids as _effective_kb_ids,
    resolve_agent as _resolve_agent,
    resolve_knowledge_base_ids as _resolve_knowledge_base_ids,
)
from app.services.chat_answers import answer_question as _answer_question
from app.services.chat_sessions import (
    ChatSessionNotFoundError,
    create_chat_session,
    get_chat_message,
    get_chat_session,
    list_chat_messages,
    list_chat_sessions,
)
from app.services.rag_prompts import build_rag_messages
from app.services.retrieval import RetrievedChunk, retrieve_chunks as _retrieve_chunks


def delete_chat_attachments(db: Session, *, current_user: User, session_id: uuid.UUID) -> None:
    attachment_service.delete_chat_attachments(
        db,
        current_user=current_user,
        session_id=session_id,
        storage=get_object_storage(),
    )


def delete_chat_session(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
) -> None:
    # Kept explicit so mocks against the historic module path continue to work.
    session = get_chat_session(db, current_user=current_user, session_id=session_id)
    if session is None:
        raise ChatSessionNotFoundError("Chat session not found")
    delete_chat_attachments(db, current_user=current_user, session_id=session_id)
    db.delete(session)
    db.commit()


def answer_question(db: Session, **kwargs):
    return _answer_question(
        db,
        chat_provider=get_chat_provider(),
        embedding_provider=get_embedding_provider(),
        **kwargs,
    )


def retrieve_chunks(db: Session, **kwargs):
    return _retrieve_chunks(db, embedding_provider=get_embedding_provider(), **kwargs)


__all__ = [
    "ChatSessionNotFoundError",
    "KnowledgeBaseAccessError",
    "RetrievedChunk",
    "answer_question",
    "build_rag_messages",
    "create_chat_session",
    "delete_chat_session",
    "get_chat_message",
    "get_chat_session",
    "list_chat_messages",
    "list_chat_sessions",
    "retrieve_chunks",
]
