"""Shared fixtures for re-agent tests."""
from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_config_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_config.yaml"


@pytest.fixture
def sample_source_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_source.cpp"


@pytest.fixture
def sample_hooks_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_hooks.csv"
