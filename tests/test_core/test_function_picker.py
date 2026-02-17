"""Tests for function picker."""
from __future__ import annotations

from pathlib import Path

from re_agent.backend.stub import StubBackend
from re_agent.core.function_picker import pick_next
from re_agent.core.models import FunctionEntry
from re_agent.core.session import Session


def test_pick_next_returns_highest_caller(tmp_path: Path) -> None:
    session = Session(tmp_path / "progress.json")
    backend = StubBackend(remaining_functions=[
        FunctionEntry(address="0x100", name="Foo", class_name="CTest", caller_count=5),
        FunctionEntry(address="0x200", name="Bar", class_name="CTest", caller_count=10),
    ])
    result = pick_next("CTest", backend, session)
    assert result is not None
    assert result.function_name == "Bar"
    assert result.caller_count == 10


def test_pick_next_skips_completed(tmp_path: Path) -> None:
    from re_agent.core.models import FunctionTarget, ReversalResult

    session = Session(tmp_path / "progress.json")
    # Record one as completed
    session.record_result(ReversalResult(
        target=FunctionTarget(address="0x200", class_name="CTest", function_name="Bar"),
        code="", checker_verdict=None, parity_status=None,
        parity_findings=[], rounds_used=1, success=True,
    ))

    backend = StubBackend(remaining_functions=[
        FunctionEntry(address="0x100", name="Foo", class_name="CTest", caller_count=5),
        FunctionEntry(address="0x200", name="Bar", class_name="CTest", caller_count=10),
    ])
    result = pick_next("CTest", backend, session)
    assert result is not None
    assert result.function_name == "Foo"


def test_pick_next_returns_none_when_empty(tmp_path: Path) -> None:
    session = Session(tmp_path / "progress.json")
    backend = StubBackend(remaining_functions=[])
    result = pick_next("CTest", backend, session)
    assert result is None
