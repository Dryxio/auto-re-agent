"""Progress tracking wrapper around Session."""
from __future__ import annotations

from re_agent.core.session import Session


class ProgressTracker:
    """Wraps Session with formatted output methods."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def print_summary(self) -> str:
        summary = self.session.get_summary()
        lines = [
            "re-agent Progress Summary",
            "=" * 40,
            f"Total functions:  {summary['total_functions']}",
            f"Passed:           {summary['passed']}",
            f"Failed:           {summary['failed']}",
            f"Classes touched:  {summary['classes_touched']}",
        ]
        return "\n".join(lines)

    def print_class_summary(self, class_name: str) -> str:
        summary = self.session.get_class_summary(class_name)
        lines = [
            f"Class: {class_name}",
            "-" * 40,
            f"Total:  {summary['total']}",
            f"Passed: {summary['passed']}",
            f"Failed: {summary['failed']}",
        ]
        return "\n".join(lines)

    def get_function_table(self, class_name: str | None = None) -> list[dict[str, str]]:
        funcs = self.session.get_all_functions()
        if class_name:
            funcs = [f for f in funcs if f.get("class_name") == class_name]
        rows = []
        for f in funcs:
            rows.append({
                "address": f.get("address", ""),
                "class": f.get("class_name", ""),
                "function": f.get("function_name", ""),
                "status": "PASS" if f.get("success") else "FAIL",
                "rounds": str(f.get("rounds_used", "")),
                "timestamp": f.get("timestamp", ""),
            })
        return rows
