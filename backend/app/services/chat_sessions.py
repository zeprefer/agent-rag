"""聊天会话生命周期服务。

只负责会话及消息的创建、查询和删除；模型调用、向量检索与 Prompt 构造由其他
高内聚服务承担。删除会话时通过存储端口清理附件对象。
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.chat import ChatMessage, ChatSession
from app.models.user import User
from app.ports.storage import ObjectStoragePort
from app.services.agent_runtime import resolve_agent, resolve_knowledge_base_ids
from app.services.attachments import delete_chat_attachments


class ChatSessionNotFoundError(RuntimeError):
    pass


def create_chat_session(
    db: Session,
    *,
    current_user: User,
    title: str | None,
    agent_id: uuid.UUID | None,
    knowledge_base_ids: list[uuid.UUID] | None,
) -> ChatSession:
    agent = resolve_agent(db, tenant_id=current_user.tenant_id, agent_id=agent_id)
    resolved_kb_ids = resolve_knowledge_base_ids(
        db,
        tenant_id=current_user.tenant_id,
        requested_ids=knowledge_base_ids,
    )
    session = ChatSession(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        agent_id=agent.id if agent is not None else None,
        title=(title or "New chat").strip() or "New chat",
        knowledge_base_ids=[str(item) for item in resolved_kb_ids] if resolved_kb_ids else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_chat_sessions(
    db: Session,
    *,
    current_user: User,
    skip: int = 0,
    limit: int = 50,
) -> list[ChatSession]:
    statement = (
        select(ChatSession)
        .where(
            ChatSession.tenant_id == current_user.tenant_id,
            ChatSession.user_id == current_user.id,
            ChatSession.status == "active",
        )
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(statement).scalars().all())


def get_chat_session(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
) -> ChatSession | None:
    statement = select(ChatSession).where(
        ChatSession.id == session_id,
        ChatSession.tenant_id == current_user.tenant_id,
        ChatSession.user_id == current_user.id,
        ChatSession.status == "active",
    )
    return db.execute(statement).scalar_one_or_none()


def delete_chat_session(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
    storage: ObjectStoragePort,
) -> None:
    session = get_chat_session(db, current_user=current_user, session_id=session_id)
    if session is None:
        raise ChatSessionNotFoundError("Chat session not found")
    delete_chat_attachments(
        db,
        current_user=current_user,
        session_id=session_id,
        storage=storage,
    )
    db.delete(session)
    db.commit()


def list_chat_messages(
    db: Session,
    *,
    current_user: User,
    session_id: uuid.UUID,
) -> list[ChatMessage]:
    session = get_chat_session(db, current_user=current_user, session_id=session_id)
    if session is None:
        raise ChatSessionNotFoundError("Chat session not found")
    statement = (
        select(ChatMessage)
        .options(selectinload(ChatMessage.citations))
        .where(ChatMessage.tenant_id == current_user.tenant_id, ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at)
    )
    return list(db.execute(statement).scalars().all())


def get_chat_message(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    message_id: uuid.UUID,
) -> ChatMessage | None:
    statement = (
        select(ChatMessage)
        .options(selectinload(ChatMessage.citations))
        .where(ChatMessage.tenant_id == tenant_id, ChatMessage.id == message_id)
    )
    return db.execute(statement).scalar_one_or_none()
