"""Tests for persistent function evidence graph."""
from __future__ import annotations

import json
from pathlib import Path

from re_agent.core.knowledge_graph import KnowledgeGraph


def test_ingest_context_builds_function_edges(tmp_path: Path) -> None:
    graph = KnowledgeGraph(tmp_path / "graph.json")
    graph.ingest_context(json.dumps({
        "kind": "function-context",
        "target": "0x100",
        "function": {
            "address": "0x100",
            "name": "Root",
            "callees": [{"addr": "0x200", "name": "Child"}],
        },
        "strings": [{"address": "0x300", "value": "hello"}],
        "globals": [{"address": "0x400", "name": "gValue"}],
    }))

    neighborhood = graph.neighborhood("0x100")
    assert "function:00000200" in neighborhood
    assert "string:0x300" in neighborhood
    assert "global:0x400" in neighborhood
    assert (tmp_path / "graph.json").exists()
