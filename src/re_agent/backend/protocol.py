"""Reverse-engineering backend protocol definition."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from re_agent.core.models import (
    AsmResult,
    DecompileResult,
    EnumDef,
    FunctionEntry,
    StructDef,
    XRef,
)


@dataclass
class BackendCapabilities:
    """Declares which operations a backend supports.

    Agents can inspect this before issuing commands to avoid unsupported
    calls that would raise errors.
    """

    has_decompile: bool = True
    has_asm: bool = False
    has_structs: bool = False
    has_xrefs: bool = True
    has_search: bool = True
    has_enums: bool = False


@runtime_checkable
class REBackend(Protocol):
    """Protocol for reverse-engineering tool backends.

    Each method corresponds to a capability in :class:`BackendCapabilities`.
    Implementations that do not support a given operation should raise
    :class:`NotImplementedError`.
    """

    @property
    def capabilities(self) -> BackendCapabilities:
        """Return the set of capabilities this backend supports."""
        ...

    def decompile(self, target: str) -> DecompileResult:
        """Decompile a function by address or name.

        Args:
            target: A hex address (e.g. ``"0x5E3E90"``) or symbol name.

        Returns:
            Parsed decompilation result.
        """
        ...

    def xrefs_to(self, target: str) -> list[XRef]:
        """Return cross-references *to* the given target."""
        ...

    def xrefs_from(self, target: str) -> list[XRef]:
        """Return cross-references *from* the given target."""
        ...

    def get_struct(self, name: str) -> StructDef | None:
        """Retrieve a struct definition by name, or ``None`` if not found."""
        ...

    def get_enum(self, name: str) -> EnumDef | None:
        """Retrieve an enum definition by name, or ``None`` if not found."""
        ...

    def get_asm(self, target: str) -> AsmResult | None:
        """Retrieve disassembly for a function, or ``None`` if unavailable."""
        ...

    def search(self, pattern: str) -> list[FunctionEntry]:
        """Search for functions matching a pattern."""
        ...

    def unimplemented(self, filter_pattern: str | None = None) -> list[FunctionEntry]:
        """List functions that are not yet implemented.

        Args:
            filter_pattern: Optional glob or regex pattern to narrow results.
        """
        ...

    def remaining(self, class_name: str | None = None) -> list[FunctionEntry]:
        """List remaining stub functions, optionally filtered by class.

        Args:
            class_name: If provided, restrict to this class.
        """
        ...
