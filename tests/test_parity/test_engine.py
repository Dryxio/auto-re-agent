"""Tests for the parity engine address-fallback logic."""
from __future__ import annotations

from pathlib import Path

from re_agent.config.schema import ParityConfig, ProjectProfile, ReAgentConfig
from re_agent.core.models import HookEntry, ParityStatus
from re_agent.parity.engine import run_parity


def _make_config(source_root: str) -> ReAgentConfig:
    profile = ProjectProfile(
        hook_patterns=[
            r"RH_ScopedInstall\s*\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+)",
        ],
        class_macro="RH_ScopedClass",
        source_root=source_root,
        source_extensions=[".cpp"],
        hooks_csv=None,
    )
    config = ReAgentConfig.create_default()
    config.project_profile = profile
    config.parity = ParityConfig(enabled=True)
    return config


def test_address_only_hook_resolves_via_hook_index(tmp_path: Path) -> None:
    """An address-only hook (empty class/fn) should resolve its source
    function body via the hook_address_index built from hook patterns."""
    src = tmp_path / "CTrain.cpp"
    src.write_text('''\
RH_ScopedClass(CTrain);
RH_ScopedInstall(ProcessControl, 0x6F86A0);

void CTrain::ProcessControl() {
    if (m_nStatus == 5) {
        DoStuff();
        MoreLogic();
        EvenMore();
    }
}
''')
    config = _make_config(str(tmp_path))

    # Simulate an address-only hook with no class/fn metadata
    hook = HookEntry(
        class_path="",
        fn_name="",
        address="0x6f86a0",
        reversed=True,
        locked=False,
        is_virtual=False,
    )

    results = run_parity([hook], tmp_path, config)
    assert len(results) == 1
    # Source should have been found (not RED for "missing source")
    assert results[0]["source"] is not None
    assert "DoStuff" in results[0]["source"].body


def test_address_only_hook_no_match_is_red(tmp_path: Path) -> None:
    """An address-only hook with no matching hook pattern should get RED."""
    src = tmp_path / "test.cpp"
    src.write_text("void Foo() { }\n")
    config = _make_config(str(tmp_path))

    hook = HookEntry(
        class_path="",
        fn_name="",
        address="0xDEAD",
        reversed=True,
        locked=False,
        is_virtual=False,
    )

    results = run_parity([hook], tmp_path, config)
    assert len(results) == 1
    assert results[0]["status"] == ParityStatus.RED
