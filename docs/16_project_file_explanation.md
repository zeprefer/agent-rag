# Enterprise Agent RAG 项目文件详解

本文档用于解释当前项目的整体结构、核心文件职责、模块之间的关系，以及一次完整业务流程如何在系统中流转。

## 1. 项目整体定位

本项目是一个面向企业知识库的 AI Agent + RAG 系统。

它包含：

- 管理端：用于企业管理员维护知识库、上传文档、管理 Agent、用户、权限、审计和租户配置。
- 用户端：用于企业用户选择 Agent、发起问答、上传附件并查看带引用的回答。
- 后端：基于 FastAPI，负责认证、权限、知识库管理、文档处理、RAG 检索、百炼模型调用和审计记录。
- 数据库：PostgreSQL + pgvector，用于保存业务数据和向量索引。
- Redis：用于缓存、限流和 Celery 任务队列。
- MinIO：作为 S3 兼容对象存储，保存上传的原始文件。
- Celery Worker：异步执行文档解析、切片、向量化任务。

系统目标不是简单 Demo，而是一个可扩展的企业级 Agent/RAG 项目基础。

## 2. 顶层目录结构

```text
agent_rag/
├─ backend/
├─ docs/
├─ frontend/
│  ├─ admin/
│  └─ user/
├─ scripts/
├─ .env.example
├─ .gitignore
├─ docker-compose.yml
└─ README.md
```

各目录作用：

- `backend/`：Python FastAPI 后端工程。
- `docs/`：产品文档、架构文档、批次交付文档和演示资料。
- `frontend/admin/`：管理端静态前端。
- `frontend/user/`：用户端静态前端。
- `scripts/`：本地部署、健康检查、冒烟测试脚本。
- `.env.example`：环境变量模板。
- `docker-compose.yml`：本地 Docker 编排文件。
- `README.md`：项目启动和基础说明。

## 3. 顶层关键文件

### 3.1 README.md

`README.md` 是项目入口说明文档。

它说明：

- 项目用途。
- Docker 启动方式。
- 后端、管理端、用户端访问地址。
- 阿里百炼模型环境变量配置。
- 常用命令。
- 文档目录入口。

### 3.2 .env.example

`.env.example` 是环境变量模板。

真实部署时需要复制为 `.env`：

```powershell
Copy-Item .env.example .env
```

主要配置包括：

- 数据库连接：`DATABASE_URL`
- Redis 地址：`REDIS_URL`
- Celery 队列：`CELERY_BROKER_URL`
- MinIO/S3：`S3_ENDPOINT_URL`、`S3_ACCESS_KEY_ID`、`S3_SECRET_ACCESS_KEY`
- JWT：`JWT_SECRET_KEY`
- 百炼/DashScope：`DASHSCOPE_API_KEY`
- 模型配置：`BAILIAN_CHAT_MODEL`、`BAILIAN_EMBEDDING_MODEL`、`BAILIAN_VISION_MODEL`
- 上传大小和文件类型配置
- RAG 参数配置

### 3.3 docker-compose.yml

`docker-compose.yml` 用于一键启动完整本地环境。

它包含以下服务：

| 服务 | 作用 |
|---|---|
| `postgres` | PostgreSQL + pgvector，保存业务数据和向量 |
| `redis` | 缓存、限流、Celery 队列 |
| `minio` | S3 兼容对象存储，保存上传文件 |
| `api` | FastAPI 后端服务 |
| `worker` | Celery 异步任务服务 |
| `admin` | 管理端前端 |
| `user` | 用户端前端 |

默认访问地址：

```text
API Docs: http://localhost:8000/docs
Admin: http://localhost:5173
User: http://localhost:5174
MinIO: http://localhost:9001
```

## 4. backend 后端结构

后端目录：

```text
backend/
├─ alembic/
├─ app/
├─ Dockerfile
├─ README.md
├─ alembic.ini
└─ requirements.txt
```

### 4.1 requirements.txt

`requirements.txt` 定义后端依赖。

主要依赖：

