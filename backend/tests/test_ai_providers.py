import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.ai_providers import (
    BAILIAN_EMBEDDING_MAX_BATCH_SIZE,
    BailianEmbeddingProvider,
    EmbeddingProviderError,
)


class FakeEmbeddingsClient:
    def __init__(self, dimensions: int, *, truncate_last_batch: bool = False) -> None:
        self.dimensions = dimensions
        self.truncate_last_batch = truncate_last_batch
        self.calls: list[list[str]] = []

    def create(self, *, model: str, input: list[str], dimensions: int):
        self.calls.append(list(input))
        data = [
            SimpleNamespace(embedding=[float(len(self.calls))] * self.dimensions)
            for _ in input
        ]
        if self.truncate_last_batch and data:
            data.pop()
        return SimpleNamespace(data=data)


def make_provider(client: FakeEmbeddingsClient, dimensions: int = 4) -> BailianEmbeddingProvider:
    provider = object.__new__(BailianEmbeddingProvider)
    provider.client = SimpleNamespace(embeddings=client)
    provider.model = "text-embedding-v4"
    provider.dimensions = dimensions
    return provider


class BailianEmbeddingProviderTests(unittest.TestCase):
    def test_splits_large_input_into_batches_of_at_most_ten(self):
        client = FakeEmbeddingsClient(dimensions=4)
        provider = make_provider(client)
        texts = [f"chunk-{index}" for index in range(23)]

        embeddings = provider.embed_texts(texts)

        self.assertEqual([len(call) for call in client.calls], [10, 10, 3])
        self.assertTrue(all(len(call) <= BAILIAN_EMBEDDING_MAX_BATCH_SIZE for call in client.calls))
        self.assertEqual(len(embeddings), len(texts))

    def test_returns_empty_without_calling_provider(self):
        client = FakeEmbeddingsClient(dimensions=4)
        provider = make_provider(client)

        self.assertEqual(provider.embed_texts([]), [])
        self.assertEqual(client.calls, [])

    def test_rejects_missing_embeddings_from_provider(self):
        client = FakeEmbeddingsClient(dimensions=4, truncate_last_batch=True)
        provider = make_provider(client)

        with self.assertRaisesRegex(EmbeddingProviderError, "Embedding count mismatch"):
            provider.embed_texts(["one", "two"])


class BailianToolCallingTests(unittest.TestCase):
    def test_normalizes_openai_tool_call_response(self):
        from app.services.ai_providers import BailianChatProvider

        tool_call = SimpleNamespace(
            id="call-42",
            function=SimpleNamespace(
                name="knowledge_search",
                arguments='{"query": "leave policy", "top_k": 3}',
            ),
        )
        response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None, tool_calls=[tool_call]),
                    finish_reason="tool_calls",
                )
            ],
            usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 12}),
        )
        create = Mock(return_value=response)
        provider = object.__new__(BailianChatProvider)
        provider.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        provider.config = SimpleNamespace(rag_temperature=0.2)
        provider.model = "qwen-plus"

        turn = provider.chat_with_tools(
            [{"role": "user", "content": "question"}],
            tools=[{"type": "function", "function": {"name": "knowledge_search"}}],
        )

        self.assertIsNone(turn.content)
        self.assertEqual(turn.tool_calls[0].id, "call-42")
        self.assertEqual(turn.tool_calls[0].name, "knowledge_search")
        self.assertEqual(turn.tool_calls[0].arguments["top_k"], 3)
        self.assertEqual(turn.metadata["finish_reason"], "tool_calls")


if __name__ == "__main__":
    unittest.main()
