# 模块化架构与扩展约束

## 1. 目标

当前代码采用“应用端口 + 基础设施适配器 + 组合根”的依赖方向，核心目标是：

- 业务用例只依赖稳定协议，不依赖百炼、S3、Celery 等具体 SDK；
- 会话、检索、Prompt、回答编排、索引命令和索引查询保持单一职责；
- 新增模型厂商、对象存储或任务队列时，只增加适配器并修改组合根；
- HTTP API、Celery Worker 和既有调用方共享同一套应用服务。

## 2. 依赖方向

```text
API / Worker
    |
    v
应用服务（app/services） ---> 端口（app/ports）
                                   ^
                                   |
组合根（app/bootstrap.py） ---> 基础设施适配器（app/infrastructure）
```

约束如下：

1. `app/services` 不得直接导入 `app/infrastructure`；
2. `app/api` 不得直接导入 Celery Task 或厂商适配器；
3. 只有 `app/bootstrap.py` 负责选择生产环境的具体实现；
4. `rag.py`、`indexing.py`、`ai_providers.py`、`object_storage.py` 是迁移期兼容门面，新代码不应继续依赖它们；
5. 架构边界由 `test_architecture_boundaries.py` 自动守护。

## 3. 后端职责划分

- `agent_runtime.py`：解析 Agent 策略和可访问知识库；
- `chat_sessions.py`：会话与消息生命周期；
- `retrieval.py`：向量检索；
- `rag_prompts.py`：纯 Prompt 构造；
- `chat_answers.py`：问答用例编排；
- `indexing_commands.py`：索引状态机和写操作；
- `indexing_queries.py`：索引任务及分块读模型；
- `app/ports`：AI、存储和后台任务的稳定接口；
- `app/infrastructure`：百炼、S3 和 Celery 实现；
- `app/bootstrap.py`：生产实现装配及测试替换入口。

## 4. 扩展方式

新增 AI 厂商时：

1. 实现 `ChatProvider`、`EmbeddingProvider` 或 `VisionProvider`；
2. 将实现放入 `app/infrastructure/ai`；
3. 在 `app/bootstrap.py` 中切换工厂；
4. 不修改检索、问答和索引业务服务。

新增存储或队列的步骤相同：实现对应端口，增加适配器，在组合根切换实现。

## 5. 前端边界

管理端与用户端均改为浏览器原生 ES Modules：

- `api-client.js`：统一 HTTP、认证头和错误对象；
- `ui-utils.js`：无业务状态的展示工具；
- `app.js`：页面用例、状态和渲染编排。

后续增加新页面时，应继续按“API 客户端—页面状态—视图组件”拆分，避免再次将网络协议细节写入页面用例。
