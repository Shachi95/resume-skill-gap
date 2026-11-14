"""Deterministic verification of extracted skills."""

from __future__ import annotations

from skillgap.config import AliasConfig
from skillgap.grounding import _is_grounded
from skillgap.models import (
    AcceptedSkill,
    ExtractedSkill,
    ExtractionResult,
    Level,
    VerifyError,
    VerifyReport,
)
from skillgap.normalizer import normalize

MIN_SKILLS = 3
MAX_SKILLS = 40

_LEVEL_RANK: dict[Level, int] = {
    Level.required: 2,
    Level.unspecified: 1,
    Level.preferred: 0,
}


def verify(
    text: str,
    result: ExtractionResult,
    lookup: dict[str, str],
    config: AliasConfig,
    *,
    grounding_threshold: float = 0.85,
) -> VerifyReport:
    """Ground, normalize, deduplicate and bounds-check an extraction result."""
    lowered = text.lower()
    errors: list[VerifyError] = []
    candidates: list[ExtractedSkill] = []
    accepted: dict[str, AcceptedSkill] = {}

    for skill in result.skills:
        if not _is_grounded(skill.evidence, text, grounding_threshold):
            errors.append(
                VerifyError(
                    skill_name=skill.name,
                    reason="evidence_not_in_text",
                    detail=f"evidence {skill.evidence!r} not found in text",
                )
            )
            continue

        resolved = normalize(skill.name, lookup, config)
        names = {skill.name.strip().lower()}
        if resolved is not None:
            names.add(resolved.canonical_name)
            names.update(config.skills[resolved.canonical_name].aliases)
        if not any(n and n in lowered for n in names):
            errors.append(
                VerifyError(
                    skill_name=skill.name,
                    reason="skill_not_in_text",
                    detail=f"neither {skill.name!r} nor its aliases appear in text",
                )
            )
            continue

        if resolved is None:
            candidates.append(skill)
            continue

        entry = AcceptedSkill(
            skill=skill, canonical_name=resolved.canonical_name, category=resolved.category
        )
        existing = accepted.get(resolved.canonical_name)
        if existing is None or _LEVEL_RANK[skill.level] > _LEVEL_RANK[existing.skill.level]:
            accepted[resolved.canonical_name] = entry

    if len(accepted) < MIN_SKILLS:
        errors.append(
            VerifyError(
                skill_name="",
                reason="too_few_skills",
                detail=f"{len(accepted)} accepted, need at least {MIN_SKILLS}",
            )
        )
    elif len(accepted) > MAX_SKILLS:
        errors.append(
            VerifyError(
                skill_name="",
                reason="too_many_skills",
                detail=f"{len(accepted)} accepted, at most {MAX_SKILLS} allowed",
            )
        )

    return VerifyReport(
        ok=len(errors) == 0 and MIN_SKILLS <= len(accepted) <= MAX_SKILLS,
        accepted=tuple(accepted.values()),
        candidates=tuple(candidates),
        errors=tuple(errors),
    )
