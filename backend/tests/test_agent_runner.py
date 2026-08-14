import unittest
import uuid
from types import SimpleNamespace

from app.ports.ai import AgentModelTurn, AgentToolCall
from app.services.agent_runner import run_agent
from app.services.agent_tools import AgentToolRegistry, ToolExecutionResult
from app.services.retrieval import RetrievedChunk


class FakeChatProvider:
    def __init__(self, turns, fallback="fallback answer"):
        self.turns = list(turns)
        self.fallback = fallback
        self.tool_requests = []
        self.chat_requests = []

    def chat_with_tools(self, messages, *, tools, temperature=None, model=None):
        self.tool_requests.append({"messages": list(messages), "tools": tools})
        return self.turns.pop(0)

    def chat(self, messages, *, temperature=None, model=None):
        self.chat_requests.append(list(messages))
        return self.fallback, {"model": model, "usage": {}}


class FakeSearchTool:
    name = "knowledge_search"

    def __init__(self, citation):
        self.citation = citation
        self.calls = []

    def definition(self):
        return {"type": "function", "function": {"name": self.name, "parameters": {"type": "object"}}}

    def execute(self, arguments):
        self.calls.append(arguments)
        return ToolExecutionResult(
            content='{"results": [{"content": "policy evidence"}]}',
            citations=[self.citation],
            metadata={"query": arguments["query"], "hit_count": 1},
        )


def make_turn(*, content=None, calls=None):
    return AgentModelTurn(
        content=content,
        tool_calls=calls or [],
        metadata={"model": "test", "usage": {}},
    )


def make_call(query="leave policy"):
    return AgentToolCall(
        id="call-1",
        name="knowledge_search",
        arguments={"query": query},
        raw_arguments=f'{{"query": "{query}"}}',
    )


class AgentRunnerTests(unittest.TestCase):
    def setUp(self):
        self.citation = RetrievedChunk(
            chunk=SimpleNamespace(id=uuid.uuid4()),
            document=SimpleNamespace(id=uuid.uuid4(), title="HR Policy"),
            score=0.92,
        )

    def test_executes_tool_then_returns_grounded_answer(self):
        provider = FakeChatProvider(
            [make_turn(calls=[make_call()]), make_turn(content="Grounded final answer")]
        )
        tool = FakeSearchTool(self.citation)

        result = run_agent(
            chat_provider=provider,
            tool_registry=AgentToolRegistry([tool]),
            system_prompt="Be helpful",
            history=[{"role": "user", "content": "previous question"}],
            question="What is the leave policy?",
            attachment_context="",
            model="test-model",
            temperature=0.1,
            max_iterations=4,
            require_citations=True,
        )

        self.assertEqual(result.content, "Grounded final answer")
        self.assertEqual(result.citations, [self.citation])
        self.assertEqual(result.metadata["iterations"], 2)
        self.assertEqual(result.metadata["tool_calls"][0]["query"], "leave policy")
        self.assertEqual(tool.calls, [{"query": "leave policy"}])
        second_turn_messages = provider.tool_requests[1]["messages"]
        self.assertTrue(any(message["role"] == "tool" for message in second_turn_messages))

    def test_forces_search_when_enterprise_answer_has_no_evidence(self):
        provider = FakeChatProvider(
            [
                make_turn(content="Ungrounded answer"),
                make_turn(content="Evidence-based answer"),
            ]
        )

        result = run_agent(
            chat_provider=provider,
            tool_registry=AgentToolRegistry([FakeSearchTool(self.citation)]),
            system_prompt="Be helpful",
            history=[],
            question="What is the company expense limit?",
            attachment_context="",
            model="test-model",
            temperature=0.1,
            max_iterations=4,
            require_citations=True,
        )

        self.assertEqual(result.content, "Evidence-based answer")
        self.assertTrue(result.metadata["forced_grounding"])
        self.assertEqual(result.metadata["iterations"], 2)
        self.assertTrue(result.metadata["tool_calls"][0]["forced"])
        self.assertEqual(result.metadata["tool_calls"][0]["query"], "What is the company expense limit?")

    def test_iteration_limit_uses_final_non_tool_synthesis(self):
        provider = FakeChatProvider([make_turn(calls=[make_call()])], fallback="Limit synthesis")

        result = run_agent(
            chat_provider=provider,
            tool_registry=AgentToolRegistry([FakeSearchTool(self.citation)]),
            system_prompt="Be helpful",
            history=[],
            question="Summarize the policy",
            attachment_context="",
            model="test-model",
            temperature=0.1,
            max_iterations=1,
            require_citations=True,
        )

        self.assertEqual(result.content, "Limit synthesis")
        self.assertEqual(result.metadata["finish_reason"], "iteration_limit")
        self.assertEqual(len(provider.chat_requests), 1)


if __name__ == "__main__":
    unittest.main()
