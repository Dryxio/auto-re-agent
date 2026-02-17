"""re-agent parity command — run parity checks."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from re_agent.config.loader import load_config
from re_agent.core.models import HookEntry, ParityStatus
from re_agent.parity.engine import read_hooks, run_parity
from re_agent.utils.address import normalize_address


def cmd_parity(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    profile = config.project_profile

    source_root = Path(profile.source_root)
    if not source_root.exists():
        print(f"Error: source root not found: {source_root}", file=sys.stderr)
        return 1

    hooks_csv = profile.hooks_csv
    hooks: list[HookEntry] = []
    if hooks_csv:
        hooks_path = Path(hooks_csv)
        if hooks_path.exists():
            hooks = read_hooks(hooks_path)
        else:
            print(f"Warning: hooks CSV not found: {hooks_path}", file=sys.stderr)

    # Filter by address, or synthesize HookEntry for addresses not in CSV
    if args.address:
        wanted = {normalize_address(a) for a in args.address}
        matched = [h for h in hooks if normalize_address(h.address) in wanted]
        # Create entries for any addresses not found in the CSV
        matched_addrs = {normalize_address(h.address) for h in matched}
        for addr in wanted - matched_addrs:
            matched.append(HookEntry(
                class_path="",
                fn_name="",
                address=addr,
                reversed=True,
                locked=False,
                is_virtual=False,
            ))
        hooks = matched
    elif not hooks:
        print("No hooks loaded. Provide --address or configure hooks_csv in project_profile.", file=sys.stderr)
        return 1

    # Filter by regex
    if args.filter:
        rx = re.compile(args.filter)
        hooks = [h for h in hooks if rx.search(h.symbol) or rx.search(h.class_path)]

    # Limit
    if args.limit:
        hooks = hooks[:args.limit]

    if not hooks:
        print("No hooks selected.")
        return 0

    backend = None
    if not args.skip_ghidra:
        try:
            from re_agent.backend.registry import create_backend
            backend = create_backend(config.backend)
        except Exception as exc:
            print(f"Warning: could not initialize backend ({exc}), running source-only checks", file=sys.stderr)

    results = run_parity(hooks, source_root, config, backend=backend)

    # Print results
    counts: dict[str, int] = {s.value: 0 for s in ParityStatus}
    for r in results:
        status = r["status"]
        status_str = status.value if isinstance(status, ParityStatus) else str(status)
        counts[status_str] = counts.get(status_str, 0) + 1
        hook = r["hook"]
        print(f"  {hook.symbol} ({hook.address}) -> {status_str.upper()}")

    green = counts.get(ParityStatus.GREEN.value, 0)
    yellow = counts.get(ParityStatus.YELLOW.value, 0)
    red = counts.get(ParityStatus.RED.value, 0)
    print(f"\nSummary: GREEN={green} YELLOW={yellow} RED={red}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        serializable = []
        for r in results:
            hook = r["hook"]
            status = r["status"]
            serializable.append({
                "symbol": hook.symbol,
                "address": hook.address,
                "status": status.value if isinstance(status, ParityStatus) else str(status),
                "findings": [{"level": f.level, "reason": f.reason} for f in r.get("findings", [])],
            })
        output_path.write_text(json.dumps({"results": serializable}, indent=2), encoding="utf-8")
        print(f"Report written to {output_path}")

    if args.strict_exit and red > 0:
        return 1
    return 0
