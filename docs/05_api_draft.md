# API 草案

## 1. API 规范

- Base path: `/api/v1`
- 认证方式：JWT Bearer Token
- 返回格式：JSON
- 文件上传：`multipart/form-data`
- 流式回答：Server-Sent Events

## 2. 认证

### POST `/auth/login`

请求：

```json
{
  "email": "admin@example.com",
  "password": "password"
}
```

响应：

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "tenant_id": "uuid",
    "role": "admin"
  }
}
```

## 3. 管理端 API

### POST `/admin/knowledge-bases`

创建知识库。

```json
{
  "name": "产品知识库",
  "description": "公司产品说明、FAQ、售后政策"
}
```

### GET `/admin/knowledge-bases`

查询知识库列表。

### POST `/admin/knowledge-bases/{kb_id}/documents`

上传知识文档。

表单字段：

- `file`: docx/doc/pdf/md
- `title`: 可选
- `tags`: 可选

响应：

```json
{
  "document_id": "uuid",
  "version_id": "uuid",
  "status": "uploaded"
}
```

### GET `/admin/documents/{document_id}`

查询文档详情、版本、解析状态。

### POST `/admin/documents/{document_id}/reindex`

重新解析和索引文档。

### GET `/admin/index-jobs`

查询解析和索引任务列表。

### GET `/admin/memories`

查询三级记忆。

查询参数：

- `knowledge_base_id`
- `level`: `raw`, `chunk`, `semantic`
- `memory_type`

### PATCH `/admin/agent-config`

配置 Agent。

```json
{
  "chat_model": "qwen-plus",
  "embedding_model": "text-embedding-v4",
  "top_k": 8,
  "temperature": 0.2,
  "system_prompt": "你是企业知识助手..."
}
```

## 4. 用户端 API

### POST `/chat/sessions`

创建会话。

```json
{
  "title": "售后政策咨询",
  "knowledge_base_ids": ["uuid"]
}
```

### GET `/chat/sessions`

查询用户会话列表。

### GET `/chat/sessions/{session_id}/messages`

查询会话消息。

### POST `/chat/sessions/{session_id}/messages`

发送普通问题。

```json
{
  "content": "客户购买后 7 天内是否可以无理由退货？",
  "knowledge_base_ids": ["uuid"],
  "stream": false
}
```

响应：

```json
{
  "message_id": "uuid",
  "answer": "根据售后政策...",
  "citations": [
    {
      "document_title": "售后政策.pdf",
      "page_number": 3,
      "chunk_id": "uuid",
      "score": 0.82,
      "snippet": "..."
    }
  ]
}
```

### POST `/chat/sessions/{session_id}/messages/stream`

流式发送问题，返回 SSE。

事件类型：

- `retrieval`
- `delta`
- `citation`
- `done`
- `error`

### POST `/chat/sessions/{session_id}/attachments`

上传用户临时附件。

表单字段：

- `file`: 图片或文档
- `purpose`: `question_context`

### POST `/chat/messages/{message_id}/feedback`

提交反馈。

```json
{
  "rating": "up",
  "comment": "回答有帮助"
}
```

## 5. 内部服务接口

### POST `/internal/documents/{version_id}/parse`

触发解析任务。

### POST `/internal/chunks/{chunk_id}/embed`

触发向量化任务。

### POST `/internal/knowledge-bases/{kb_id}/semantic-memory/rebuild`

重建企业语义记忆。

## 6. 错误码

| 错误码 | 说明 |
| --- | --- |
| `AUTH_INVALID_TOKEN` | Token 无效 |
| `PERMISSION_DENIED` | 无权限 |
| `FILE_TYPE_NOT_SUPPORTED` | 文件类型不支持 |
| `DOCUMENT_PARSE_FAILED` | 文档解析失败 |
| `EMBEDDING_FAILED` | 向量化失败 |
| `RETRIEVAL_EMPTY` | 未检索到相关知识 |
| `LLM_PROVIDER_ERROR` | 模型服务调用失败 |

