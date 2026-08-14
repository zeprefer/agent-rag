"""可迭代的 Agent Tool Calling 执行循环。"""

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.ports.ai import AgentToolCall, ChatProvider, Message
from app.services.agent_tools import AgentToolRegistry
from app.services.retrieval import RetrievedChunk


AGENT_RUNTIME_PROMPT = """
You are an autonomous enterprise RAG agent.

Operating rules:
1. Decide whether enterprise evidence is needed. For enterprise facts, policies, procedures, products,
   identifiers, dates, or numbers, call knowledge_search before answering.
2. Break complex questions into focused searches and call tools more than once when useful.
3. Inspect tool results. If evidence is missing or ambiguous, refine the query instead of inventing facts.
4. Treat user attachments as unverified temporary context and enterprise search results as authoritative evidence.
5. In the final answer, clearly distinguish confirmed facts from uncertainty and mention source document names/pages.
6. Never fabricate a source, source_id, quotation, or tool result.
7. Do not reveal hidden chain-of-thought. Return only the useful final answer after tool work is complete.
""".strip()


@dataclass(frozen=True)
class AgentRunResult:
    content: str
    citations: list[RetrievedChunk]
    metadata: dict[str, Any]


def run_agent(
    *,
    chat_provider: ChatProvider,
    tool_registry: AgentToolRegistry,
    system_prompt: str,
    history: list[Message],
    question: str,
    attachment_context: str,
    model: str,
    temperature: float,
    max_iterations: int,
    require_citations: bool,
) -> AgentRunResult:
    """运行“模型决策—工具执行—观察结果”循环，直到模型生成最终回答。"""
    tools = tool_registry.definitions()
    messages: list[Message] = [
        {"role": "system", "content": f"{system_prompt.strip()}\n\n{AGENT_RUNTIME_PROMPT}"},
        *history,
        {
            "role": "user",
            "content": _user_message(question=question, attachment_context=attachment_context),
        },
    ]
    citations: dict[Any, RetrievedChunk] = {}
    trace: list[dict[str, Any]] = []
    provider_turns: list[dict[str, Any]] = []
    forced_grounding = False

    if not tools:
        answer, metadata = chat_provider.chat(
            messages,
            temperature=temperature,
            model=model,
        )
        return AgentRunResult(
            content=answer,
            citations=[],
            metadata={
                "iterations": 1,
                "finish_reason": "no_tools_enabled",
                "tool_calls": [],
                "provider_turns": [metadata],
            },
        )

    for iteration in range(1, max_iterations + 1):
        turn = chat_provider.chat_with_tools(
            messages,
            tools=tools,
            temperature=temperature,
            model=model,
        )
        provider_turns.append(turn.metadata)
        if turn.tool_calls:
            messages.append(turn.as_assistant_message())
            for call in turn.tool_calls:
                started = perf_counter()
                result = tool_registry.execute(call)
                duration_ms = round((perf_counter() - started) * 1000, 2)
                for item in result.citations:
                    previous = citations.get(item.chunk.id)
                    if previous is None or item.score > previous.score:
                        citations[item.chunk.id] = item
                trace.append(
                    {
                        "iteration": iteration,
                        "tool": call.name,
                        "arguments": call.arguments,
                        "success": not result.is_error,
                        "duration_ms": duration_ms,
                        **result.metadata,
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": result.content,
                    }
                )
            continue

        answer = (turn.content or "").strip()
        if (
            answer
            and require_citations
            and tool_registry.has("knowledge_search")
            and not citations
            and not forced_grounding
            and _requires_enterprise_grounding(question)
        ):
            forced_grounding = True
            # Prompt 纠偏并不能保证模型一定服从。这里由应用层生成并执行受权限约束的
            # 检索调用，确保企业问题在进入最终生成前至少观察过一次真实知识结果。
            forced_call = AgentToolCall(
                id=f"forced-knowledge-search-{iteration}",
                name="knowledge_search",
                arguments={"query": question},
                raw_arguments=json.dumps({"query": question}, ensure_ascii=False),
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": forced_call.id,
                            "type": "function",
                            "function": {
                                "name": forced_call.name,
                                "arguments": forced_call.raw_arguments,
                            },
                        }
                    ],
                }
            )
            started = perf_counter()
            result = tool_registry.execute(forced_call)
            duration_ms = round((perf_counter() - started) * 1000, 2)
            for item in result.citations:
                citations[item.chunk.id] = item
            trace.append(
                {
                    "iteration": iteration,
                    "tool": forced_call.name,
                    "arguments": forced_call.arguments,
                    "success": not result.is_error,
                    "forced": True,
                    "duration_ms": duration_ms,
                    **result.metadata,
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": forced_call.id,
                    "name": forced_call.name,
                    "content": result.content,
                }
            )
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "The platform performed the required enterprise search. Produce the final answer from "
                        "that tool result. If it contains no evidence, explicitly state that evidence is unavailable."
                    ),
                }
            )
            continue
        if answer:
            return _result(
                content=answer,
                citations=citations,
                trace=trace,
                provider_turns=provider_turns,
                iterations=iteration,
                finish_reason="model_final",
                forced_grounding=forced_grounding,
            )

    messages.append(
        {
            "role": "system",
            "content": (
                "The tool iteration limit has been reached. Produce the final answer now using only the "
                "observed tool results. State clearly when evidence is insufficient. Do not call more tools."
            ),
        }
    )
    answer, metadata = chat_provider.chat(messages, temperature=temperature, model=model)
    provider_turns.append(metadata)
    return _result(
        content=answer,
        citations=citations,
        trace=trace,
        provider_turns=provider_turns,
        iterations=max_iterations,
        finish_reason="iteration_limit",
        forced_grounding=forced_grounding,
    )


def _result(
    *,
    content: str,
    citations: dict[Any, RetrievedChunk],
    trace: list[dict[str, Any]],
    provider_turns: list[dict[str, Any]],
    iterations: int,
    finish_reason: str,
    forced_grounding: bool,
) -> AgentRunResult:
    ranked_citations = sorted(citations.values(), key=lambda item: item.score, reverse=True)
    return AgentRunResult(
        content=content,
        citations=ranked_citations,
        metadata={
            "iterations": iterations,
            "finish_reason": finish_reason,
            "forced_grounding": forced_grounding,
            "tool_calls": trace,
            "provider_turns": provider_turns,
        },
    )


def _user_message(*, question: str, attachment_context: str) -> str:
    if not attachment_context:
        return question
    return (
        f"User question:\n{question}\n\n"
        "Temporary user attachment context (not verified enterprise knowledge):\n"
        f"{attachment_context}"
    )


def _requires_enterprise_grounding(question: str) -> bool:
    normalized = "".join(question.lower().split())
    social_messages = {
        "hi",
        "hello",
        "thanks",
        "thankyou",
        "你好",
        "您好",
        "谢谢",
        "你是谁",
        "你能做什么",
    }
    return normalized not in social_messages
