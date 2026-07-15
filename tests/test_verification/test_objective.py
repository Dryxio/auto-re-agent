"""Regression tests for conservative structural evidence handling."""
from __future__ import annotations

import json

from re_agent.backend.protocol import BackendCapabilities
from re_agent.core.models import AnalysisArtifact, DecompileResult, FunctionTarget, Verdict
from re_agent.verification.objective import verify_candidate


class _ErrorIRBackend:
    capabilities = BackendCapabilities(has_pcode=True, has_cfg=True)

    def decompile(self, target: str) -> DecompileResult:
        return DecompileResult(
            address=target,
            name="f",
            signature="void f()",
            decompiled="void f() {}",
            raw_output="void f() {}",
        )

    def get_pcode(self, target: str) -> AnalysisArtifact:
        payload = {"data": [{"error": "HighFunction unavailable"}]}
        return AnalysisArtifact("pcode", target, json.dumps(payload))

    def get_cfg(self, target: str) -> AnalysisArtifact:
        payload = {"data": [{"error": "CFG unavailable"}]}
        return AnalysisArtifact("cfg", target, json.dumps(payload))


def test_ir_error_objects_are_not_counted_as_successful_checks() -> None:
    verdict = verify_candidate(
        "void f() {}",
        FunctionTarget("0x100", "", "f"),
        _ErrorIRBackend(),  # type: ignore[arg-type]
    )
    assert verdict.verdict == Verdict.UNKNOWN
