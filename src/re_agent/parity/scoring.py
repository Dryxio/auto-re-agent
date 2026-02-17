"""Aggregate parity findings into a single GREEN/YELLOW/RED status."""
from __future__ import annotations

from re_agent.core.models import Finding, ParityStatus


def score(findings: list[Finding]) -> ParityStatus:
    """Return the highest severity from a list of findings."""
    has_red = any(f.level == "red" for f in findings)
    has_yellow = any(f.level == "yellow" for f in findings)
    if has_red:
        return ParityStatus.RED
    if has_yellow:
        return ParityStatus.YELLOW
    return ParityStatus.GREEN
