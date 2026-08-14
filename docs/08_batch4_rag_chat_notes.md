# Batch 4: RAG Chat Backend Notes

## Runtime Flow

1. User creates a chat session with optional knowledge base scope.
2. User sends a text question.
3. The backend embeds the question with Bailian/DashScope.
4. The retriever searches `knowledge_chunks` through pgvector cosine similarity.
5. SQL filters enforce `tenant_id`, selected knowledge bases, indexed documents, and active knowledge bases.
6. The prompt builder creates numbered evidence blocks.
7. Bailian/DashScope Chat generates the answer.
8. The backend stores user message, assistant message, and citations.

## Required Environment

```env
DASHSCOPE_API_KEY=your-api-key
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_CHAT_MODEL=qwen-plus
BAILIAN_EMBEDDING_MODEL=text-embedding-v4
BAILIAN_EMBEDDING_DIMENSIONS=1024
RAG_TOP_K=8
RAG_MAX_CONTEXT_TOKENS=3500
RAG_TEMPERATURE=0.2
```

## Implemented API

- `POST /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions`
- `GET /api/v1/chat/sessions/{session_id}`
- `GET /api/v1/chat/sessions/{session_id}/messages`
- `POST /api/v1/chat/sessions/{session_id}/messages`

## Current Scope

Batch 4 implements non-streaming text RAG. Image/file question handling and SSE streaming should be added after this core retrieval-answer-citation loop is verified end to end.

