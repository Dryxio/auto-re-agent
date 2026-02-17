"""Disk cache for Ghidra decompile/ASM/refs data."""
from __future__ import annotations

from pathlib import Path

from re_agent.utils.address import normalize_address


class ParityCache:
    """Simple file-based cache keyed by normalized address."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, prefix: str, address: str) -> Path:
        key = normalize_address(address)
        return self.cache_dir / f"{prefix}-{key}.txt"

    def get(self, prefix: str, address: str) -> str | None:
        p = self._path(prefix, address)
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")
        return None

    def put(self, prefix: str, address: str, content: str) -> None:
        p = self._path(prefix, address)
        p.write_text(content, encoding="utf-8")

    def has(self, prefix: str, address: str) -> bool:
        return self._path(prefix, address).exists()

    def clear(self) -> None:
        for f in self.cache_dir.iterdir():
            if f.is_file():
                f.unlink()
