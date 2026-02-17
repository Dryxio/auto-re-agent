"""Configuration schema dataclasses for re-agent."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectProfile:
    """Project-specific patterns and paths."""

    hook_patterns: list[str] = field(default_factory=lambda: [
        r"RH_ScopedInstall\s*\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+)",
        r"RH_ScopedVirtualInstall\s*\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+)",
    ])
    stub_patterns: list[str] = field(default_factory=lambda: [
        r"plugin::Call",
    ])
    stub_markers: list[str] = field(default_factory=lambda: [
        "NOTSA_UNREACHABLE",
    ])
    stub_call_prefix: str = "plugin::Call"
    class_macro: str = "RH_ScopedClass"
    source_root: str = "source/game_sa"
    source_extensions: list[str] = field(default_factory=lambda: [
        ".cpp", ".h", ".hpp",
    ])
    hooks_csv: str | None = "docs/hooks.csv"


@dataclass
class LLMConfig:
    """LLM provider configuration."""

    provider: str = "claude"
    model: str = "claude-sonnet-4-5-20250929"
    api_key: str | None = None
    base_url: str | None = None
    max_tokens: int = 4096
    temperature: float = 0.0


@dataclass
class BackendConfig:
    """Decompiler backend configuration."""

    type: str = "ghidra-bridge"
    cli_path: str = "ghidra"
    timeout_s: int = 45


@dataclass
class ParityConfig:
    """Static parity verification settings."""

    enabled: bool = True
    call_count_warn_diff: int = 3
    inline_wrapper_autoskip: bool = False
    semantic_rules_file: str | None = None
    manual_checks_file: str | None = None
    cache_dir: str = ".cache/re-agent-parity"


@dataclass
class OrchestratorConfig:
    """Orchestrator loop settings."""

    max_review_rounds: int = 4
    max_functions_per_class: int = 10


@dataclass
class OutputConfig:
    """Output and reporting settings."""

    report_dir: str = "reports/re-agent"
    log_dir: str = "reports/re-agent/logs"
    session_file: str = "re-agent-progress.json"
    format: str = "json"


@dataclass
class ReAgentConfig:
    """Top-level configuration for the re-agent system."""

    project_profile: ProjectProfile = field(default_factory=ProjectProfile)
    llm: LLMConfig = field(default_factory=LLMConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    parity: ParityConfig = field(default_factory=ParityConfig)
    orchestrator: OrchestratorConfig = field(default_factory=OrchestratorConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def create_default(cls) -> ReAgentConfig:
        """Create a configuration with all default values."""
        return cls(
            project_profile=ProjectProfile(),
            llm=LLMConfig(),
            backend=BackendConfig(),
            parity=ParityConfig(),
            orchestrator=OrchestratorConfig(),
            output=OutputConfig(),
        )