- `fastapi`：Web API 框架。
- `uvicorn`：ASGI 服务。
- `SQLAlchemy`：ORM。
- `alembic`：数据库迁移。
- `psycopg`：PostgreSQL 驱动。
- `redis`：Redis 客户端。
- `celery`：异步任务。
- `boto3`：S3/MinIO 对象存储客户端。
- `openai`：调用 OpenAI-compatible API，这里用于阿里百炼。
- `pgvector`：PostgreSQL 向量字段支持。
- `pypdf`：PDF 解析。
- `python-docx`：DOCX 解析。

### 4.2 Dockerfile

`backend/Dockerfile` 用于构建后端镜像。

`api` 和 `worker` 两个服务都基于这个镜像。

## 5. 数据库迁移 alembic

目录：

```text
backend/alembic/versions/
```

迁移文件按批次演进。

### 5.1 0001_initial_auth.py

创建基础认证表：

- `tenants`
- `users`

同时启用 PostgreSQL 的 `vector` 扩展，用于 pgvector 向量检索。

### 5.2 0002_knowledge_documents.py

创建知识库和文档相关表：

- `knowledge_bases`
- `documents`
- `document_versions`

文档版本表用于保证上传资料可追溯。

### 5.3 0003_processing_chunks_embeddings.py

创建索引处理和向量表：

- `document_processing_jobs`
- `knowledge_chunks`
- `chunk_embeddings`

关系为：

```text
DocumentVersion -> KnowledgeChunk -> ChunkEmbedding
```

### 5.4 0004_chat_rag.py

创建聊天和引用相关表：

- `chat_sessions`
- `chat_messages`
- `message_citations`

用于保存用户问题、AI 回答和引用来源。

### 5.5 0005_chat_attachments.py

创建聊天附件表：

- `chat_attachments`

用于保存用户临时上传的图片或文件附件。

### 5.6 0006_rbac_audit_tenant_settings.py

创建企业治理相关表：

- `tenant_settings`
- `audit_logs`

用于租户级配置和操作审计。

### 5.7 0007_agent_configuration.py

创建 Agent 配置表：

- `agents`

并给 `chat_sessions` 增加：

- `agent_id`

这样每个聊天会话可以绑定具体 Agent 策略，让用户可以选择不同的 Agent 进行对话。

## 6. app 后端核心代码

目录：

```text
backend/app/
├─ api/
├─ infrastructure/
├─ ports/
├─ core/
├─ db/
├─ middleware/
├─ models/
├─ schemas/
├─ services/
├─ bootstrap.py
├─ cli.py
├─ main.py
├─ tasks.py
└─ worker.py
```

重构后的依赖方向为：

```text
API / Worker
    -> services（业务用例）
    -> ports（稳定能力接口）
    <- infrastructure（厂商和中间件适配器）

bootstrap.py 负责把端口与生产适配器装配起来
```

- `ports/`：定义 AI、对象存储和后台任务能力，不引用厂商 SDK。
- `infrastructure/`：放置百炼、S3/MinIO、Celery 等具体实现。
- `bootstrap.py`：唯一的生产依赖组合入口，FastAPI 和 Worker 从这里获取实现。
- `services/`：面向业务用例编排，只依赖模型、数据库抽象和 ports。

## 7. 后端入口文件

### 7.1 app/main.py

`main.py` 是 FastAPI 应用入口。

它负责：

- 初始化日志。
- 创建 FastAPI app。
- 注册请求日志中间件。
- 注册限流中间件。
- 注册安全响应头中间件。
- 注册 CORS。
- 挂载 `/api/v1` 路由。

### 7.2 app/api/v1/api.py

这是所有 API 路由的总入口。

已注册的路由包括：

```text
/auth
/admin/knowledge-bases
/admin/agents
/admin/documents
/admin/index-jobs
/admin/users
/admin/audit-logs
/admin/tenant-settings
/chat
/agents
/health
```

## 8. core 核心配置、安全和权限

目录：

```text
backend/app/core/
```

### 8.1 config.py

统一读取环境变量。

它管理：

