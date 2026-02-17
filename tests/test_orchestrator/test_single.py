"""Tests for single function orchestrator."""
from __future__ import annotations

from re_agent.config.schema import ReAgentConfig
from re_agent.core.models import FunctionTarget


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
