"""Top-level parity engine — runs all signals and aggregates results."""
from __future__ import annotations

import csv
import logging
import re
from pathlib import Path
from typing import Any

from re_agent.backend.protocol import REBackend
from re_agent.config.schema import ParityConfig, ReAgentConfig
from re_agent.core.models import (
    Finding,
    GhidraData,
    HookEntry,
    ParityStatus,
    SourceMatch,
)
from re_agent.parity.rules import (
    apply_semantic_rules,
    read_manual_checks,
    read_semantic_rules,
)
from re_agent.parity.scoring import score
from re_agent.parity.signals import ALL_SIGNALS
from re_agent.parity.source_indexer import SourceIndexer
from re_agent.utils.address import normalize_address
from re_agent.utils.text import has_fp_asm

logger = logging.getLogger(__name__)

HOOK_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]+$")


def read_hooks(path: Path, include_unreversed: bool = False) -> list[HookEntry]:
    """Read hooks from a CSV file.

    Supports both the standard column set (class, fn_name, address,
    reversed, locked, is_virtual) and minimal CSVs that only have
    address + name columns.  Missing columns default to safe values.
    """
    out: list[HookEntry] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = set(reader.fieldnames or [])
        for row in reader:
            addr = row.get("address", "").strip()
            if not HOOK_ADDR_RE.match(addr):
                continue

            rev = bool(int(row["reversed"])) if "reversed" in fields else True
            if not include_unreversed and not rev:
                continue

            # Derive class_path and fn_name from available columns
            class_path = row["class"].strip() if "class" in fields else ""
            fn_name = row["fn_name"].strip() if "fn_name" in fields else ""

            # Fall back to a combined "name" column (e.g. "CClass::Func")
            if not class_path and not fn_name and "name" in fields:
                full_name = row["name"].strip()
                if "::" in full_name:
                    class_path, fn_name = full_name.rsplit("::", 1)
                else:
                    fn_name = full_name

            out.append(HookEntry(
                class_path=class_path,
                fn_name=fn_name,
                address=addr.lower(),
                reversed=rev,
                locked=bool(int(row["locked"])) if "locked" in fields else False,
                is_virtual=bool(int(row["is_virtual"])) if "is_virtual" in fields else False,
            ))
    return out


def score_single(
    entry: HookEntry,
    source: SourceMatch | None,
    ghidra: GhidraData | None,
    config: ParityConfig,
    semantic_rules: list[Any] | None = None,
) -> tuple[ParityStatus, list[Finding]]:
    """Run all parity signals on a single function and return (status, findings)."""
    inline_skip = config.inline_wrapper_autoskip and source is not None and source.is_inline_internal_forwarder

    findings: list[Finding] = []
    for signal_fn in ALL_SIGNALS:
        result = signal_fn(
            source=source,
            ghidra=ghidra,
            inline_skip=inline_skip,
            call_count_warn_diff=config.call_count_warn_diff,
        )
        if result is not None:
            findings.append(result)

    if source is not None and semantic_rules:
        findings.extend(apply_semantic_rules(entry, source.body_no_comments, semantic_rules))

    if entry.reversed and source is None and not any(f.level == "red" for f in findings):
        findings.append(Finding(level="red", reason="Reversed hook has no source body"))

    status = score(findings)
    return status, findings


def fetch_ghidra_data(address: str, backend: REBackend) -> GhidraData:
    """Fetch and aggregate Ghidra analysis data for a single function address.

    Uses backend capability flags to skip unsupported queries gracefully.
    """
    data = GhidraData(resolved_address=address)
    caps = backend.capabilities

    # Decompile (always required)
    try:
        dec = backend.decompile(address)
        data.decompile_ok = True
        data.callers = dec.callers
        data.callees = dec.callees
        data.decompile_has_nan = "NAN" in dec.decompiled.upper() if dec.decompiled else False
    except Exception as exc:
        data.decompile_ok = False
        data.decompile_error = str(exc)

    # ASM
    if caps.has_asm:
        try:
            asm = backend.get_asm(address)
            if asm is not None:
                data.asm_ok = True
                data.asm_instruction_count = asm.instruction_count
                data.asm_call_count = asm.call_count
                data.asm_has_fp_sensitive = has_fp_asm(asm.instructions)
        except Exception as exc:
            data.asm_ok = False
            data.asm_error = str(exc)

    return data


def run_parity(
    hooks: list[HookEntry],
    source_root: Path,
    config: ReAgentConfig,
    backend: REBackend | None = None,
    ghidra_data_map: dict[str, GhidraData] | None = None,
) -> list[dict[str, Any]]:
    """Run parity checks on a list of hooks.

    Args:
        hooks: Functions to check.
        source_root: Root directory for C++ source files.
        config: Full agent config.
        backend: Optional RE backend for live Ghidra data fetching.
            When provided, Ghidra data is fetched for each function.
        ghidra_data_map: Optional pre-fetched Ghidra data keyed by
            normalized address. Entries here take priority over live
            fetching via ``backend``.

    Returns:
        List of result dicts with keys: hook, status, findings, source, ghidra.
    """
    profile = config.project_profile
    parity_cfg = config.parity

    indexer = SourceIndexer(source_root, profile)

    manual_checks: dict[str, Any] = {}
    if parity_cfg.manual_checks_file:
        manual_checks = read_manual_checks(Path(parity_cfg.manual_checks_file))

    semantic_rules = []
    if parity_cfg.semantic_rules_file:
        semantic_rules = read_semantic_rules(Path(parity_cfg.semantic_rules_file))

    results: list[dict[str, Any]] = []
    for entry in hooks:
        addr_key = normalize_address(entry.address)

        if addr_key in manual_checks:
            mc = manual_checks[addr_key]
            results.append({
                "hook": entry,
                "status": ParityStatus.GREEN,
                "findings": [Finding(level="info", reason=f"Manual check override: {mc.note}")],
            })
            continue

        # Try address-based lookup first (uses hook_patterns index),
        # then fall back to class::fn_name lookup.
        source = None
        if entry.fn_name:
            source = indexer.find(entry.class_name, entry.fn_name)
        if source is None:
            source = indexer.find_by_address(entry.address)

        # Resolve Ghidra data: pre-fetched map > live backend > None
        ghidra: GhidraData | None = None
        if ghidra_data_map and addr_key in ghidra_data_map:
            ghidra = ghidra_data_map[addr_key]
        elif backend is not None:
            try:
                ghidra = fetch_ghidra_data(entry.address, backend)
            except Exception:
                logger.warning("Failed to fetch Ghidra data for %s", entry.address, exc_info=True)

        status, findings = score_single(entry, source, ghidra, parity_cfg, semantic_rules)
        results.append({
            "hook": entry,
            "status": status,
            "findings": findings,
            "source": source,
            "ghidra": ghidra,
        })

    return results
