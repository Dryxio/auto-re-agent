"""Tests for source indexer."""
from __future__ import annotations

from pathlib import Path

from re_agent.config.schema import ProjectProfile
from re_agent.parity.source_indexer import SourceIndexer


def test_find_function_body(tmp_path: Path) -> None:
    src = tmp_path / "test.cpp"
    src.write_text('''
void CTrain::ProcessControl() {
    if (m_nStatus == 5) {
        DoStuff();
    }
}
''')
    indexer = SourceIndexer(tmp_path)
    match = indexer.find("CTrain", "ProcessControl")
    assert match is not None
    assert match.body_lines > 1
    assert match.call_count >= 1


def test_find_returns_none_for_missing(tmp_path: Path) -> None:
    src = tmp_path / "test.cpp"
    src.write_text("void Foo() { }")
    indexer = SourceIndexer(tmp_path)
    match = indexer.find("CTrain", "DoesNotExist")
    assert match is None


def test_stub_marker_detection(tmp_path: Path) -> None:
    src = tmp_path / "test.cpp"
    src.write_text('''
void CTrain::Shutdown() {
    NOTSA_UNREACHABLE();
}
''')
    indexer = SourceIndexer(tmp_path)
    match = indexer.find("CTrain", "Shutdown")
    assert match is not None
    assert match.has_stub_marker


def test_inline_forwarder_detection(tmp_path: Path) -> None:
    src = tmp_path / "test.cpp"
    src.write_text('''
void CTrain::UpdateSpeed() {
    return I_UpdateSpeed<false>();
}
''')
    indexer = SourceIndexer(tmp_path)
    match = indexer.find("CTrain", "UpdateSpeed")
    assert match is not None
    assert match.is_inline_internal_forwarder


# -- Empty fn_name guard tests ------------------------------------------------


def test_find_empty_fn_name_returns_none(tmp_path: Path) -> None:
    """find('', '') must NOT match arbitrary functions."""
    src = tmp_path / "test.cpp"
    src.write_text("void Foo() { return; }\n")
    indexer = SourceIndexer(tmp_path)
    assert indexer.find("", "") is None


def test_find_empty_fn_name_with_class_returns_none(tmp_path: Path) -> None:
    src = tmp_path / "test.cpp"
    src.write_text("void CTrain::Go() { }\n")
    indexer = SourceIndexer(tmp_path)
    assert indexer.find("CTrain", "") is None


# -- find_by_address with hook_patterns ----------------------------------------


def _make_profile(**overrides: object) -> ProjectProfile:
    defaults: dict[str, object] = {
        "hook_patterns": [
            r"RH_ScopedInstall\s*\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+)",
        ],
        "class_macro": "RH_ScopedClass",
        "source_root": ".",
        "source_extensions": [".cpp"],
        "hooks_csv": None,
        "stub_markers": ["NOTSA_UNREACHABLE"],
        "stub_call_prefix": "plugin::Call",
        "stub_patterns": [],
    }
    defaults.update(overrides)
    return ProjectProfile(**defaults)  # type: ignore[arg-type]


def test_find_by_address_resolves_via_hook_pattern(tmp_path: Path) -> None:
    src = tmp_path / "CTrain.cpp"
    src.write_text('''\
RH_ScopedClass(CTrain);
RH_ScopedInstall(ProcessControl, 0x6F86A0);
RH_ScopedInstall(Shutdown, 0x6F5900);

void CTrain::ProcessControl() {
    DoStuff();
}

void CTrain::Shutdown() {
    NOTSA_UNREACHABLE();
}
''')
    profile = _make_profile(source_root=str(tmp_path))
    indexer = SourceIndexer(tmp_path, profile)

    # Address lookup should work
    match = indexer.find_by_address("0x6f86a0")
    assert match is not None
    assert "DoStuff" in match.body

    # Another address
    match2 = indexer.find_by_address("0x6f5900")
    assert match2 is not None
    assert "NOTSA_UNREACHABLE" in match2.body


def test_find_by_address_unknown_returns_none(tmp_path: Path) -> None:
    src = tmp_path / "test.cpp"
    src.write_text("void Foo() { }\n")
    profile = _make_profile(source_root=str(tmp_path))
    indexer = SourceIndexer(tmp_path, profile)
    assert indexer.find_by_address("0xDEADBEEF") is None


def test_hook_address_index_extracts_class_name(tmp_path: Path) -> None:
    """Verify that _build_index reads RH_ScopedClass for class names."""
    src = tmp_path / "CTrain.cpp"
    src.write_text('''\
RH_ScopedClass(CTrain);
RH_ScopedInstall(ProcessControl, 0x6F86A0);

void CTrain::ProcessControl() {
    DoStuff();
}
''')
    profile = _make_profile(source_root=str(tmp_path))
    indexer = SourceIndexer(tmp_path, profile)
    entry = indexer.hook_address_index.get("0x6f86a0")
    assert entry is not None
    assert entry == ("CTrain", "ProcessControl")
