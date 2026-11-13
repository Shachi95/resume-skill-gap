"""Deduplicate extracted skills by canonical name."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from skillgap.models import Category, ExtractedSkill, Gap, Level
from skillgap.ranking import WEIGHTS


def dedup_extracted_skills(
    skills: Sequence[ExtractedSkill],
    lookup: dict[str, str],
) -> dict[str, list[ExtractedSkill]]:
    """Group extracted skills by canonical name.

    Unknown skills are grouped under their lowercased raw name.
    """
    groups: dict[str, list[ExtractedSkill]] = defaultdict(list)
    for skill in skills:
        key = lookup.get(skill.name.strip().lower(), skill.name.strip().lower())
        groups[key].append(skill)
    return dict(groups)


def merge_to_gap(
    canonical_name: str,
    category: Category,
    mentions: Sequence[ExtractedSkill],
) -> Gap:
    """Merge multiple mentions of the same skill into a single Gap."""
    required_count = sum(1 for m in mentions if m.level == Level.required)
    preferred_count = sum(1 for m in mentions if m.level == Level.preferred)
    total_score = sum(WEIGHTS[m.level] for m in mentions)
    return Gap(
        skill=canonical_name,
        category=category,
        score=total_score,
        posting_count=len(mentions),
        required_count=required_count,
        preferred_count=preferred_count,
    )


def dedup_gaps(gaps: Sequence[Gap]) -> list[Gap]:
    """Merge Gap entries that share the same skill name."""
    merged: dict[str, Gap] = {}
    for gap in gaps:
        if gap.skill in merged:
            existing = merged[gap.skill]
            merged[gap.skill] = Gap(
                skill=gap.skill,
                category=gap.category,
                score=existing.score + gap.score,
                posting_count=existing.posting_count + gap.posting_count,
                required_count=existing.required_count + gap.required_count,
                preferred_count=existing.preferred_count + gap.preferred_count,
            )
        else:
            merged[gap.skill] = gap
    return list(merged.values())
