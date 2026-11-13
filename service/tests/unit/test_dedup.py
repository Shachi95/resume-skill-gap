"""Tests for skill deduplication."""

from __future__ import annotations

from skillgap.config import AliasConfig
from skillgap.dedup import dedup_extracted_skills, dedup_gaps, merge_to_gap
from skillgap.models import Category, ExtractedSkill, Gap, Level
from skillgap.normalizer import build_lookup


def _skill(
    name: str,
    category: Category = Category.language,
    level: Level = Level.required,
    evidence: str = "some evidence",
) -> ExtractedSkill:
    return ExtractedSkill(name=name, category=category, level=level, evidence=evidence)


class TestDedupExtractedSkills:
    def test_groups_by_canonical(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        skills = [_skill("k8s"), _skill("kubernetes"), _skill("python")]
        groups = dedup_extracted_skills(skills, lookup)
        assert "kubernetes" in groups
        assert len(groups["kubernetes"]) == 2
        assert "python" in groups
        assert len(groups["python"]) == 1

    def test_unknown_grouped_by_raw(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        skills = [_skill("MyCustomTool"), _skill("mycustomtool")]
        groups = dedup_extracted_skills(skills, lookup)
        assert "mycustomtool" in groups
        assert len(groups["mycustomtool"]) == 2

    def test_empty(self, alias_config: AliasConfig) -> None:
        lookup = build_lookup(alias_config)
        groups = dedup_extracted_skills([], lookup)
        assert groups == {}


class TestMergeToGap:
    def test_multi_mention(self) -> None:
        mentions = [
            _skill("python", level=Level.required),
            _skill("python", level=Level.preferred),
            _skill("python", level=Level.required),
        ]
        gap = merge_to_gap("python", Category.language, mentions)
        assert gap.skill == "python"
        assert gap.posting_count == 3
        assert gap.required_count == 2
        assert gap.preferred_count == 1
        assert gap.score == 2.5  # 1.0 + 0.5 + 1.0

    def test_single_mention(self) -> None:
        mentions = [_skill("python", level=Level.unspecified)]
        gap = merge_to_gap("python", Category.language, mentions)
        assert gap.posting_count == 1
        assert gap.required_count == 0
        assert gap.preferred_count == 0
        assert gap.score == 0.75

    def test_all_unspecified(self) -> None:
        mentions = [
            _skill("python", level=Level.unspecified),
            _skill("python", level=Level.unspecified),
        ]
        gap = merge_to_gap("python", Category.language, mentions)
        assert gap.score == 1.5
        assert gap.required_count == 0
        assert gap.preferred_count == 0


class TestDedupGaps:
    def test_merges_same_skill(self) -> None:
        g1 = Gap(
            skill="python",
            category=Category.language,
            score=2.0,
            posting_count=2,
            required_count=2,
        )
        g2 = Gap(
            skill="python",
            category=Category.language,
            score=1.5,
            posting_count=2,
            required_count=1,
            preferred_count=1,
        )
        merged = dedup_gaps([g1, g2])
        assert len(merged) == 1
        assert merged[0].skill == "python"
        assert merged[0].score == 3.5
        assert merged[0].posting_count == 4
        assert merged[0].required_count == 3
        assert merged[0].preferred_count == 1

    def test_distinct_skills_unchanged(self) -> None:
        g1 = Gap(skill="python", category=Category.language, score=2.0, posting_count=2)
        g2 = Gap(skill="java", category=Category.language, score=1.0, posting_count=1)
        merged = dedup_gaps([g1, g2])
        assert len(merged) == 2

    def test_empty(self) -> None:
        assert dedup_gaps([]) == []
