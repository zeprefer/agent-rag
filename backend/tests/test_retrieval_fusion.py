import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from app.services.retrieval import RetrievedChunk, retrieve_hybrid_chunks


def result(chunk_id, score):
    return RetrievedChunk(
        chunk=SimpleNamespace(id=chunk_id),
        document=SimpleNamespace(id=uuid.uuid4(), title="doc"),
        score=score,
    )


class HybridRetrievalTests(unittest.TestCase):
    @patch("app.services.retrieval.retrieve_keyword_chunks")
    @patch("app.services.retrieval.retrieve_chunks")
    def test_fuses_and_deduplicates_vector_and_keyword_results(self, vector_search, keyword_search):
        shared = uuid.uuid4()
        vector_only = uuid.uuid4()
        keyword_only = uuid.uuid4()
        vector_search.return_value = [result(shared, 0.8), result(vector_only, 0.7)]
        keyword_search.return_value = [result(shared, 1.0), result(keyword_only, 1.0)]

        results = retrieve_hybrid_chunks(
            SimpleNamespace(),
            embedding_provider=SimpleNamespace(),
            tenant_id=uuid.uuid4(),
            query="policy code",
            knowledge_base_ids=[uuid.uuid4()],
            top_k=3,
        )

        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].chunk.id, shared)
        self.assertEqual(len({item.chunk.id for item in results}), 3)


if __name__ == "__main__":
    unittest.main()
