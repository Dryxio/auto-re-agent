"""Candidate overlays and configurable build/test validation gates."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from re_agent.config.schema import ValidationConfig
from re_agent.core.models import FunctionTarget, SourceMatch, ValidationVerdict, Verdict


def extract_candidate_body(code: str) -> str:
    """Extract the outer C++ body from generated code."""
    open_brace = code.find("{")
    close_brace = code.rfind("}")
    if open_brace == -1 or close_brace <= open_brace:
        return code.strip()
    return code[open_brace:close_brace + 1].strip()


def create_candidate_overlay(
    target: FunctionTarget,
    code: str,
    source: SourceMatch | None,
    source_root: Path,
    report_dir: Path,
    project_root: Path | None = None,
    copy_project: bool = False,
) -> Path:
    """Write a source overlay with the original function body replaced."""
    safe_address = _sanitize_path_component(target.address)
    overlay_root: Path | None = None
    try:
        if copy_project:
            if project_root is None:
                raise ValueError("project_root is required when copy_project is enabled")
            overlay_root = Path(tempfile.mkdtemp(prefix=f"re-agent-{safe_address}-"))
            shutil.copytree(
                project_root,
                overlay_root,
                dirs_exist_ok=True,
                symlinks=True,
                ignore=shutil.ignore_patterns(
                    ".git", ".venv", "build", "reports", "__pycache__", "*.pyc"
                ),
            )
        else:
            overlay_root = report_dir / "candidates" / safe_address
        overlay_root.mkdir(parents=True, exist_ok=True)
        (overlay_root / ".re-agent-overlay").write_text(
            "schema_version=1\n", encoding="utf-8"
        )
        if source is None:
            safe_class_name = _sanitize_path_component(target.class_name)
            safe_function_name = _sanitize_path_component(target.function_name)
            candidate_file = overlay_root / f"{safe_class_name}_{safe_function_name}.cpp"
            candidate_file.parent.mkdir(parents=True, exist_ok=True)
            candidate_file.write_text(code.rstrip() + "\n", encoding="utf-8")
            return candidate_file

        original_path = Path(source.path)
        relative_root = project_root if copy_project and project_root is not None else source_root
        try:
            relative = original_path.resolve().relative_to(relative_root.resolve())
        except ValueError:
            if copy_project:
                raise ValueError(
                    f"Source file {original_path} is outside validation.project_root {relative_root}"
                ) from None
            relative = Path(original_path.name)
        candidate_file = overlay_root / relative
        candidate_file.parent.mkdir(parents=True, exist_ok=True)

        original = original_path.read_text(encoding="utf-8", errors="ignore")
        if source.body_end <= source.body_start:
            raise ValueError(f"Source body offsets unavailable for {source.path}")
        body = extract_candidate_body(code)
        overlaid = original[:source.body_start] + body + original[source.body_end:]
        candidate_file.write_text(overlaid, encoding="utf-8")
        return candidate_file
    except Exception:
        if copy_project and overlay_root is not None:
            shutil.rmtree(overlay_root, ignore_errors=True)
        raise


def validate_candidate(
    config: ValidationConfig,
    candidate_file: Path,
    source_file: str | None,
) -> ValidationVerdict:
    """Run configured build and test commands against the candidate overlay."""
    commands = [("build", command) for command in config.build_commands]
    commands.extend(("test", command) for command in config.test_commands)
    commands.extend(("runtime", command) for command in config.runtime_commands)
    if not config.enabled:
        return ValidationVerdict(
            verdict=Verdict.UNKNOWN,
            summary="Candidate validation disabled",
            overlay_file=str(candidate_file),
        )
    if config.require_build and not config.build_commands:
        return _failed("Build validation is required but no build_commands are configured", candidate_file)
    if config.require_tests and not config.test_commands:
        return _failed("Test validation is required but no test_commands are configured", candidate_file)
    if config.require_runtime and not config.runtime_commands:
        return _failed("Runtime validation is required but no runtime_commands are configured", candidate_file)
    if (
        source_file is None
        and config.copy_project
        and commands
        and not any("{candidate_file}" in command for _, command in commands)
    ):
        return _failed(
            "Candidate has no source location; isolated project commands must explicitly use {candidate_file}",
            candidate_file,
        )
    if not commands:
        return ValidationVerdict(
            verdict=Verdict.UNKNOWN,
            summary="Candidate overlay created; no build or test commands configured",
            overlay_file=str(candidate_file),
        )
    if not config.copy_project:
        unsafe = [command for _, command in commands if not _consumes_candidate(command)]
        if unsafe:
            return _failed(
                "Non-isolated validation commands must explicitly consume "
                "{candidate_file}, {overlay_root}, RE_AGENT_CANDIDATE_FILE, or "
                "RE_AGENT_OVERLAY_ROOT",
                candidate_file,
                [f"does not consume candidate: {command}" for command in unsafe],
            )

    env = os.environ.copy()
    env.update({
        "RE_AGENT_CANDIDATE_FILE": str(candidate_file.resolve()),
        "RE_AGENT_OVERLAY_ROOT": str(_overlay_root(candidate_file).resolve()),
        "RE_AGENT_SOURCE_FILE": source_file or "",
    })
    findings: list[str] = []
    for kind, command in commands:
        expanded = command
        replacements = {
            "{candidate_file}": str(candidate_file.resolve()),
            "{overlay_root}": str(_overlay_root(candidate_file).resolve()),
            "{source_file}": source_file or "",
        }
        for placeholder, value in replacements.items():
            expanded = expanded.replace(placeholder, value)
        try:
            proc = subprocess.run(
                ["/bin/sh", "-lc", expanded],
                cwd=_working_directory(config, candidate_file),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=config.command_timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return _failed(f"{kind} command timed out: {command}", candidate_file, findings)
        tail = "\n".join(proc.stdout.splitlines()[-20:])
        findings.append(f"{kind}: {command} -> exit {proc.returncode}\n{tail}".rstrip())
        if proc.returncode != 0:
            return _failed(f"Candidate {kind} gate failed", candidate_file, findings)

    if not config.trust_configured_commands:
        return ValidationVerdict(
            verdict=Verdict.UNKNOWN,
            summary=(
                "Configured commands passed but are not accepted as proof until "
                "validation.trust_configured_commands is explicitly enabled"
            ),
            findings=findings,
            overlay_file=str(candidate_file),
        )

    return ValidationVerdict(
        verdict=Verdict.PASS,
        summary="All configured candidate build/test gates passed",
        findings=findings,
        overlay_file=str(candidate_file),
    )


def cleanup_candidate_overlay(candidate_file: Path) -> None:
    """Remove a temporary full-project overlay created for isolated validation."""
    root = _overlay_root(candidate_file)
    if root.name.startswith("re-agent-") and (root / ".re-agent-overlay").exists():
        shutil.rmtree(root, ignore_errors=True)


def _sanitize_path_component(value: str) -> str:
    """Replace characters that are illegal in host filesystem names."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value)


