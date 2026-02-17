"""Tests for the agent fix loop."""
from __future__ import annotations

from re_agent.agents.loop import run_fix_loop
from re_agent.backend.stub import StubBackend
from re_agent.core.models import FunctionTarget, Verdict
from re_agent.llm.protocol import Message


class MockLLM:
    """Mock LLM that returns canned responses in order."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = responses
        self._idx = 0

    def send(self, messages: list[Message], **kwargs: object) -> str:
        idx = min(self._idx, len(self._responses) - 1)
        self._idx += 1
        return self._responses[idx]

    @property
    def supports_conversations(self) -> bool:
        return False

    def new_conversation(self, system: str) -> str:
        return ""

    def resume(self, conversation_id: str, message: str) -> str:
        return ""


def test_loop_pass_first_round(tmp_path: object) -> None:
    target = FunctionTarget(address="0x6F86A0", class_name="CTrain", function_name="ProcessControl")
    backend = StubBackend()

    reverser_resp = (
        "```cpp\nvoid CTrain::ProcessControl() { }\n```\n"
        "REVERSED_FUNCTION: CTrain::ProcessControl (0x6F86A0)"
    )
    checker_resp = "VERDICT: PASS\nSUMMARY: All good\nISSUES:\n- none\nFIX_INSTRUCTIONS:\n- none"

    rev_llm = MockLLM([reverser_resp])
    chk_llm = MockLLM([checker_resp])
    result = run_fix_loop(target, backend, rev_llm, chk_llm, max_rounds=3)

    assert result.success
    assert result.rounds_used == 1
    assert result.checker_verdict is not None
    assert result.checker_verdict.verdict == Verdict.PASS


def test_loop_fail_then_pass(tmp_path: object) -> None:
    target = FunctionTarget(address="0x6F86A0", class_name="CTrain", function_name="ProcessControl")
    backend = StubBackend()

    reverser_responses = [
        "```cpp\nvoid CTrain::ProcessControl() { /* wrong */ }\n```\n"
        "REVERSED_FUNCTION: CTrain::ProcessControl (0x6F86A0)",
        "```cpp\nvoid CTrain::ProcessControl() { /* fixed */ }\n```\n"
        "REVERSED_FUNCTION: CTrain::ProcessControl (0x6F86A0)",
    ]
    checker_responses = [
        "VERDICT: FAIL\nSUMMARY: Missing branch\nISSUES:\n- missing if check\nFIX_INSTRUCTIONS:\n- add the if check",
        "VERDICT: PASS\nSUMMARY: All good\nISSUES:\n- none\nFIX_INSTRUCTIONS:\n- none",
    ]

    rev_llm = MockLLM(reverser_responses)
    chk_llm = MockLLM(checker_responses)
    result = run_fix_loop(target, backend, rev_llm, chk_llm, max_rounds=3)

    assert result.success
    assert result.rounds_used == 2


def test_loop_exhausts_rounds() -> None:
    target = FunctionTarget(address="0x6F86A0", class_name="CTrain", function_name="ProcessControl")
    backend = StubBackend()

    reverser_resp = "```cpp\nvoid CTrain::ProcessControl() { }\n```"
    checker_resp = "VERDICT: FAIL\nSUMMARY: Still wrong\nISSUES:\n- issue\nFIX_INSTRUCTIONS:\n- fix it"

    rev_llm = MockLLM([reverser_resp] * 5)
    chk_llm = MockLLM([checker_resp] * 5)
    result = run_fix_loop(target, backend, rev_llm, chk_llm, max_rounds=2)

    assert not result.success
    assert result.rounds_used == 2
