"""Tests for config loader and data file validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from skillgap.config import AliasConfig, RolesConfig, load_config


class TestRealDataFiles:
    def test_load_config_succeeds(self) -> None:
        aliases, roles = load_config()
        assert len(aliases.skills) > 100
        assert len(roles.roles) == 3
        assert len(roles.precedence) == 3

    def test_aliases_all_have_category(self) -> None:
        aliases, _ = load_config()
        for name, entry in aliases.skills.items():
            assert entry.category, f"{name} has no category"

    def test_aliases_canonical_names_lowercase(self) -> None:
        aliases, _ = load_config()
        for name in aliases.skills:
            assert name == name.strip().lower(), f"'{name}' is not lowercase/stripped"

    def test_roles_patterns_nonempty(self) -> None:
        _, roles = load_config()
        for role, pattern in roles.roles.items():
            assert len(pattern.include) > 0, f"role {role} has no include patterns"


class TestBadAliases:
    def test_duplicate_alias(self, fixtures_dir: Path) -> None:
        import yaml

        raw = yaml.safe_load((fixtures_dir / "bad_alias_duplicate.yaml").read_text())
        with pytest.raises(ValueError, match=r"alias.*appears under both"):
            AliasConfig(skills=raw)

    def test_parent_cycle(self, fixtures_dir: Path) -> None:
        import yaml

        raw = yaml.safe_load((fixtures_dir / "bad_alias_cycle.yaml").read_text())
        with pytest.raises(ValueError, match="cycle"):
            AliasConfig(skills=raw)

    def test_missing_parent(self, fixtures_dir: Path) -> None:
        import yaml

        raw = yaml.safe_load((fixtures_dir / "bad_alias_missing_parent.yaml").read_text())
        with pytest.raises(ValueError, match="does not exist"):
            AliasConfig(skills=raw)

    def test_bad_category(self, fixtures_dir: Path) -> None:
        import yaml

        raw = yaml.safe_load((fixtures_dir / "bad_alias_bad_category.yaml").read_text())
        with pytest.raises(ValueError):
            AliasConfig(skills=raw)


class TestBadRoles:
    def test_bad_regex(self, fixtures_dir: Path) -> None:
        import yaml

        raw = yaml.safe_load((fixtures_dir / "bad_roles_bad_regex.yaml").read_text())
        with pytest.raises(ValueError, match="invalid regex"):
            RolesConfig(**raw)

    def test_bad_precedence(self, fixtures_dir: Path) -> None:
        import yaml

        raw = yaml.safe_load((fixtures_dir / "bad_roles_bad_precedence.yaml").read_text())
        with pytest.raises(ValueError, match="precedence"):
            RolesConfig(**raw)
