"""Fix loop — reverser -> checker -> fix, bounded by max rounds."""
from __future__ import annotations

import json
import time
from pathlib import Path

from re_agent.agents.checker import CheckerAgent
from re_agent.agents.reverser import ReverserAgent
from re_agent.backend.protocol import REBackend
from re_agent.core.models import (
    CheckerVerdict,
    FunctionTarget,
    ReversalResult,
    Verdict,
)
from re_agent.llm.protocol import LLMProvider


def run_fix_loop(
    target: FunctionTarget,
    backend: REBackend,
    reverser_llm: LLMProvider,
    checker_llm: LLMProvider | None = None,
    max_rounds: int = 4,
    log_dir: Path | None = None,
) -> ReversalResult:
    """Run the reverser->checker->fix loop up to max_rounds.

    Args:
        target: Function to reverse
        backend: RE backend for Ghidra data
        reverser_llm: LLM provider for the reverser agent
        checker_llm: LLM provider for the checker agent (defaults to reverser_llm)
        max_rounds: Maximum fix iterations
        log_dir: Directory to write prompt/response logs

    Returns:
        ReversalResult with the final code and verdict
    """
    if checker_llm is None:
        checker_llm = reverser_llm

    reverser = ReverserAgent(reverser_llm, backend)
    checker = CheckerAgent(checker_llm, backend)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    code = ""
    last_verdict: CheckerVerdict | None = None

    for round_num in range(1, max_rounds + 1):
        timestamp = time.strftime("%Y%m%d-%H%M%S")

        # Reverse (or fix)
        if round_num == 1:
            code, tag = reverser.reverse(target)
        else:
            assert last_verdict is not None
            code, tag = reverser.fix(
                checker_report=last_verdict.summary,
                issues=last_verdict.issues,
                fix_instructions=last_verdict.fix_instructions,
                target=target,
            )

        if log_dir:
            log_entry = {
                "round": round_num,
                "timestamp": timestamp,
                "phase": "reverse" if round_num == 1 else "fix",
                "target": f"{target.class_name}::{target.function_name}",
                "address": target.address,
                "prompt": reverser.last_prompt,
                "response": reverser.last_response,
                "code_length": len(code),
            }
            log_path = log_dir / f"round{round_num}-{timestamp}-reverser.json"
            log_path.write_text(json.dumps(log_entry, indent=2), encoding="utf-8")

        # Check
        verdict = checker.check(code, target)
        last_verdict = verdict

        if log_dir:
            check_log = {
                "round": round_num,
                "timestamp": timestamp,
                "phase": "check",
                "prompt": checker.last_prompt,
                "response": checker.last_response,
                "verdict": verdict.verdict.value,
                "summary": verdict.summary,
                "issues": verdict.issues,
                "fix_instructions": verdict.fix_instructions,
            }
            check_path = log_dir / f"round{round_num}-{timestamp}-checker.json"
            check_path.write_text(json.dumps(check_log, indent=2), encoding="utf-8")

        if verdict.verdict == Verdict.PASS:
            return ReversalResult(
                target=target,
                code=code,
                checker_verdict=verdict,
                parity_status=None,
                parity_findings=[],
                rounds_used=round_num,
                success=True,
            )

    # Exhausted all rounds
    return ReversalResult(
        target=target,
        code=code,
        checker_verdict=last_verdict,
        parity_status=None,
        parity_findings=[],
        rounds_used=max_rounds,
        success=False,
    )