- 数据库配置。
- Redis 配置。
- S3/MinIO 配置。
- JWT 配置。
- CORS 配置。
- 文件上传限制。
- 百炼模型配置。
- RAG 参数。

### 8.2 security.py

负责：

- 密码哈希。
- 密码校验。
- JWT Token 创建。

### 8.3 rbac.py

定义角色和权限。

当前角色：

| 角色 | 权限 |
|---|---|
| `admin` | 所有管理权限 |
| `manager` | 知识库、文档、Agent 管理 |
| `user` | 用户端问答 |

权限包括：

- `knowledge:manage`
- `users:manage`
- `audit:read`
- `tenant_settings:manage`
- `chat:use`

## 9. db 数据库连接层

目录：

```text
backend/app/db/
```

### 9.1 base.py

定义 SQLAlchemy 基类和时间戳 mixin。

所有模型都继承统一的 `Base`。

### 9.2 session.py

创建数据库 engine 和 Session 工厂。

API 每次请求都会从这里获取数据库 Session。

## 10. middleware 中间件

目录：

```text
backend/app/middleware/
```

### 10.1 request_logging.py

记录请求日志。

同时设置请求 ID，方便排查问题。

### 10.2 rate_limit.py

基于 Redis 做固定窗口限流。

用于保护接口，避免被大量请求压垮。

### 10.3 security_headers.py

添加安全响应头。

用于提升 Web 安全基础能力。

## 11. models 数据库模型

目录：

```text
backend/app/models/
```

### 11.1 tenant.py

企业租户模型。

每个企业对应一个租户。

### 11.2 user.py

用户模型。

字段包括：

- 邮箱
- 用户名
- 密码哈希
- 角色
- 状态
- 所属租户

### 11.3 knowledge_base.py

知识库模型。

管理端创建知识库后，会写入这个表。

### 11.4 document.py

文档和文档版本模型。

包含：

- `Document`
- `DocumentVersion`

设计文档版本的原因是企业资料需要可审计、可追溯。

### 11.5 knowledge_chunk.py

知识片段和向量模型。

包含：

- `KnowledgeChunk`
- `ChunkEmbedding`

每个 chunk 是文档被解析切片后的文本片段。

每个 embedding 是 chunk 对应的向量。

### 11.6 processing.py

文档处理任务模型。

记录异步索引状态：

- `queued`
- `running`
- `success`
- `failed`

### 11.7 chat.py

聊天相关模型。

包含：

- `ChatSession`
- `ChatMessage`
- `MessageCitation`
- `ChatAttachment`

其中：

- `ChatSession` 表示一次会话。
- `ChatMessage` 保存用户问题和 AI 回答。
- `MessageCitation` 保存回答引用的知识来源。
- `ChatAttachment` 保存用户临时附件。

### 11.8 agent.py

Agent 配置模型。

每个 Agent 可以配置：

- 名称
- 描述
- 系统提示词
- 默认知识库
- 模型名
- temperature
- top_k
- 最大上下文长度
- 状态

### 11.9 audit.py

审计日志模型。

用于记录：

- 谁操作
- 操作了什么
- 操作对象
- 操作结果
- 请求来源
- 请求时间

### 11.10 tenant_settings.py

租户配置模型。

用于配置：

- 默认语言
- 支持的知识库文件类型
- 最大上传大小
- 最大附件大小
- RAG top_k
- RAG temperature
- 是否启用审计
- 是否启用上传安全扫描
- 数据保留天数

## 12. schemas API 数据结构

目录：

```text
backend/app/schemas/
```

schemas 是 API 的输入输出结构。

它不直接代表数据库，而是代表接口格式。

主要文件：

- `auth.py`：登录请求、Token 返回。
- `user.py`：用户返回结构。
- `knowledge_base.py`：知识库创建、更新、读取结构。
- `document.py`：文档和版本返回结构。
- `chunk.py`：知识片段返回结构。
- `processing.py`：索引任务返回结构。
- `chat.py`：会话、消息、引用、附件结构。
- `agent.py`：Agent 创建、更新、读取结构。
- `admin.py`：用户管理、角色、审计、租户配置结构。

三者关系：

