"""Ranks and selects the next function to reverse in a class."""
from __future__ import annotations

from re_agent.backend.protocol import REBackend
from re_agent.core.models import FunctionTarget
from re_agent.core.session import Session


def pick_next(
    class_name: str,
    backend: REBackend,
    session: Session,
    strategy: str = "high-impact",
    max_attempts_per_function: int = 3,
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
        if not session.is_completed(f.address)
        and session.attempt_count(f.address) < max_attempts_per_function
    ]

    if not candidates:
        return None

    if strategy == "dependency-order":
        dependency_counts: dict[str, int] = {}
        for candidate in candidates:
            try:
                dependency_counts[candidate.address] = backend.decompile(candidate.address).callees or 0
            except Exception:
                dependency_counts[candidate.address] = 1_000_000
        candidates.sort(
            key=lambda f: (dependency_counts[f.address], f.caller_count, f.name, f.address)
        )
    elif strategy == "easiest-first":
        candidates.sort(key=lambda f: (f.caller_count, f.name, f.address))
    else:
        candidates.sort(key=lambda f: (-f.caller_count, f.name, f.address))
    best = candidates[0]

    return FunctionTarget(
        address=best.address,
        class_name=best.class_name or class_name,
        function_name=best.name,
        caller_count=best.caller_count,
    )
