"""Tests for parity scoring."""
from __future__ import annotations

from re_agent.core.models import Finding, ParityStatus
from re_agent.parity.scoring import score


def test_all_green() -> None:
    assert score([]) == ParityStatus.GREEN
    assert score([Finding(level="info", reason="test")]) == ParityStatus.GREEN


def test_yellow_dominates_info() -> None:
    findings = [
        Finding(level="info", reason="ok"),
        Finding(level="yellow", reason="warning"),
    ]
    assert score(findings) == ParityStatus.YELLOW


def test_red_dominates_all() -> None:
    findings = [
        Finding(level="info", reason="ok"),
        Finding(level="yellow", reason="warning"),
        Finding(level="red", reason="error"),
    ]
    assert score(findings) == ParityStatus.RED
