"""Tests for config loading."""
from __future__ import annotations

from pathlib import Path

import pytest

from re_agent.config.loader import load_config
from re_agent.config.schema import ReAgentConfig


def test_load_default_config() -> None:
    config = load_config(None)
    assert isinstance(config, ReAgentConfig)
    assert config.llm.provider == "claude"
    assert config.backend.type == "ghidra-bridge"
    assert config.orchestrator.max_review_rounds == 4


def test_load_from_yaml(sample_config_path: Path) -> None:
    config = load_config(sample_config_path)
    assert config.project_profile.stub_call_prefix == "plugin::Call"
    assert config.llm.model == "claude-sonnet-4-5-20250929"
    assert config.parity.call_count_warn_diff == 3


def test_cli_overrides() -> None:
    config = load_config(None, cli_overrides={"llm.provider": "openai", "orchestrator.max_review_rounds": "6"})
    assert config.llm.provider == "openai"
    assert config.orchestrator.max_review_rounds == 6


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RE_AGENT_LLM_PROVIDER", "openai")
    monkeypatch.setenv("RE_AGENT_LLM_MODEL", "gpt-4o")
    config = load_config(None)
    assert config.llm.provider == "openai"
    assert config.llm.model == "gpt-4o"
