"""Ranks and selects the next function to reverse in a class."""
from __future__ import annotations

from re_agent.backend.protocol import REBackend
from re_agent.core.models import FunctionTarget
from re_agent.core.session import Session


def pick_next(
    class_name: str,
    backend: REBackend,
    session: Session,
) -> FunctionTarget | None:
    """Pick the next function to reverse in a class.

    Filters out already-completed functions, ranks by caller_count (descending).
    Returns None if no candidates remain.
    """
    try:
        remaining = backend.remaining(class_name)
    except Exception:
        remaining = []

    if not remaining:
        try:
            remaining = backend.unimplemented(class_name)
        except Exception:
            return None

    candidates = [
        f for f in remaining
        if not session.is_attempted(f.address)
    ]

    if not candidates:
        return None

    candidates.sort(key=lambda f: f.caller_count, reverse=True)
    best = candidates[0]

    return FunctionTarget(
        address=best.address,
        class_name=best.class_name or class_name,
        function_name=best.name,
        caller_count=best.caller_count,
    )
