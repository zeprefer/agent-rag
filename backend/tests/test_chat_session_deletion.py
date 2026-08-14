import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.rag import ChatSessionNotFoundError, delete_chat_session


class ChatSessionDeletionTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()
        self.user = SimpleNamespace(id=uuid.uuid4(), tenant_id=uuid.uuid4())
        self.session_id = uuid.uuid4()

    @patch("app.services.rag.delete_chat_attachments")
    @patch("app.services.rag.get_chat_session")
    def test_deletes_attachments_then_session(self, get_session, delete_attachments):
        session = SimpleNamespace(id=self.session_id)
        get_session.return_value = session

        delete_chat_session(self.db, current_user=self.user, session_id=self.session_id)

        delete_attachments.assert_called_once_with(
            self.db,
            current_user=self.user,
            session_id=self.session_id,
        )
        self.db.delete.assert_called_once_with(session)
        self.db.commit.assert_called_once_with()

    @patch("app.services.rag.delete_chat_attachments")
    @patch("app.services.rag.get_chat_session")
    def test_rejects_session_not_owned_by_user(self, get_session, delete_attachments):
        get_session.return_value = None

        with self.assertRaisesRegex(ChatSessionNotFoundError, "Chat session not found"):
            delete_chat_session(self.db, current_user=self.user, session_id=self.session_id)

        delete_attachments.assert_not_called()
        self.db.delete.assert_not_called()
        self.db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
