"""Conservative structural verification that does not rely on an LLM."""
from __future__ import annotations

from re_agent.backend.protocol import REBackend
from re_agent.core.models import FunctionTarget, ObjectiveVerdict, Verdict
from re_agent.utils.text import count_calls, count_control_flow, strip_comments


def verify_candidate(
    code: str,
    target: FunctionTarget,
    backend: REBackend,
    call_count_tolerance: int = 3,
    control_flow_tolerance: int = 2,
) -> ObjectiveVerdict:
    """Return FAIL only on strong structural mismatches, else PASS/UNKNOWN."""
    if not code.strip():
        return ObjectiveVerdict(
            verdict=Verdict.FAIL,
            summary="No candidate code produced",
            findings=["Candidate code is empty"],
        )

    source_body = strip_comments(_extract_body(code))
    source_call_count, _, _ = count_calls(source_body)
    source_flow_count = count_control_flow(source_body)

    findings: list[str] = []
    checks_run = 0

    try:
        decompile = backend.decompile(target.address)
    except Exception as exc:
        return ObjectiveVerdict(
            verdict=Verdict.UNKNOWN,
            summary="Objective verifier could not read decompile output",
            findings=[str(exc)],
        )

    decompile_body = strip_comments(_extract_body(decompile.raw_output))
    decompile_flow_count = count_control_flow(decompile_body)
    if decompile.callees is not None:
        checks_run += 1
        call_diff = abs(decompile.callees - source_call_count)
        if call_diff >= call_count_tolerance and source_call_count < decompile.callees:
            findings.append(
                f"Call count mismatch: decompile reports {decompile.callees} callees, "
                f"candidate has {source_call_count} calls"
            )

    if decompile_flow_count >= 2:
        checks_run += 1
        flow_diff = decompile_flow_count - source_flow_count
        if flow_diff >= control_flow_tolerance and source_flow_count < decompile_flow_count:
            findings.append(
                f"Control-flow mismatch: decompile has {decompile_flow_count} branches/loops, "
                f"candidate has {source_flow_count}"
            )

    if backend.capabilities.has_asm:
        try:
            asm = backend.get_asm(target.address)
        except Exception:
            asm = None
        if asm is not None:
            checks_run += 1
            call_diff = abs(asm.call_count - source_call_count)
            if call_diff >= call_count_tolerance and source_call_count < asm.call_count:
                findings.append(
                    f"ASM call mismatch: disassembly has {asm.call_count} calls, "
                    f"candidate has {source_call_count}"
                )

    if findings:
        return ObjectiveVerdict(
            verdict=Verdict.FAIL,
            summary="Objective verifier found structural mismatches",
            findings=findings,
        )
    if checks_run == 0:
        return ObjectiveVerdict(
            verdict=Verdict.UNKNOWN,
            summary="Objective verifier had insufficient structural data",
            findings=[],
        )
    return ObjectiveVerdict(
        verdict=Verdict.PASS,
        summary="No structural mismatches found",
        findings=[],
    )


def _extract_body(text: str) -> str:
    open_brace = text.find("{")
    close_brace = text.rfind("}")
    if open_brace == -1 or close_brace == -1 or close_brace <= open_brace:
        return text
    return text[open_brace:close_brace + 1]
