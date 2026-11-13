"""Tests for the category classifier."""

from __future__ import annotations

from skillgap.classifier import classify, classify_role, is_ambiguous, validate_category
from skillgap.config import AliasConfig, RolesConfig
from skillgap.models import Category, Role


class TestClassify:
    def test_known_skill(self, alias_config: AliasConfig) -> None:
        assert classify("python", alias_config) == Category.language

    def test_unknown_skill(self, alias_config: AliasConfig) -> None:
        assert classify("made_up_skill_xyz", alias_config) is None

    def test_cloud_infra(self, alias_config: AliasConfig) -> None:
        assert classify("kubernetes", alias_config) == Category.cloud_infra


class TestIsAmbiguous:
    def test_ambiguous_true(self, alias_config: AliasConfig) -> None:
        assert is_ambiguous("go", alias_config) is True

    def test_ambiguous_false(self, alias_config: AliasConfig) -> None:
        assert is_ambiguous("python", alias_config) is False

    def test_unknown_not_ambiguous(self, alias_config: AliasConfig) -> None:
        assert is_ambiguous("nonexistent", alias_config) is False


class TestValidateCategory:
    def test_match(self, alias_config: AliasConfig) -> None:
        assert validate_category("python", Category.language, alias_config) is True

    def test_mismatch(self, alias_config: AliasConfig) -> None:
        assert validate_category("python", Category.framework, alias_config) is False

    def test_unknown_skill_passes(self, alias_config: AliasConfig) -> None:
        assert validate_category("unknown_xyz", Category.language, alias_config) is True


class TestClassifyRole:
    def test_swe(self, roles_config: RolesConfig) -> None:
        assert classify_role("Senior Backend Engineer", roles_config) == Role.software_engineer

    def test_ai_engineer(self, roles_config: RolesConfig) -> None:
        assert classify_role("Senior ML Engineer", roles_config) == Role.ai_engineer

    def test_fde(self, roles_config: RolesConfig) -> None:
        assert classify_role("Forward Deployed Engineer", roles_config) == Role.fde

    def test_fde_solutions(self, roles_config: RolesConfig) -> None:
        assert classify_role("Solutions Engineer", roles_config) == Role.fde

    def test_excluded_manager(self, roles_config: RolesConfig) -> None:
        assert classify_role("Engineering Manager", roles_config) == Role.excluded

    def test_excluded_intern(self, roles_config: RolesConfig) -> None:
        assert classify_role("Software Engineering Intern", roles_config) == Role.excluded

    def test_unknown_title(self, roles_config: RolesConfig) -> None:
        assert classify_role("Chief Happiness Officer", roles_config) == Role.excluded

    def test_fde_sw_eng_matches_swe(self, roles_config: RolesConfig) -> None:
        result = classify_role("Forward Deployed Software Engineer", roles_config)
        assert result == Role.software_engineer
