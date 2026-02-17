"""Stub backend for testing without a real Ghidra instance."""
from __future__ import annotations

from re_agent.backend.protocol import BackendCapabilities
from re_agent.core.models import (
    AsmResult,
    DecompileResult,
    EnumDef,
    FunctionEntry,
    StructDef,
    XRef,
)

_CANNED_DECOMPILE = """\
// Decompiled by stub backend
void __fastcall CStub::StubFunction(CStub *this) {
    // stub body
    return;
}
// Callers: 2 | Callees: 0
"""


class StubBackend:
    """In-memory stub backend that returns canned data.

    Useful for testing the agent loop, prompt construction, and
    orchestration logic without requiring a live Ghidra instance.
    """

    def __init__(
        self,
        remaining_functions: list[FunctionEntry] | None = None,
    ) -> None:
        self._caps = BackendCapabilities(
            has_decompile=True,
            has_asm=True,
            has_structs=True,
            has_xrefs=True,
            has_search=True,
            has_enums=True,
        )
        self._remaining = remaining_functions or []

    @property
    def capabilities(self) -> BackendCapabilities:
        return self._caps

    def decompile(self, target: str) -> DecompileResult:
        return DecompileResult(
            address=target,
            name="CStub::StubFunction",
            signature="void __fastcall CStub::StubFunction(CStub *this)",
            decompiled=_CANNED_DECOMPILE,
            raw_output=_CANNED_DECOMPILE,
            callers=2,
            callees=0,
        )

    def xrefs_to(self, target: str) -> list[XRef]:
        return []

    def xrefs_from(self, target: str) -> list[XRef]:
        return []

    def get_struct(self, name: str) -> StructDef | None:
        return None

    def get_enum(self, name: str) -> EnumDef | None:
        return None

    def get_asm(self, target: str) -> AsmResult | None:
        return None

    def search(self, pattern: str) -> list[FunctionEntry]:
        return []

    def unimplemented(self, filter_pattern: str | None = None) -> list[FunctionEntry]:
        return []

    def remaining(self, class_name: str | None = None) -> list[FunctionEntry]:
        if class_name is None:
            return list(self._remaining)
        return [f for f in self._remaining if f.class_name == class_name]
