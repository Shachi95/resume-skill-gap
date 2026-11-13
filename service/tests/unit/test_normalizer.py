"""Tests for the skill normalizer."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from skillgap.config import AliasConfig, load_config
from skillgap.models import Category
from skillgap.normalizer import build_lookup, get_parents, normalize, normalize_batch


def _config() -> AliasConfig:
    aliases, _ = load_config()
    return aliases


class TestBuildLookup:
    def test_contains_all_canonical_names(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        for name in alias_config.skills:
            assert name in lookup
            assert lookup[name] == name

    def test_contains_all_aliases(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        for name, entry in alias_config.skills.items():
            for alias in entry.aliases:
                assert alias in lookup
                assert lookup[alias] == name

    def test_total_size(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        expected = len(alias_config.skills)
        for entry in alias_config.skills.values():
            expected += len(entry.aliases)
        assert len(lookup) == expected


class TestNormalize:
    def test_canonical_name(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("python", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "python"
        assert result.category == Category.language

    def test_alias(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("k8s", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "kubernetes"

    def test_case_insensitive(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("PyThOn", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "python"

    def test_strips_whitespace(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("  python  ", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "python"

    def test_unknown_returns_none(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("made_up_skill_xyz", lookup, alias_config)
        assert result is None

    def test_ambiguous_flag(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("go", lookup, alias_config)
        assert result is not None
        assert result.ambiguous is True

    def test_non_ambiguous_flag(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("python", lookup, alias_config)
        assert result is not None
        assert result.ambiguous is False

    def test_version_stripping_major(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("Java 17", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "java"

    def test_version_stripping_semver(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("Python 3.12", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "python"

    def test_version_stripping_x(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("Node 18.x", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "node_js"

    def test_version_stripping_no_false_positive(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        result = normalize("Go", lookup, alias_config)
        assert result is not None
        assert result.canonical_name == "go"

    def test_unmatched_logged(
        self, alias_config: AliasConfig, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging

        lookup = build_lookup(alias_config)
        with caplog.at_level(logging.DEBUG, logger="skillgap.normalizer"):
            normalize("nonexistent_xyz", lookup, alias_config)
        assert any("unmatched" in r.message for r in caplog.records)


class TestGetParents:
    def test_single_parent(self, alias_config: AliasConfig) -> None:
        parents = get_parents("lambda", alias_config)
        assert len(parents) == 1
        assert parents[0].canonical_name == "aws"

    def test_no_parent(self, alias_config: AliasConfig) -> None:
        parents = get_parents("python", alias_config)
        assert parents == []

    def test_unknown_skill(self, alias_config: AliasConfig) -> None:
        parents = get_parents("nonexistent_xyz", alias_config)
        assert parents == []

    def test_cloudformation_parent(self, alias_config: AliasConfig) -> None:
        parents = get_parents("cloudformation", alias_config)
        assert len(parents) >= 1
        assert parents[0].canonical_name == "aws"


class TestNormalizeBatch:
    def test_batch(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        results = normalize_batch(["python", "k8s", "nonexistent"], lookup, alias_config)
        assert len(results) == 3
        assert results[0] is not None and results[0].canonical_name == "python"
        assert results[1] is not None and results[1].canonical_name == "kubernetes"
        assert results[2] is None


_config_for_hypothesis = _config()
_lookup_for_hypothesis = build_lookup(_config_for_hypothesis)
_all_canonical = list(_config_for_hypothesis.skills.keys())
_all_aliases: list[str] = []
for _name, _entry in _config_for_hypothesis.skills.items():
    _all_aliases.extend(_entry.aliases)


@given(name=st.sampled_from(_all_canonical))
def test_normalize_idempotent(name: str) -> None:
    result = normalize(name, _lookup_for_hypothesis, _config_for_hypothesis)
    assert result is not None
    result2 = normalize(result.canonical_name, _lookup_for_hypothesis, _config_for_hypothesis)
    assert result2 is not None
    assert result == result2


@given(alias=st.sampled_from(_all_aliases) if _all_aliases else st.nothing())
def test_every_alias_resolves(alias: str) -> None:
    result = normalize(alias, _lookup_for_hypothesis, _config_for_hypothesis)
    assert result is not None
