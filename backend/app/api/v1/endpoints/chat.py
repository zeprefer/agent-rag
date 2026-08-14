"""聊天 HTTP 接口。

本文件只处理认证依赖、请求参数、状态码和 Schema 转换；问答、会话、检索等
业务逻辑委托给应用服务，外部能力由 FastAPI Depends 从组合根注入。
"""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.bootstrap import get_chat_provider, get_embedding_provider, get_object_storage, get_vision_provider
from app.models.user import User
from app.ports.ai import (
    AIProviderConfigError,
    ChatProvider,
    ChatProviderError,
    EmbeddingProvider,
    EmbeddingProviderError,
    VisionProvider,
)
from app.ports.storage import ObjectStorageError, ObjectStoragePort
from app.schemas.chat import (
    ChatAnswerResponse,
    ChatAttachmentList,
    ChatAttachmentRead,
    ChatMessageCreate,
    ChatMessageList,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionList,
    ChatSessionRead,
)
from app.services.attachments import (
    AttachmentProcessingError,
    AttachmentValidationError,
    create_chat_attachment,
    list_attachments,
)
from app.services.agent_runtime import KnowledgeBaseAccessError
from app.services.chat_answers import answer_question
from app.services.chat_sessions import (
    ChatSessionNotFoundError,
    create_chat_session,
    delete_chat_session,
    get_chat_session,
    list_chat_messages,
    list_chat_sessions,
)
from app.services.security_scan import SecurityScanError
from app.services.tenant_settings import get_or_create_tenant_settings

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionRead:
    try:
        session = create_chat_session(
            db,
            current_user=current_user,
            title=payload.title,
            agent_id=payload.agent_id,
            knowledge_base_ids=payload.knowledge_base_ids,
        )
    except KnowledgeBaseAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return ChatSessionRead.model_validate(session)


@router.get("/sessions", response_model=ChatSessionList)
def read_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionList:
    sessions = list_chat_sessions(db, current_user=current_user, skip=skip, limit=limit)
    return ChatSessionList(items=[ChatSessionRead.model_validate(item) for item in sessions])


@router.get("/sessions/{session_id}", response_model=ChatSessionRead)
def read_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionRead:
    session = get_chat_session(db, current_user=current_user, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    return ChatSessionRead.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: ObjectStoragePort = Depends(get_object_storage),
) -> Response:
    try:
        delete_chat_session(
            db,
            current_user=current_user,
            session_id=session_id,
            storage=storage,
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ObjectStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions/{session_id}/messages", response_model=ChatMessageList)
def read_messages(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageList:
    try:
        messages = list_chat_messages(db, current_user=current_user, session_id=session_id)
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ChatMessageList(items=[ChatMessageRead.model_validate(item) for item in messages])


@router.get("/sessions/{session_id}/attachments", response_model=ChatAttachmentList)
def read_attachments(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatAttachmentList:
    session = get_chat_session(db, current_user=current_user, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    attachments = list_attachments(db, current_user=current_user, session_id=session_id)
    return ChatAttachmentList(items=[ChatAttachmentRead.model_validate(item) for item in attachments])


@router.post(
    "/sessions/{session_id}/attachments",
    response_model=ChatAttachmentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_attachment(
    session_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: ObjectStoragePort = Depends(get_object_storage),
    vision_provider: VisionProvider = Depends(get_vision_provider),
) -> ChatAttachmentRead:
    session = get_chat_session(db, current_user=current_user, session_id=session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")
    try:
        tenant_settings = get_or_create_tenant_settings(db, tenant_id=current_user.tenant_id)
        attachment = await create_chat_attachment(
            db,
            current_user=current_user,
            session=session,
            file=file,
            tenant_settings=tenant_settings,
            storage=storage,
            vision_provider=vision_provider,
        )
    except AttachmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SecurityScanError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except AttachmentProcessingError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (AIProviderConfigError, ChatProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ObjectStorageError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return ChatAttachmentRead.model_validate(attachment)


@router.post("/sessions/{session_id}/messages", response_model=ChatAnswerResponse)
def create_message(
    session_id: uuid.UUID,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    chat_provider: ChatProvider = Depends(get_chat_provider),
    embedding_provider: EmbeddingProvider = Depends(get_embedding_provider),
) -> ChatAnswerResponse:
    try:
        user_message, assistant_message = answer_question(
            db,
            chat_provider=chat_provider,
            embedding_provider=embedding_provider,
            current_user=current_user,
            session_id=session_id,
            question=payload.content.strip(),
            knowledge_base_ids=payload.knowledge_base_ids,
            attachment_ids=payload.attachment_ids,
        )
    except ChatSessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AttachmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except KnowledgeBaseAccessError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AIProviderConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except (ChatProviderError, EmbeddingProviderError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return ChatAnswerResponse(
        user_message=ChatMessageRead.model_validate(user_message),
        assistant_message=ChatMessageRead.model_validate(assistant_message),
    )
