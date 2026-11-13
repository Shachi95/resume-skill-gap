"""Grounding validator: ensure evidence phrases exist in source text."""

from __future__ import annotations

from difflib import SequenceMatcher

from skillgap.models import ExtractedSkill

_FUZZY_THRESHOLD = 0.85


def _is_grounded(evidence: str, source: str, threshold: float) -> bool:
    evidence_lower = evidence.strip().lower()
    source_lower = source.lower()

    if evidence_lower in source_lower:
        return True

    for line in source_lower.splitlines():
        line = line.strip()
        if not line:
            continue
        ratio = SequenceMatcher(None, evidence_lower, line).ratio()
        if ratio >= threshold:
            return True

    return False


def validate_grounding(
    skills: list[ExtractedSkill],
    source_text: str,
    *,
    threshold: float = _FUZZY_THRESHOLD,
) -> list[ExtractedSkill]:
    """Return only skills whose evidence is found in the source text.

    Uses case-insensitive substring matching first, then falls back
    to fuzzy line-level matching with SequenceMatcher.
    """
    return [s for s in skills if _is_grounded(s.evidence, source_text, threshold)]
