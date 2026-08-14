import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.conversation_memory import load_conversation_memory


class ConversationMemoryTests(unittest.TestCase):
    def test_returns_chronological_messages_within_token_budget(self):
        newest_first = [
            SimpleNamespace(role="assistant", content="new answer", token_count=4),
            SimpleNamespace(role="user", content="new question", token_count=3),
            SimpleNamespace(role="assistant", content="old answer", token_count=5),
        ]
        db = Mock()
        db.execute.return_value.scalars.return_value.all.return_value = newest_first

        messages = load_conversation_memory(
            db,
            tenant_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            message_limit=10,
            token_limit=7,
        )

        self.assertEqual(
            messages,
            [
                {"role": "user", "content": "new question"},
                {"role": "assistant", "content": "new answer"},
            ],
        )

    def test_disabled_memory_does_not_query_database(self):
        db = Mock()

        messages = load_conversation_memory(
            db,
            tenant_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            message_limit=0,
            token_limit=100,
        )

        self.assertEqual(messages, [])
        db.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