```text
models  = 数据库结构
schemas = API 输入输出结构
services = 业务逻辑
```

## 13. services 业务逻辑层

目录：

```text
backend/app/services/
```

### 13.1 users.py

处理用户和租户逻辑：

- 创建租户。
- 创建用户。
- 用户登录认证。
- 用户列表。
- 用户更新。
- 用户禁用。

### 13.2 knowledge_bases.py

处理知识库 CRUD：

- 创建知识库。
- 查询知识库。
- 更新知识库。
- 归档知识库。

### 13.3 documents.py

处理文档上传。

流程：

1. 校验文件名。
2. 校验扩展名。
3. 校验上传大小。
4. 安全扫描。
5. 计算文件 SHA256。
6. 写入 MinIO。
7. 创建 Document。
8. 创建 DocumentVersion。

### 13.4 object_storage.py

这是旧导入路径的兼容门面。

真正的 S3/MinIO 实现在：

```text
app/infrastructure/storage/s3.py
```

主要能力：

- 上传 bytes。
- 下载 bytes。
- 删除 object。
- 确保存储桶存在。

### 13.5 security_scan.py

上传文件安全扫描。

检查内容包括：

- EICAR 测试病毒字符串。
- PDF 风险标记，如 JavaScript、OpenAction 等。
- Office 宏和可执行内容。
- 文件扩展名与基础签名。

### 13.6 document_parsers.py

文档解析。

支持：

- `pdf`
- `docx`
- `doc`
- `md`
- `txt`

`.doc` 文件依赖 LibreOffice 转换为 docx 后解析。

### 13.7 chunking.py

文本切片。

它把解析后的长文本切成适合 embedding 和检索的小片段。

### 13.8 ai_providers.py

这是旧 AI Provider 导入路径的兼容门面。

AI 能力协议位于：

```text
app/ports/ai.py
```

阿里百炼适配器位于：

```text
app/infrastructure/ai/bailian.py
```

包含：

- `BailianEmbeddingProvider`
- `BailianChatProvider`
- `BailianVisionProvider`

它通过 OpenAI-compatible API 调用百炼：

