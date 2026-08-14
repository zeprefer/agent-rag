"""Agentic RAG 问答应用服务。

本服务装配会话记忆、附件上下文、Agent 工具和模型循环，随后持久化最终消息、
执行轨迹与真实检索引用。具体模型和 Embedding 实现由端口注入。
"""

import uuid

from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, MessageCitation
from app.models.user import User
from app.ports.ai import ChatProvider, EmbeddingProvider
from app.services.agent_runner import run_agent
from app.services.agent_runtime import (
    build_agent_config,
    build_agent_metadata,
    effective_knowledge_base_ids,
    resolve_agent,
    resolve_knowledge_base_ids,
)
from app.services.agent_tools import AgentToolRegistry, KnowledgeSearchTool
from app.services.attachments import build_attachment_context, get_attachments_for_message
from app.services.chat_sessions import ChatSessionNotFoundError, get_chat_message, get_chat_session
from app.services.chunking import estimate_token_count
from app.services.conversation_memory import load_conversation_memory


def answer_question(
    db: Session,
    *,
    chat_provider: ChatProvider,
    embedding_provider: EmbeddingProvider,
    current_user: User,
    session_id: uuid.UUID,
    question: str,
    knowledge_base_ids: list[uuid.UUID] | None = None,
    attachment_ids: list[uuid.UUID] | None = None,
) -> tuple[ChatMessage, ChatMessage]:
    session = get_chat_session(db, current_user=current_user, session_id=session_id)
    if session is None:
        raise ChatSessionNotFoundError("Chat session not found")

    agent = resolve_agent(db, tenant_id=current_user.tenant_id, agent_id=session.agent_id)
    agent_config = build_agent_config(agent)
    effective_kb_ids = effective_knowledge_base_ids(
        session=session,
        agent=agent,
        override_ids=knowledge_base_ids,
    )
    resolved_kb_ids = resolve_knowledge_base_ids(
        db,
        tenant_id=current_user.tenant_id,
        requested_ids=effective_kb_ids,
    )
    attachments = get_attachments_for_message(
        db,
        current_user=current_user,
        session_id=session.id,
        attachment_ids=attachment_ids,
    )
    attachment_context, attachment_metadata = build_attachment_context(attachments)
    history = load_conversation_memory(
        db,
        tenant_id=current_user.tenant_id,
        session_id=session.id,
        message_limit=agent_config["memory_window"],
        token_limit=max(500, agent_config["max_context_tokens"] // 3),
    )

    user_message = ChatMessage(
        tenant_id=current_user.tenant_id,
        session_id=session.id,
        role="user",
        content=question,
        input_type="mixed" if attachments else "text",
        token_count=estimate_token_count(question),
        extra_metadata={"attachments": attachment_metadata} if attachment_metadata else None,
    )
    db.add(user_message)
    db.flush()

    tools = []
    if "knowledge_search" in agent_config["enabled_tools"]:
        tools.append(
            KnowledgeSearchTool(
                db=db,
                embedding_provider=embedding_provider,
                tenant_id=current_user.tenant_id,
                knowledge_base_ids=resolved_kb_ids,
                default_top_k=agent_config["top_k"],
            )
        )
    run = run_agent(
        chat_provider=chat_provider,
        tool_registry=AgentToolRegistry(tools),
        system_prompt=agent_config["system_prompt"],
        history=history,
        question=question,
        attachment_context=attachment_context,
        model=agent_config["chat_model"],
        temperature=agent_config["temperature"],
        max_iterations=agent_config["max_iterations"],
        require_citations=agent_config["require_citations"],
    )

    assistant_message = ChatMessage(
        tenant_id=current_user.tenant_id,
        session_id=session.id,
        role="assistant",
        content=run.content,
        input_type="text",
        token_count=estimate_token_count(run.content),
        extra_metadata={
            "agent": build_agent_metadata(agent, agent_config),
            "agent_run": run.metadata,
            "memory": {"message_count": len(history)},
            "retrieval": {
                "mode": "agentic_hybrid",
                "hit_count": len(run.citations),
                "queries": [
                    item.get("query")
                    for item in run.metadata["tool_calls"]
                    if item.get("tool") == "knowledge_search" and item.get("query")
                ],
            },
            "attachments": attachment_metadata,
        },
    )
    db.add(assistant_message)
    db.flush()

    for item in run.citations:
        db.add(
            MessageCitation(
                tenant_id=current_user.tenant_id,
                message_id=assistant_message.id,
                chunk_id=item.chunk.id,
                document_id=item.document.id,
                document_title=item.document.title,
                page_number=item.chunk.page_number,
                heading_path=item.chunk.heading_path,
                score=item.score,
                quote=item.chunk.content[:1200],
            )
        )

    db.commit()
    user_message = get_chat_message(db, tenant_id=current_user.tenant_id, message_id=user_message.id) or user_message
    assistant_message = (
        get_chat_message(db, tenant_id=current_user.tenant_id, message_id=assistant_message.id)
        or assistant_message
    )
    return user_message, assistant_message
