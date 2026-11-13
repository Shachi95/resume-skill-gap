"""Fixtures for unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillgap.config import AliasConfig, RolesConfig, load_config

_FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture()
def fixtures_dir() -> Path:
    return _FIXTURES


@pytest.fixture()
def alias_config() -> AliasConfig:
    aliases, _ = load_config()
    return aliases


@pytest.fixture()
def roles_config() -> RolesConfig:
    _, roles = load_config()
    return roles
