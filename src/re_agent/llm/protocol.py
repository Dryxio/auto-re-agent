"""LLM provider protocol and message types."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass
class Message:
    """A single message in an LLM conversation.

    Attributes:
        role: One of ``"system"``, ``"user"``, or ``"assistant"``.
        content: The text content of the message.
    """

    role: str  # "system" | "user" | "assistant"
    content: str


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol that all LLM provider implementations must satisfy."""

    def send(self, messages: list[Message], **kwargs: Any) -> str:
        """Send a list of messages to the LLM and return the response text.

        Args:
            messages: Ordered conversation messages.  If the first message has
                ``role="system"`` it is treated as the system prompt.
            **kwargs: Provider-specific overrides (e.g. ``temperature``).

        Returns:
            The assistant's response text.
        """
        ...

    @property
    def supports_conversations(self) -> bool:
        """Whether this provider supports multi-turn conversation state."""
        ...

    def new_conversation(self, system: str) -> str:
        """Start a new conversation with the given system prompt.

        Args:
            system: The system-level instruction for the conversation.

        Returns:
            A conversation ID that can be passed to :meth:`resume`.
        """
        ...

    def resume(self, conversation_id: str, message: str) -> str:
        """Resume an existing conversation with a new user message.

        Args:
            conversation_id: ID returned by :meth:`new_conversation`.
            message: The new user message.

        Returns:
            The assistant's response text.
        """
        ...
