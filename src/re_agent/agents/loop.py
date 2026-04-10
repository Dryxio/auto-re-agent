"""Fix loop — reverser -> checker -> fix, bounded by max rounds."""
from __future__ import annotations

import json
import time
from pathlib import Path

from re_agent.agents.checker import CheckerAgent
from re_agent.agents.reverser import ReverserAgent
from re_agent.backend.protocol import REBackend
from re_agent.config.schema import ProjectProfile
from re_agent.core.models import (
    CheckerVerdict,
    FunctionTarget,
    ObjectiveVerdict,
    ReversalResult,
    Verdict,
)
from re_agent.core.session import Session
from re_agent.llm.protocol import LLMProvider
from re_agent.parity.source_indexer import SourceIndexer
from re_agent.verification.objective import verify_candidate


def run_fix_loop(
    target: FunctionTarget,
    backend: REBackend,
    reverser_llm: LLMProvider,
    checker_llm: LLMProvider | None = None,
    max_rounds: int = 4,
    log_dir: Path | None = None,
    source_root: Path | None = None,
    project_profile: ProjectProfile | None = None,
    indexer: SourceIndexer | None = None,
    session: Session | None = None,
    report_dir: Path | None = None,
    objective_verifier_enabled: bool = True,
    objective_call_count_tolerance: int = 3,
    objective_control_flow_tolerance: int = 2,
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

    reverser = ReverserAgent(
        reverser_llm,
        backend,
        source_root=source_root,
        project_profile=project_profile,
        indexer=indexer,
        session=session,
        report_dir=report_dir,
    )
    checker = CheckerAgent(checker_llm, backend)

    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    code = ""
    last_verdict: CheckerVerdict | None = None
    last_objective_verdict: ObjectiveVerdict | None = None

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
                objective_findings=last_objective_verdict.findings if last_objective_verdict else None,
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

        objective_verdict: ObjectiveVerdict | None = None
        if objective_verifier_enabled:
            objective_verdict = verify_candidate(
                code,
                target,
                backend,
                call_count_tolerance=objective_call_count_tolerance,
                control_flow_tolerance=objective_control_flow_tolerance,
            )
        last_objective_verdict = objective_verdict

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
                "objective_verdict": objective_verdict.verdict.value if objective_verdict else None,
                "objective_summary": objective_verdict.summary if objective_verdict else "",
                "objective_findings": objective_verdict.findings if objective_verdict else [],
            }
            check_path = log_dir / f"round{round_num}-{timestamp}-checker.json"
            check_path.write_text(json.dumps(check_log, indent=2), encoding="utf-8")

        if verdict.verdict == Verdict.PASS and (
            objective_verdict is None or objective_verdict.verdict != Verdict.FAIL
        ):
            return ReversalResult(
                target=target,
                code=code,
                checker_verdict=verdict,
                objective_verdict=objective_verdict,
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
        objective_verdict=last_objective_verdict,
        parity_status=None,
        parity_findings=[],
        rounds_used=max_rounds,
        success=False,
    )
