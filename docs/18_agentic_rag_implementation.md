# Agentic RAG 实现说明

## 1. 当前能力

系统不再采用固定的“检索一次后直接生成”流程，而是运行可迭代的 Agent：

```text
用户问题 + 会话记忆 + 附件上下文
              |
              v
        Agent 模型自主判断
         /             \
  调用知识检索工具       直接回答非企业问题
         |
   混合检索并观察结果
         |
  继续改写查询或补充检索
         |
     生成有证据的最终回答
```

一次企业问答可以调用 `knowledge_search` 多次。模型负责拆解问题、生成独立检索词、
观察返回证据，并决定继续检索还是结束。系统不保存或展示模型隐藏思维过程，只保存
可审计的工具调用轨迹。

## 2. 核心组件

| 文件 | 职责 |
|---|---|
| `app/ports/ai.py` | 厂商无关的聊天、Tool Calling、Embedding 和视觉协议 |
| `app/infrastructure/ai/bailian.py` | 百炼 OpenAI-compatible Tool Calling 适配器 |
| `app/services/agent_runner.py` | 模型决策、工具执行、观察和迭代终止循环 |
| `app/services/agent_tools.py` | 工具注册表与企业知识检索工具 |
| `app/services/conversation_memory.py` | 从数据库读取并裁剪会话短期记忆 |
| `app/services/retrieval.py` | 向量与关键词混合召回、融合及去重 |
| `app/services/chat_answers.py` | 组装 Agent 运行环境并持久化回答、轨迹和引用 |

## 3. Agent 配置

每个 Agent 除原有提示词、模型和 RAG 参数外，还支持：

- `max_iterations`：一次回答允许的最大模型推理轮数，范围 1–10；
- `memory_window`：带入本轮的最近会话消息数，范围 0–50；
- `enabled_tools`：允许 Agent 使用的工具，目前为 `knowledge_search`；
- `require_citations`：企业事实问题未检索证据时，是否强制模型先调用检索工具。

数据库升级：

```powershell
docker compose exec api alembic upgrade head
```

迁移文件为 `0008_agentic_rag_runtime.py`。

## 4. 企业知识检索工具

`knowledge_search` 仅能访问经过以下条件过滤的数据：

- 当前用户所属 `tenant_id`；
- 当前会话或 Agent 允许的知识库；
- 未归档知识库；
- 已成功索引的文档。

检索同时执行：

1. pgvector 语义向量召回；
2. 关键词、编号和中文短词召回；
3. 加权融合；
4. 按 `chunk_id` 去重；
5. 返回受 `top_k` 限制的证据。

模型不能指定租户或绕过知识库范围，权限边界由工具构造时固定。

## 5. 会话记忆

每次回答前从 `chat_messages` 读取最近的用户及助手消息，并同时受以下限制：

- Agent 的 `memory_window`；
- 最大上下文 Token 的三分之一预算。

工具调用中间消息不会写入聊天正文，只将可审计摘要保存到最终助手消息的
`extra_metadata.agent_run`。

## 6. 执行轨迹与引用

最终助手消息包含：

```json
{
  "agent_run": {
    "iterations": 3,
    "finish_reason": "model_final",
    "forced_grounding": false,
    "tool_calls": [
      {
        "iteration": 1,
        "tool": "knowledge_search",
        "query": "差旅住宿报销标准",
        "hit_count": 5,
        "success": true,
        "duration_ms": 42.7
      }
    ]
  },
  "memory": {"message_count": 8},
  "retrieval": {
    "mode": "agentic_hybrid",
    "queries": ["差旅住宿报销标准"],
    "hit_count": 5
  }
}
```

工具实际返回的知识片段会继续保存为 `message_citations`，因此前端引用不是模型
自行生成的文本，而是数据库中真实命中的文档和 chunk。

## 7. 安全与终止机制

- 工具不能接收或修改租户 ID；
- 非法 JSON 参数会作为工具错误返回模型，不会直接执行；
- 未注册工具会被拒绝；
- 工具异常被记录到轨迹，并允许模型说明服务暂不可用；
- 达到最大迭代次数后禁止继续调用工具，强制根据已有观察生成最终回答；
- 企业问题在启用 `require_citations` 后，如果模型试图无证据直接回答，应用层会
  生成并执行一次受权限约束的 `knowledge_search`，不能只靠模型遵循 Prompt。

## 8. 新增工具

新增工具只需：

1. 实现 `AgentTool` 的 `definition()` 与 `execute()`；
2. 在问答用例构造工具时按 `enabled_tools` 注册；
3. 将新的工具名加入 Agent Schema 允许列表；
4. 为权限边界、参数校验和执行结果增加单元测试。

Agent Runner 不需要随工具数量增加而修改。