```text
https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 13.9 indexing.py

这是旧索引服务的兼容门面。新代码按读写职责拆分：

- `indexing_commands.py`：创建、执行和失败处理等写操作及状态机。
- `indexing_queries.py`：索引任务列表和文档分块查询。

流程：

1. 获取当前文档版本。
2. 从 MinIO 读取原始文件。
3. 解析文档文本。
4. 文本切片。
5. 调用百炼 embedding。
6. 写入 chunks。
7. 写入向量。
8. 更新任务状态。
9. 更新文档状态。

### 13.10 rag.py

这是旧 RAG 服务的兼容门面，新问答流程已按职责拆分：

- `agent_runtime.py`：Agent 和知识库运行策略。
- `chat_sessions.py`：会话及消息生命周期。
- `retrieval.py`：向量检索。
- `rag_prompts.py`：纯 Prompt 构造。
- `chat_answers.py`：完整问答用例编排。

用户提问后：

1. 找到聊天会话。
2. 读取会话绑定的 Agent。
3. 读取 Agent 策略。
4. 解析知识库范围。
5. 处理用户附件上下文。
6. 将问题向量化。
7. 在 pgvector 中做相似度检索。
8. 构造 RAG prompt。
9. 调用百炼 Chat。
10. 保存用户消息。
11. 保存 AI 回答。
12. 保存引用来源。

### 13.11 attachments.py

处理用户聊天附件。

支持：

- 文档附件：解析成文本。
- 图片附件：调用百炼视觉模型提取信息。

注意：用户附件只作为当前会话上下文，不会写入企业正式知识库。

### 13.12 agents.py

处理 Agent 配置。

Agent 控制：

- 系统提示词。
- 默认知识库。
- 模型名。
- temperature。
- top_k。
- 最大上下文长度。
- 发布状态。

### 13.13 audit.py

处理审计日志。

用于记录关键管理动作。

### 13.14 tenant_settings.py

处理租户配置。

配置会影响：

- 企业文档上传扩展名。
- 企业文档最大上传大小。
- 用户附件最大上传大小。

## 14. API endpoints

目录：

```text
backend/app/api/v1/endpoints/
```

### 14.1 auth.py

认证接口：

```text
POST /api/v1/auth/login
GET  /api/v1/auth/me
```

### 14.2 admin_knowledge_bases.py

知识库管理接口：

```text
GET    /api/v1/admin/knowledge-bases
POST   /api/v1/admin/knowledge-bases
GET    /api/v1/admin/knowledge-bases/{kb_id}
PATCH  /api/v1/admin/knowledge-bases/{kb_id}
DELETE /api/v1/admin/knowledge-bases/{kb_id}
```

### 14.3 admin_documents.py

文档管理接口：

```text
GET  /api/v1/admin/knowledge-bases/{kb_id}/documents
POST /api/v1/admin/knowledge-bases/{kb_id}/documents
GET  /api/v1/admin/documents/{document_id}
```

### 14.4 admin_indexing.py

索引管理接口：

```text
POST /api/v1/admin/documents/{document_id}/index
GET  /api/v1/admin/index-jobs
GET  /api/v1/admin/documents/{document_id}/chunks
```

### 14.5 admin_agents.py

Agent 管理接口：

```text
GET    /api/v1/admin/agents
POST   /api/v1/admin/agents
GET    /api/v1/admin/agents/{agent_id}
PATCH  /api/v1/admin/agents/{agent_id}
DELETE /api/v1/admin/agents/{agent_id}
```

### 14.6 agents.py

用户端获取已发布 Agent：

```text
GET /api/v1/agents
```

### 14.7 chat.py

用户端聊天接口：

```text
POST /api/v1/chat/sessions
GET  /api/v1/chat/sessions
GET  /api/v1/chat/sessions/{session_id}
GET  /api/v1/chat/sessions/{session_id}/messages
POST /api/v1/chat/sessions/{session_id}/messages
POST /api/v1/chat/sessions/{session_id}/attachments
GET  /api/v1/chat/sessions/{session_id}/attachments
```

### 14.8 admin_users.py

用户和角色管理：

```text
GET    /api/v1/admin/roles
GET    /api/v1/admin/users
POST   /api/v1/admin/users
PATCH  /api/v1/admin/users/{user_id}
DELETE /api/v1/admin/users/{user_id}
```

### 14.9 admin_audit.py

审计日志：

```text
GET /api/v1/admin/audit-logs
```

### 14.10 admin_tenant_settings.py

租户配置：

```text
GET   /api/v1/admin/tenant-settings
PATCH /api/v1/admin/tenant-settings
```

### 14.11 health.py

健康检查：

```text
GET /api/v1/health
GET /api/v1/ready
```

## 15. Celery 异步任务

### 15.1 worker.py

定义 Celery 应用。

### 15.2 tasks.py

定义异步任务。

当前核心任务是文档索引任务。

流程：

```text
管理端点击 Index
-> API 创建 queued job
-> Celery worker 执行解析、切片、向量化
-> 更新 job 状态
```

## 16. CLI 工具

文件：

```text
backend/app/cli.py
```

用于创建第一个管理员。

命令：

```powershell
docker compose exec api python -m app.cli create-admin --email admin@example.com --password "ChangeMe123!" --tenant-name "Demo Enterprise" --if-not-exists
```

`--if-not-exists` 表示用户已存在时不报错，便于重复部署。

## 17. 管理端前端

目录：

```text
frontend/admin/
```

文件：

- `index.html`：页面结构。
- `styles.css`：页面样式。
- `app.js`：管理端状态、事件和视图编排。
- `api-client.js`：HTTP、Token 和统一错误处理。
- `ui-utils.js`：日期、字节数和 HTML 转义等无状态工具。
- `package.json`：声明浏览器模块源码采用 ES Module 语义。
- `Dockerfile`：构建管理端静态服务。
- `nginx.conf`：Nginx 配置。

管理端功能：

- 登录。
- 知识库创建和刷新。
- 文档上传。
- 文档状态查看。
- 文档版本查看。
- 索引任务触发。
- 索引任务查看。
- chunks 查看。
- Agent 创建、发布、归档。
- 用户创建和禁用。
- 角色查看。
- 租户配置。
- 审计日志查看。

管理端主要调用：

```text
/api/v1/admin/...
```

## 18. 用户端前端

目录：

```text
frontend/user/
```

文件：

- `index.html`：页面结构。
- `styles.css`：页面样式。
- `app.js`：聊天状态、事件和视图编排。
- `api-client.js`：HTTP、Token 和统一错误处理。
- `ui-utils.js`：日期和 HTML 转义等无状态工具。
- `package.json`：声明浏览器模块源码采用 ES Module 语义。
- `Dockerfile`：构建用户端静态服务。
- `nginx.conf`：Nginx 配置。

用户端功能：

- 登录。
- 选择已发布 Agent。
- 创建聊天会话。
- 输入问题。
- 上传附件。
- 查看 AI 回答。
- 查看引用来源。

用户端主要调用：

```text
/api/v1/agents
/api/v1/chat/...
```

## 19. docs 文档目录

目录：

```text
docs/
```

主要文档：

- `01_product_requirements.md`：产品需求。
- `02_system_architecture.md`：系统架构。
- `03_memory_and_rag_design.md`：三级记忆与 RAG 设计。
- `04_data_model.md`：数据模型。
- `05_api_draft.md`：API 草案。
- `06_development_plan.md`：开发计划。
- `07_batch3_indexing_notes.md`：文档解析、切片、向量化说明。
- `08_batch4_rag_chat_notes.md`：RAG 问答后端说明。
- `09_batch5_admin_frontend_notes.md`：管理端前端说明。
- `10_batch6_user_frontend_notes.md`：用户端前端说明。
- `11_user_attachment_rag_notes.md`：用户附件问答说明。
- `12_batch7_enterprise_hardening.md`：质量、安全、部署增强说明。
- `13_batch8_acceptance_and_demo.md`：验收和演示闭环说明。
- `14_batch9_permissions_audit_tenant_settings.md`：权限、审计、租户配置说明。
- `15_batch10_agent_configuration.md`：Agent 配置和运行策略说明。
- `16_project_file_explanation.md`：当前文档。
- `17_modular_architecture.md`：低耦合、高内聚的模块边界和扩展约束。
- `18_agentic_rag_implementation.md`：Agent 工具调用、混合检索、会话记忆和执行轨迹实现。

演示文档：

```text
docs/demo/enterprise_policy.md
```

冒烟测试会上传它作为示例知识文档。

## 20. scripts 脚本目录

目录：

```text
scripts/
```

### 20.1 deploy-local.ps1

本地部署脚本。

功能：

1. 如果没有 `.env`，从 `.env.example` 创建。
2. 启动 Docker Compose。
3. 执行数据库迁移。
4. 创建管理员。

### 20.2 healthcheck.ps1

健康检查脚本。

检查：

- API 是否可访问。
- 管理端是否可访问。
- 用户端是否可访问。
- Docker Compose 服务状态。

### 20.3 smoke-docker.ps1

Docker 冒烟测试脚本。

基础模式：

```powershell
.\scripts\smoke-docker.ps1 -CreateAdmin
```

验证：

- API ready。
- 登录。
- 创建知识库。
- 上传演示文档。
- 创建索引任务。

完整 RAG 模式：

```powershell
.\scripts\smoke-docker.ps1 -CreateAdmin -RunModelChecks
```

额外验证：

- 文档向量化。
- chunks 生成。
- 创建聊天会话。
- 调用百炼问答。
- 返回引用。

## 21. 一次完整管理端业务流程

```text
管理员登录
-> 创建知识库
-> 上传企业文档
-> 文件写入 MinIO
-> 数据库写入 Document 和 DocumentVersion
-> 管理员点击 Index
-> API 创建 DocumentProcessingJob
-> Celery Worker 执行索引
-> 读取 MinIO 原始文件
-> 解析文档文本
-> 切片
-> 调用百炼 Embedding
-> 写入 KnowledgeChunk
-> 写入 ChunkEmbedding
-> 文档状态变成 indexed
```

## 22. 一次完整用户问答流程

```text
用户登录
-> 获取已发布 Agent
-> 选择 Agent
-> 创建聊天会话
-> 输入问题
-> 可选上传图片或文件
-> 后端读取 Agent 策略
-> 处理附件上下文
-> 将问题向量化
-> 按租户和知识库权限检索 chunks
-> 构造 RAG prompt
-> 调用百炼 Chat
-> 保存用户消息
-> 保存 AI 回答
-> 保存引用来源
-> 前端展示回答和 citations
```

## 23. Agent 在系统中的作用

Agent 是企业问答策略配置。

一个 Agent 可以定义：

- 回答身份。
- 系统提示词。
- 默认知识库范围。
- 使用哪个模型。
- 检索多少条 chunk。
- 回答随机性。
- 最大上下文长度。
- 是否发布给用户使用。

如果用户没有选择 Agent，系统会使用默认企业助手策略。

## 24. 权限和审计关系

当前角色：

```text
admin
manager
user
```

权限关系：

```text
admin:
  - 用户管理
  - 租户配置
  - 审计查看
  - 知识库管理
  - Agent 管理
  - 用户端问答

