"""Tests for single function orchestrator."""
from __future__ import annotations

from pathlib import Path

from re_agent.backend.stub import StubBackend
from re_agent.config.schema import ReAgentConfig
from re_agent.core.models import FunctionTarget, ParityStatus, Verdict
from re_agent.llm.protocol import Message
from re_agent.orchestrator.single import reverse_single


class _LLM:
    def __init__(self, response: str) -> None:
        self.response = response

    def send(self, messages: list[Message], **kwargs: object) -> str:
        return self.response

    @property
    def supports_conversations(self) -> bool:
        return False

    def new_conversation(self, system: str) -> str:
        return ""

    def resume(self, conversation_id: str, message: str) -> str:
        return self.response


def test_dry_run_smoke() -> None:
    """Smoke test that config + target creation works."""
    config = ReAgentConfig.create_default()
    target = FunctionTarget(
        address="0x6F86A0",
        class_name="CTrain",
        function_name="ProcessControl",
    )
    assert target.address == "0x6F86A0"
    assert config.orchestrator.max_review_rounds == 4


def test_candidate_parity_is_blocking_and_uses_generated_body(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "CTest.cpp").write_text(
        "void CTest::Foo() { ExistingImplementation(); }\n",
        encoding="utf-8",
    )
    config = ReAgentConfig.create_default()
    config.project_profile.source_root = str(source_root)
    config.output.report_dir = str(tmp_path / "reports")
    config.output.log_dir = str(tmp_path / "logs")
    config.output.session_file = str(tmp_path / "session.json")
    config.orchestrator.max_review_rounds = 1
    config.orchestrator.investigation_enabled = False

    reverser = _LLM(
        "```cpp\nvoid CTest::Foo() { NOTSA_UNREACHABLE(); }\n```\n"
        "REVERSED_FUNCTION: CTest::Foo (0x100)"
    )
    checker = _LLM(
        "VERDICT: PASS\nSUMMARY: Looks right\nISSUES:\n- none\n"
        "FIX_INSTRUCTIONS:\n- none"
    )
    result = reverse_single(
        FunctionTarget("0x100", "CTest", "Foo"),
        config,
        StubBackend(),
        reverser,
        checker_llm=checker,
    )

    assert result.parity_status == ParityStatus.RED
    assert result.validation_verdict is not None
    assert result.validation_verdict.verdict == Verdict.UNKNOWN
    assert result.success is False


def test_unknown_validation_blocks_acceptance_by_default(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "CTest.cpp").write_text(
        "void CTest::Foo() { ExistingImplementation(); }\n",
        encoding="utf-8",
    )
    config = ReAgentConfig.create_default()
    config.project_profile.source_root = str(source_root)
    config.output.report_dir = str(tmp_path / "reports")
    config.output.log_dir = str(tmp_path / "logs")
    config.orchestrator.max_review_rounds = 1
    config.orchestrator.investigation_enabled = False
    config.parity.enabled = False

    result = reverse_single(
        FunctionTarget("0x100", "CTest", "Foo"),
        config,
        StubBackend(),
        _LLM("```cpp\nvoid CTest::Foo() { NewImplementation(); }\n```"),
        checker_llm=_LLM(
            "VERDICT: PASS\nSUMMARY: Looks right\nISSUES:\n- none\n"
            "FIX_INSTRUCTIONS:\n- none"
        ),
    )

    assert result.validation_verdict is not None
    assert result.validation_verdict.verdict == Verdict.UNKNOWN
    assert result.success is False


def test_explicitly_disabled_validation_does_not_block(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "CTest.cpp").write_text("void CTest::Foo() {}\n", encoding="utf-8")
    config = ReAgentConfig.create_default()
    config.project_profile.source_root = str(source_root)
    config.output.report_dir = str(tmp_path / "reports")
    config.output.log_dir = str(tmp_path / "logs")
    config.orchestrator.max_review_rounds = 1
    config.orchestrator.investigation_enabled = False
    config.orchestrator.objective_verifier_enabled = False
    config.parity.enabled = False
    config.validation.enabled = False

    result = reverse_single(
        FunctionTarget("0x100", "CTest", "Foo"),
        config,
        StubBackend(),
        _LLM("```cpp\nvoid CTest::Foo() {}\n```"),
        checker_llm=_LLM(
            "VERDICT: PASS\nSUMMARY: Looks right\nISSUES:\n- none\n"
            "FIX_INSTRUCTIONS:\n- none"
        ),
    )

    assert result.validation_verdict is not None
    assert result.validation_verdict.verdict == Verdict.UNKNOWN
    assert result.success is True
