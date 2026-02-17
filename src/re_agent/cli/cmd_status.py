"""re-agent status command — show reversal progress."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from re_agent.config.loader import load_config
from re_agent.core.session import Session
from re_agent.reports.tracker import ProgressTracker


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    session = Session(config.output.session_file)
    tracker = ProgressTracker(session)

    if args.format == "json":
        data = tracker.get_function_table(args.class_name) if args.class_name else session.get_summary()
        print(json.dumps(data, indent=2))
        return 0

    if args.format == "markdown":
        rows = tracker.get_function_table(args.class_name)
        if not rows:
            print("No functions recorded yet.")
            return 0
        print("| Address | Class | Function | Status | Rounds | Time |")
        print("|---------|-------|----------|--------|--------|------|")
        for r in rows:
            addr = r['address']
            cls = r['class']
            fn = r['function']
            st = r['status']
            rds = r['rounds']
            ts = r['timestamp']
            print(f"| {addr} | {cls} | {fn} | {st} | {rds} | {ts} |")
        return 0

    # Default: text format
    if args.class_name:
        print(tracker.print_class_summary(args.class_name))
        print()
        rows = tracker.get_function_table(args.class_name)
        for r in rows:
            print(f"  {r['address']}  {r['function']:40s}  {r['status']:4s}  ({r['rounds']} rounds)")
    else:
        print(tracker.print_summary())

    return 0
