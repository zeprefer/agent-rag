"""阿里百炼 AI 适配器。

本文件是厂商 SDK 与应用端口之间的转换层，负责配置校验、请求调用、批处理
以及把 SDK 异常统一转换为业务可识别的 Provider 异常。
"""

import base64
import json
from typing import Any

from openai import OpenAI

from app.core.config import Settings, settings
from app.ports.ai import (
    AIProviderConfigError,
    AgentModelTurn,
    AgentToolCall,
    ChatProviderError,
    EmbeddingProviderError,
    Message,
    ToolDefinition,
)

BAILIAN_EMBEDDING_MAX_BATCH_SIZE = 10


class BailianEmbeddingProvider:
    """使用百炼 OpenAI-compatible Embedding API 实现向量化端口。"""
    def __init__(self, config: Settings | None = None) -> None:
        config = config or settings
        self.client = (
            OpenAI(api_key=config.dashscope_api_key, base_url=config.bailian_base_url)
            if config.dashscope_api_key
            else None
        )
        self.model = config.bailian_embedding_model
        self.dimensions = config.bailian_embedding_dimensions

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self.client is None:
            raise AIProviderConfigError("DASHSCOPE_API_KEY is required for embedding")
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), BAILIAN_EMBEDDING_MAX_BATCH_SIZE):
            batch = texts[start : start + BAILIAN_EMBEDDING_MAX_BATCH_SIZE]
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                    dimensions=self.dimensions,
                )
            except Exception as exc:
                raise EmbeddingProviderError(f"Embedding provider failed: {exc}") from exc

            batch_embeddings = [item.embedding for item in response.data]
            if len(batch_embeddings) != len(batch):
                raise EmbeddingProviderError(
                    "Embedding count mismatch: "
                    f"expected {len(batch)}, got {len(batch_embeddings)}"
                )
            for embedding in batch_embeddings:
                if len(embedding) != self.dimensions:
                    raise EmbeddingProviderError(
                        f"Embedding dimension mismatch: expected {self.dimensions}, got {len(embedding)}"
                    )
            embeddings.extend(batch_embeddings)
        return embeddings


class BailianChatProvider:
    """使用百炼 Chat Completions API 实现聊天端口。"""
    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings
        self.client = (
            OpenAI(
                api_key=self.config.dashscope_api_key,
                base_url=self.config.bailian_base_url,
            )
            if self.config.dashscope_api_key
            else None
        )
        self.model = self.config.bailian_chat_model

    def chat(
        self,
        messages: list[Message],
        *,
        temperature: float | None = None,
        model: str | None = None,
    ) -> tuple[str, dict]:
        if self.client is None:
            raise AIProviderConfigError("DASHSCOPE_API_KEY is required for chat")
        selected_model = model or self.model
        try:
            response = self.client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=self.config.rag_temperature if temperature is None else temperature,
            )
        except Exception as exc:
            raise ChatProviderError(f"Chat provider failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else None
        if not content:
            raise ChatProviderError("Chat provider returned empty content")
        usage = response.usage.model_dump() if response.usage is not None else {}
        return content, {"model": selected_model, "usage": usage}

    def chat_with_tools(
        self,
        messages: list[Message],
        *,
        tools: list[ToolDefinition],
        temperature: float | None = None,
        model: str | None = None,
    ) -> AgentModelTurn:
        """调用兼容 OpenAI Function Calling 的百炼接口并标准化返回结构。"""
        if self.client is None:
            raise AIProviderConfigError("DASHSCOPE_API_KEY is required for chat")
        selected_model = model or self.model
        request: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": self.config.rag_temperature if temperature is None else temperature,
        }
        if tools:
            request.update({"tools": tools, "tool_choice": "auto"})
        try:
            response = self.client.chat.completions.create(**request)
        except Exception as exc:
            raise ChatProviderError(f"Agent provider failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        message = choice.message if choice else None
        if message is None:
            raise ChatProviderError("Agent provider returned no message")

        calls: list[AgentToolCall] = []
        for call in message.tool_calls or []:
            raw_arguments = call.function.arguments or "{}"
            try:
                arguments = json.loads(raw_arguments)
                if not isinstance(arguments, dict):
                    raise ValueError("tool arguments must be an object")
            except (json.JSONDecodeError, ValueError):
                arguments = {"_invalid_arguments": raw_arguments}
            calls.append(
                AgentToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                    raw_arguments=raw_arguments,
                )
            )

        content = message.content.strip() if message.content else None
        if not content and not calls:
            raise ChatProviderError("Agent provider returned neither content nor tool calls")
        usage = response.usage.model_dump() if response.usage is not None else {}
        return AgentModelTurn(
            content=content,
            tool_calls=calls,
            metadata={
                "model": selected_model,
                "usage": usage,
                "finish_reason": choice.finish_reason if choice is not None else None,
            },
        )


class BailianVisionProvider:
    """使用百炼视觉模型将图片转换为可进入 RAG 上下文的文本。"""
    def __init__(self, config: Settings | None = None) -> None:
        self.config = config or settings
        self.client = (
            OpenAI(
                api_key=self.config.dashscope_api_key,
                base_url=self.config.bailian_base_url,
            )
            if self.config.dashscope_api_key
            else None
        )
        self.model = self.config.bailian_vision_model

    def describe_image(
        self,
        *,
        data: bytes,
        content_type: str | None,
        user_hint: str | None = None,
    ) -> tuple[str, dict]:
        if self.client is None:
            raise AIProviderConfigError("DASHSCOPE_API_KEY is required for vision")
        media_type = content_type or "image/png"
        encoded = base64.b64encode(data).decode("ascii")
        prompt = (
            "Extract useful information from this image for enterprise knowledge QA. "
            "Include visible text, tables, numbers, entities, and a concise visual description. "
            "If the image is not readable, say so clearly."
        )
        if user_hint:
            prompt += f"\nUser question or hint: {user_hint}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{encoded}"},
                            },
                        ],
                    }
                ],
                temperature=0,
            )
        except Exception as exc:
            raise ChatProviderError(f"Vision provider failed: {exc}") from exc

        choice = response.choices[0] if response.choices else None
        content = choice.message.content if choice and choice.message else None
        if not content:
            raise ChatProviderError("Vision provider returned empty content")
        usage = response.usage.model_dump() if response.usage is not None else {}
        return content, {"model": self.model, "usage": usage}
