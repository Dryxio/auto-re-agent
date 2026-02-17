"""Tests for core data models."""
from __future__ import annotations

from re_agent.core.models import (
    CheckerVerdict,
    Finding,
    FunctionTarget,
    HookEntry,
    ParityStatus,
    ReversalResult,
    Verdict,
)


def test_function_target() -> None:
    t = FunctionTarget(address="0x6F86A0", class_name="CTrain", function_name="ProcessControl")
    assert t.address == "0x6F86A0"
    assert t.caller_count == 0


def test_verdict_enum() -> None:
    assert Verdict.PASS.value == "PASS"
    assert Verdict.FAIL.value == "FAIL"
    assert Verdict.UNKNOWN.value == "UNKNOWN"


def test_parity_status_enum() -> None:
    assert ParityStatus.GREEN.value == "green"
    assert ParityStatus.YELLOW.value == "yellow"
    assert ParityStatus.RED.value == "red"


def test_finding() -> None:
    f = Finding(level="red", reason="Missing source body")
    assert f.level == "red"


def test_checker_verdict() -> None:
    v = CheckerVerdict(
        verdict=Verdict.PASS,
        summary="All checks passed",
        issues=[],
        fix_instructions=[],
    )
    assert v.verdict == Verdict.PASS


def test_hook_entry_properties() -> None:
    h = HookEntry(
        class_path="Vehicle/CTrain",
        fn_name="ProcessControl",
        address="0x6f86a0",
        reversed=True,
        locked=False,
        is_virtual=False,
    )
    assert h.class_name == "CTrain"
    assert h.symbol == "CTrain::ProcessControl"


def test_reversal_result() -> None:
    t = FunctionTarget(address="0x6F86A0", class_name="CTrain", function_name="ProcessControl")
    r = ReversalResult(
        target=t,
        code="void CTrain::ProcessControl() { }",
        checker_verdict=None,
        parity_status=None,
        parity_findings=[],
        rounds_used=1,
        success=True,
    )
    assert r.success
    assert r.rounds_used == 1
