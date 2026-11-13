"""Deterministic skill-gap analysis pipeline for tech roles."""

from skillgap.classifier import classify, classify_role, is_ambiguous, validate_category
from skillgap.dedup import dedup_extracted_skills, dedup_gaps, merge_to_gap
from skillgap.extractor import (
    NonRetryableExtractionError,
    RetryableExtractionError,
    extract_posting_skills,
    extract_resume_skills,
    parse_extraction_response,
)
from skillgap.grounding import validate_grounding
from skillgap.models import (
    Category,
    ExtractedSkill,
    Gap,
    Level,
    Posting,
    RankedGap,
    Resume,
    Role,
    Skill,
)
from skillgap.normalizer import build_lookup, get_parents, normalize, normalize_batch
from skillgap.ranking import WEIGHTS, rank_gaps, score_gap

__all__ = [
    "WEIGHTS",
    "Category",
    "ExtractedSkill",
    "Gap",
    "Level",
    "NonRetryableExtractionError",
    "Posting",
    "RankedGap",
    "Resume",
    "RetryableExtractionError",
    "Role",
    "Skill",
    "build_lookup",
    "classify",
    "classify_role",
    "dedup_extracted_skills",
    "dedup_gaps",
    "extract_posting_skills",
    "extract_resume_skills",
    "get_parents",
    "is_ambiguous",
    "merge_to_gap",
    "normalize",
    "normalize_batch",
    "parse_extraction_response",
    "rank_gaps",
    "score_gap",
    "validate_category",
    "validate_grounding",
]
