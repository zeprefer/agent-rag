import unittest
from types import SimpleNamespace

from app.services.rag_prompts import build_rag_messages
from app.services.retrieval import RetrievedChunk


class RagPromptTests(unittest.TestCase):
    def test_prompt_builder_is_pure_and_respects_context_budget(self):
        chunks = [
            RetrievedChunk(
                chunk=SimpleNamespace(
                    token_count=4,
                    page_number=index,
                    heading_path=f"section-{index}",
                    content=f"content-{index}",
                ),
                document=SimpleNamespace(title=f"document-{index}"),
                score=0.9,
            )
            for index in (1, 2)
        ]

        messages = build_rag_messages(
            question="question",
            retrieved_chunks=chunks,
            max_context_tokens=4,
        )

        self.assertEqual([message["role"] for message in messages], ["system", "user"])
        self.assertIn("content-1", messages[1]["content"])
        self.assertNotIn("content-2", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
