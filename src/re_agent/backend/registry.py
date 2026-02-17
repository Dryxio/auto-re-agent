"""Backend factory — creates a backend from configuration."""
from __future__ import annotations

from re_agent.backend.protocol import REBackend
from re_agent.config.schema import BackendConfig


def create_backend(config: BackendConfig) -> REBackend:
    """Create an RE backend based on config.backend.type.

    Supported types:
        - ``"ghidra-bridge"`` (default): Shells out to a Ghidra CLI tool.
        - ``"stub"``: In-memory stub returning canned data (for testing).

    Raises:
        ValueError: If the backend type is not recognised.
    """
    backend_type = config.type.lower().replace("_", "-")

    if backend_type in ("ghidra-bridge", "ghidra"):
        from re_agent.backend.ghidra_bridge import GhidraBridgeBackend

        return GhidraBridgeBackend(
            cli_path=config.cli_path,
            timeout_s=config.timeout_s,
        )

    if backend_type == "stub":
        from re_agent.backend.stub import StubBackend

        return StubBackend()

    raise ValueError(
        f"Unknown backend type: {config.type!r}. "
        f"Supported: ghidra-bridge, stub"
    )
