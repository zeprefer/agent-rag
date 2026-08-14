"""业务层所需的 AI 能力端口。

这里仅描述聊天、向量化和视觉识别需要什么能力，不引用任何厂商 SDK。
基础设施层只要实现这些 Protocol，就能在不修改检索、索引和问答用例的情况下
替换百炼或接入其他模型服务。
"""

from dataclasses import dataclass
from typing import Any, Protocol

Message = dict[str, Any]
ToolDefinition = dict[str, Any]


class AIProviderConfigError(RuntimeError):
    pass


class EmbeddingProviderError(RuntimeError):
    pass


class ChatProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentToolCall:
    """厂商无关的工具调用请求。"""

    id: str
    name: str
    arguments: dict[str, Any]
    raw_arguments: str


@dataclass(frozen=True)
class AgentModelTurn:
    """一次 Agent 模型推理结果，可包含最终文本或若干工具调用。"""

    content: str | None
    tool_calls: list[AgentToolCall]
    metadata: dict[str, Any]

    def as_assistant_message(self) -> Message:
        message: Message = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.raw_arguments},
                }
                for call in self.tool_calls
            ]
        return message


class EmbeddingProvider(Protocol):
    """文本向量化端口；模型名称和维度用于索引元数据记录。"""
    model: str
    dimensions: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class ChatProvider(Protocol):
    """大语言模型聊天端口。"""
    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        model: str | None = None,
    ) -> tuple[str, dict]: ...

    def chat_with_tools(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition],
        temperature: float | None = None,
        model: str | None = None,
    ) -> AgentModelTurn: ...


class VisionProvider(Protocol):
    """图片内容提取端口。"""
    def describe_image(
        self,
        *,
        data: bytes,
        content_type: str | None,
        user_hint: str | None = None,
    ) -> tuple[str, dict]: ...
