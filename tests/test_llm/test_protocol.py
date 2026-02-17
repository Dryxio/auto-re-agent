"""Tests for LLM protocol and provider basics."""
from __future__ import annotations

from re_agent.llm.protocol import LLMProvider, Message


def test_message_creation() -> None:
    m = Message(role="user", content="Hello")
    assert m.role == "user"
    assert m.content == "Hello"


class MockProvider:
    """Mock LLM provider for testing."""

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = responses or ["Mock response"]
        self._call_count = 0

    def send(self, messages: list[Message], **kwargs: object) -> str:
        idx = min(self._call_count, len(self._responses) - 1)
        self._call_count += 1
        return self._responses[idx]

    @property
    def supports_conversations(self) -> bool:
        return True

    def new_conversation(self, system: str) -> str:
        return "mock-conv-1"

    def resume(self, conversation_id: str, message: str) -> str:
        return self.send([Message(role="user", content=message)])


def test_mock_provider_implements_protocol() -> None:
    provider = MockProvider()
    assert isinstance(provider, LLMProvider)
    assert provider.supports_conversations


def test_mock_provider_send() -> None:
    provider = MockProvider(["Hello!", "World!"])
    r1 = provider.send([Message(role="user", content="Hi")])
    assert r1 == "Hello!"
    r2 = provider.send([Message(role="user", content="Again")])
    assert r2 == "World!"