manager:
  - 知识库管理
  - 文档管理
  - Agent 管理
  - 用户端问答

user:
  - 用户端问答
```

审计记录覆盖：

- 登录。
- 创建用户。
- 修改用户。
- 禁用用户。
- 创建知识库。
- 更新知识库。
- 归档知识库。
- 上传文档。
- 触发索引。
- 创建 Agent。
- 修改 Agent。
- 归档 Agent。
- 修改租户配置。

## 25. 核心数据关系图

```text
Tenant
├─ Users
├─ TenantSettings
├─ KnowledgeBases
│  └─ Documents
│     └─ DocumentVersions
│        └─ KnowledgeChunks
│           └─ ChunkEmbeddings
├─ Agents
│  └─ default_knowledge_base_ids
├─ ChatSessions
│  ├─ agent_id
│  ├─ ChatMessages
│  │  └─ MessageCitations
│  └─ ChatAttachments
└─ AuditLogs
```

## 26. 运行方式

### 26.1 启动服务

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

### 26.2 执行数据库迁移

```powershell
docker compose exec api alembic upgrade head
```

### 26.3 创建管理员

```powershell
docker compose exec api python -m app.cli create-admin --email admin@example.com --password "ChangeMe123!" --tenant-name "Demo Enterprise" --if-not-exists
```

### 26.4 访问系统

```text
API Docs: http://localhost:8000/docs
Admin: http://localhost:5173
User: http://localhost:5174
MinIO: http://localhost:9001
```

### 26.5 基础冒烟测试

```powershell
.\scripts\smoke-docker.ps1 -CreateAdmin
```

### 26.6 完整 RAG 测试

先在 `.env` 中配置：

```env
DASHSCOPE_API_KEY=your-api-key
```

然后运行：

```powershell
.\scripts\smoke-docker.ps1 -CreateAdmin -RunModelChecks
```

## 27. 项目总结

本项目已经具备一个企业级 AI Agent/RAG 平台的基础能力：

- 多租户基础。
- JWT 登录认证。
- RBAC 权限控制。
- 管理端知识库维护。
- 文档上传和版本管理。
- MinIO 对象存储。
- 文档解析、切片、向量化。
- PostgreSQL + pgvector 向量检索。
- 阿里百炼 Embedding、Chat、Vision 模型调用。
- 用户端文本问答。
- 用户端图片和文件附件问答。
- Agent 配置和发布。
- 租户级配置。
- 审计日志。
- Redis 限流。
- 安全响应头。
- 上传安全扫描。
- Celery 异步任务。
- Docker Compose 本地部署。
- 冒烟测试脚本。

整体上，它可以作为后续企业知识助手、内部智能客服、制度问答、产品知识库问答、售前知识支持、运维知识助手等场景的基础工程。