def _consumes_candidate(command: str) -> bool:
    markers = (
        "{candidate_file}",
        "{overlay_root}",
        "$RE_AGENT_CANDIDATE_FILE",
        "${RE_AGENT_CANDIDATE_FILE}",
        "$RE_AGENT_OVERLAY_ROOT",
        "${RE_AGENT_OVERLAY_ROOT}",
    )
    return any(marker in command for marker in markers)


def _overlay_root(candidate_file: Path) -> Path:
    for parent in (candidate_file.parent, *candidate_file.parents):
        if (parent / ".re-agent-overlay").exists():
            return parent
    parts = candidate_file.parts
    if "candidates" in parts:
        idx = parts.index("candidates")
        if idx + 1 < len(parts):
            return Path(*parts[:idx + 2])
    return candidate_file.parent


def _working_directory(config: ValidationConfig, candidate_file: Path) -> str:
    overlay_root = str(_overlay_root(candidate_file).resolve())
    value = config.working_directory.replace("{overlay_root}", overlay_root)
    if config.copy_project and config.working_directory == ".":
        return overlay_root
    if config.copy_project and not Path(value).is_absolute():
        return str(Path(overlay_root) / value)
    return value


def _failed(
    summary: str,
    candidate_file: Path,
    findings: list[str] | None = None,
) -> ValidationVerdict:
    return ValidationVerdict(
        verdict=Verdict.FAIL,
        summary=summary,
        findings=findings or [],
        overlay_file=str(candidate_file),
    )
