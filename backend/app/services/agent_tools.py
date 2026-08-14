"""Agent 工具定义、注册与知识检索工具实现。"""

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core.config import settings
from app.ports.ai import AgentToolCall, EmbeddingProvider, ToolDefinition
from app.services.retrieval import RetrievedChunk, retrieve_hybrid_chunks


@dataclass
class ToolExecutionResult:
    content: str
    citations: list[RetrievedChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_error: bool = False


class AgentTool(Protocol):
    name: str

    def definition(self) -> ToolDefinition: ...

    def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult: ...


class KnowledgeSearchTool:
    """在当前租户及 Agent 允许的知识库范围内执行混合检索。"""

    name = "knowledge_search"

    def __init__(
        self,
        *,
        db: Session,
        embedding_provider: EmbeddingProvider,
        tenant_id: uuid.UUID,
        knowledge_base_ids: list[uuid.UUID],
        default_top_k: int,
    ) -> None:
        self.db = db
        self.embedding_provider = embedding_provider
        self.tenant_id = tenant_id
        self.knowledge_base_ids = knowledge_base_ids
        self.default_top_k = default_top_k

    def definition(self) -> ToolDefinition:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": (
                    "Search authorized enterprise knowledge using hybrid semantic and keyword retrieval. "
                    "Use this tool for company facts, policies, procedures, products, numbers, or any answer "
                    "that must be grounded in enterprise sources. You may call it multiple times with refined queries."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A focused standalone search query, rewritten from the user's question.",
                        },
                        "top_k": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 20,
                            "description": "Number of evidence chunks to retrieve.",
                        },
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, arguments: dict[str, Any]) -> ToolExecutionResult:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return ToolExecutionResult(
                content=json.dumps({"error": "query must be a non-empty string"}, ensure_ascii=False),
                is_error=True,
            )
        if not self.knowledge_base_ids:
            return ToolExecutionResult(
                content=json.dumps(
                    {"query": query.strip(), "results": [], "message": "No authorized knowledge bases."},
                    ensure_ascii=False,
                ),
                metadata={"query": query.strip(), "hit_count": 0},
            )
        requested_top_k = arguments.get("top_k", self.default_top_k)
        try:
            top_k = max(1, min(int(requested_top_k), min(self.default_top_k, 20)))
        except (TypeError, ValueError):
            top_k = self.default_top_k
        # 使用 SAVEPOINT 隔离工具查询失败，避免一次检索异常污染外层消息事务。
        with self.db.begin_nested():
            results = retrieve_hybrid_chunks(
                self.db,
                embedding_provider=self.embedding_provider,
                tenant_id=self.tenant_id,
                query=query.strip(),
                knowledge_base_ids=self.knowledge_base_ids,
                top_k=top_k,
            )
        payload = {
            "query": query.strip(),
            "results": [
                {
                    "source_id": str(item.chunk.id),
                    "document": item.document.title,
                    "page": item.chunk.page_number,
                    "section": item.chunk.heading_path,
                    "score": round(item.score, 6),
                    "content": item.chunk.content,
                }
                for item in results
            ],
        }
        content = json.dumps(payload, ensure_ascii=False)
        if len(content) > settings.agent_tool_result_max_chars:
            per_result_budget = max(
                240,
                settings.agent_tool_result_max_chars // max(1, len(payload["results"])) - 240,
            )
            for item in payload["results"]:
                item["content"] = item["content"][:per_result_budget]
            payload["truncated"] = True
            content = json.dumps(payload, ensure_ascii=False)
        return ToolExecutionResult(
            content=content,
            citations=results,
            metadata={"query": query.strip(), "hit_count": len(results)},
        )


class AgentToolRegistry:
    """按名称查找工具并把未知工具或执行异常转换为模型可理解的结果。"""

    def __init__(self, tools: list[AgentTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    def definitions(self) -> list[ToolDefinition]:
        return [tool.definition() for tool in self._tools.values()]

    def has(self, name: str) -> bool:
        return name in self._tools

    def execute(self, call: AgentToolCall) -> ToolExecutionResult:
        tool = self._tools.get(call.name)
        if tool is None:
            return ToolExecutionResult(
                content=json.dumps({"error": f"Unknown tool: {call.name}"}),
                is_error=True,
            )
        if "_invalid_arguments" in call.arguments:
            return ToolExecutionResult(
                content=json.dumps({"error": "Tool arguments are not valid JSON"}),
                is_error=True,
            )
        try:
            return tool.execute(call.arguments)
        except Exception as exc:
            return ToolExecutionResult(
                content=json.dumps(
                    {"error": "Tool execution failed", "error_type": type(exc).__name__},
                    ensure_ascii=False,
                ),
                metadata={"error_type": type(exc).__name__},
                is_error=True,
            )
