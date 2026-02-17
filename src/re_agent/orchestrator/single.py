"""Single function reversal pipeline."""
from __future__ import annotations

import logging
from pathlib import Path

from re_agent.agents.loop import run_fix_loop
from re_agent.backend.protocol import REBackend
from re_agent.config.schema import ReAgentConfig
from re_agent.core.models import FunctionTarget, HookEntry, ReversalResult
from re_agent.core.session import Session
from re_agent.llm.protocol import LLMProvider
from re_agent.parity.engine import fetch_ghidra_data, score_single
from re_agent.parity.source_indexer import SourceIndexer

logger = logging.getLogger(__name__)


def reverse_single(
    target: FunctionTarget,
    config: ReAgentConfig,
    backend: REBackend,
    llm: LLMProvider,
    session: Session | None = None,
    output_dir: Path | None = None,
    indexer: SourceIndexer | None = None,
) -> ReversalResult:
    """Reverse a single function: agent loop -> optional parity check -> record.

    Args:
        output_dir: If provided, write the generated code to a file in this
            directory.  The file is named ``<address>_<class>_<func>.cpp``.
        indexer: Pre-built source indexer.  When running multiple functions
            in the same class, callers should build the indexer once and pass
            it here to avoid re-scanning the entire source tree each time.
    """
    log_dir = Path(config.output.log_dir) if config.output.log_dir else None

    result = run_fix_loop(
        target=target,
        backend=backend,
        reverser_llm=llm,
        checker_llm=llm,
        max_rounds=config.orchestrator.max_review_rounds,
        log_dir=log_dir,
    )

    # Write generated code to a file so users don't have to dig through logs
    if result.code:
        code_dir = output_dir or (Path(config.output.report_dir) / "code")
        try:
            code_dir.mkdir(parents=True, exist_ok=True)
            safe_name = f"{target.address}_{target.class_name}_{target.function_name}.cpp"
            safe_name = safe_name.replace("::", "_").replace("/", "_")
            code_path = code_dir / safe_name
            code_path.write_text(result.code, encoding="utf-8")
            logger.info("Code written to %s", code_path)
        except OSError as exc:
            logger.warning("Failed to write code file: %s", exc)

    # Run parity check if enabled and code was produced
    if config.parity.enabled and result.code:
        try:
            if indexer is None:
                source_root = Path(config.project_profile.source_root)
                indexer = SourceIndexer(source_root, config.project_profile)
            source = indexer.find(target.class_name, target.function_name)

            # Fetch Ghidra data from the backend for signal checks
            ghidra_data = None
            if backend.capabilities.has_decompile:
                try:
                    ghidra_data = fetch_ghidra_data(target.address, backend)
                except Exception:
                    logger.debug("Ghidra data fetch failed for %s, running source-only", target.address, exc_info=True)

            status, findings = score_single(
                entry=_target_to_hook(target),
                source=source,
                ghidra=ghidra_data,
                config=config.parity,
            )
            result = ReversalResult(
                target=result.target,
                code=result.code,
                checker_verdict=result.checker_verdict,
                parity_status=status,
                parity_findings=findings,
                rounds_used=result.rounds_used,
                success=result.success,
            )
        except (FileNotFoundError, ValueError) as exc:
            logger.warning("Parity check failed for %s: %s", target.address, exc)

    if session:
        session.record_result(result)

    return result


def _target_to_hook(target: FunctionTarget) -> HookEntry:
    return HookEntry(
        class_path=target.class_name,
        fn_name=target.function_name,
        address=target.address,
        reversed=True,
        locked=False,
        is_virtual=False,
    )
