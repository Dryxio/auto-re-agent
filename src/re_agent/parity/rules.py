"""Semantic rules (JSON) and manual approval checks (.md) for parity overrides."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from re_agent.core.models import Finding, HookEntry, ManualCheckEntry, SemanticRule
from re_agent.utils.address import normalize_address

MANUAL_CHECK_LINE_RE = re.compile(r"^\s*-\s*\[(x|X)\]\s*(0x[0-9a-fA-F]+)\b(.*)$")


def read_manual_checks(path: Path) -> dict[str, ManualCheckEntry]:
    if not path.exists():
        return {}
    out: dict[str, ManualCheckEntry] = {}
    for line_no, ln in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
        m = MANUAL_CHECK_LINE_RE.match(ln)
        if not m:
            continue
        addr = normalize_address(m.group(2))
        note = m.group(3).strip(" -|")
        out[addr] = ManualCheckEntry(line=line_no, note=note)
    return out


def read_semantic_rules(path: Path) -> list[SemanticRule]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"WARNING: semantic rules JSON parse failed ({path}): {e}", file=sys.stderr)
        return []

    if isinstance(raw, dict):
        rules_raw = raw.get("rules", [])
    elif isinstance(raw, list):
        rules_raw = raw
    else:
        print(f"WARNING: semantic rules must be a JSON object/list: {path}", file=sys.stderr)
        return []

    rules: list[SemanticRule] = []
    for i, rr in enumerate(rules_raw):
        if not isinstance(rr, dict):
            continue
        rid = str(rr.get("id", f"rule-{i + 1}"))
        reason = str(rr.get("reason", "")).strip()
        if not reason:
            reason = f"Semantic parity rule '{rid}' failed"
        sev = str(rr.get("severity", "red")).lower()
        if sev not in {"red", "yellow", "info"}:
            sev = "red"
        addresses = [normalize_address(a) for a in rr.get("addresses", []) if isinstance(a, str)]
        symbols = [s for s in rr.get("symbols", []) if isinstance(s, str)]
        source_all_of = [s for s in rr.get("source_all_of", []) if isinstance(s, str)]
        source_any_of = [s for s in rr.get("source_any_of", []) if isinstance(s, str)]
        source_none_of = [s for s in rr.get("source_none_of", []) if isinstance(s, str)]
        rules.append(SemanticRule(
            id=rid, reason=reason, severity=sev,
            addresses=addresses, symbols=symbols,
            source_all_of=source_all_of, source_any_of=source_any_of, source_none_of=source_none_of,
        ))
    return rules


def _match_pattern(text: str, pattern: str) -> bool:
    if pattern.startswith("re:"):
        return re.search(pattern[3:], text) is not None
    return pattern in text


def rule_matches_entry(rule: SemanticRule, entry: HookEntry) -> bool:
    key = normalize_address(entry.address)
    if rule.addresses and key not in rule.addresses:
        return False
    if not rule.symbols:
        return True
    return any(_match_pattern(entry.symbol, sym_pat) for sym_pat in rule.symbols)


def apply_semantic_rules(
    entry: HookEntry,
    source_text: str,
    rules: list[SemanticRule],
) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if not rule_matches_entry(rule, entry):
            continue
        if any(not _match_pattern(source_text, pat) for pat in rule.source_all_of):
            findings.append(Finding(level=rule.severity, reason=f"[semantic:{rule.id}] {rule.reason}"))
            continue
        if rule.source_any_of and not any(_match_pattern(source_text, pat) for pat in rule.source_any_of):
            findings.append(Finding(level=rule.severity, reason=f"[semantic:{rule.id}] {rule.reason}"))
            continue
        if any(_match_pattern(source_text, pat) for pat in rule.source_none_of):
            findings.append(Finding(level=rule.severity, reason=f"[semantic:{rule.id}] {rule.reason}"))
            continue
    return findings
