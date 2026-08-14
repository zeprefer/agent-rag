"""Backward-compatible imports for AI adapters.

New application code should depend on ``app.ports.ai`` and receive providers
through ``app.bootstrap``.  This module remains to avoid breaking integrations
that imported the original provider classes.
"""

from app.infrastructure.ai.bailian import (
    BAILIAN_EMBEDDING_MAX_BATCH_SIZE,
    BailianChatProvider,
    BailianEmbeddingProvider,
    BailianVisionProvider,
)
from app.ports.ai import (
    AIProviderConfigError,
    AgentModelTurn,
    AgentToolCall,
    ChatProviderError,
    EmbeddingProviderError,
)

__all__ = [
    "AIProviderConfigError",
    "AgentModelTurn",
    "AgentToolCall",
    "BAILIAN_EMBEDDING_MAX_BATCH_SIZE",
    "BailianChatProvider",
    "BailianEmbeddingProvider",
    "BailianVisionProvider",
    "ChatProviderError",
    "EmbeddingProviderError",
]
