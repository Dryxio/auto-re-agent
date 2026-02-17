"""Tests for individual parity signals."""
from __future__ import annotations

from re_agent.core.models import GhidraData, SourceMatch
from re_agent.parity.signals import (
    check_call_count_mismatch,
    check_fp_sensitivity,
    check_inline_wrapper,
    check_large_asm_tiny_source,
    check_missing_source,
    check_short_body,
    check_stub_markers,
    check_trivial_stub,
)


def _make_source(**kwargs: object) -> SourceMatch:
    defaults = dict(
        path="test.cpp", line=1, body="{ code; }", body_no_comments="{ code; }",
        body_lines=10, call_count=5, plugin_call_count=0, non_plugin_call_count=5,
        control_flow_count=3, has_stub_marker=False, has_fp_token=False,
        is_inline_internal_forwarder=False,
    )
    defaults.update(kwargs)
    return SourceMatch(**defaults)  # type: ignore[arg-type]


def _make_ghidra(**kwargs: object) -> GhidraData:
    defaults = dict(
        decompile_ok=True, asm_ok=True,
        asm_instruction_count=50, asm_call_count=5,
        asm_has_fp_sensitive=False, callees=5,
    )
    defaults.update(kwargs)
    return GhidraData(**defaults)  # type: ignore[arg-type]


def test_missing_source() -> None:
    f = check_missing_source(source=None)
    assert f is not None
    assert f.level == "red"


def test_source_present() -> None:
    f = check_missing_source(source=_make_source())
    assert f is None


def test_stub_marker_detected() -> None:
    f = check_stub_markers(source=_make_source(has_stub_marker=True))
    assert f is not None
    assert f.level == "red"


def test_no_stub_marker() -> None:
    f = check_stub_markers(source=_make_source(has_stub_marker=False))
    assert f is None


def test_trivial_stub() -> None:
    src = _make_source(plugin_call_count=2, non_plugin_call_count=0, body_lines=5, control_flow_count=0)
    f = check_trivial_stub(source=src)
    assert f is not None
    assert f.level == "red"


def test_short_body() -> None:
    f = check_short_body(source=_make_source(body_lines=3))
    assert f is not None
    assert f.level == "yellow"


def test_short_body_inline_skip() -> None:
    f = check_short_body(source=_make_source(body_lines=3), inline_skip=True)
    assert f is None


def test_large_asm_tiny_source() -> None:
    src = _make_source(body_lines=5)
    ghidra = _make_ghidra(asm_instruction_count=100)
    f = check_large_asm_tiny_source(source=src, ghidra=ghidra)
    assert f is not None
    assert f.level == "red"


def test_fp_sensitivity() -> None:
    src = _make_source(has_fp_token=False)
    ghidra = _make_ghidra(asm_has_fp_sensitive=True)
    f = check_fp_sensitivity(source=src, ghidra=ghidra)
    assert f is not None
    assert f.level == "yellow"


def test_call_count_mismatch() -> None:
    src = _make_source(call_count=2)
    ghidra = _make_ghidra(asm_call_count=8)
    f = check_call_count_mismatch(source=src, ghidra=ghidra, call_count_warn_diff=3)
    assert f is not None
    assert f.level == "yellow"


def test_call_count_within_threshold() -> None:
    src = _make_source(call_count=5)
    ghidra = _make_ghidra(asm_call_count=7)
    f = check_call_count_mismatch(source=src, ghidra=ghidra, call_count_warn_diff=3)
    assert f is None


def test_inline_wrapper() -> None:
    src = _make_source(is_inline_internal_forwarder=True)
    f = check_inline_wrapper(source=src)
    assert f is not None
    assert f.level == "info"
