"""Pydantic models for the skill-gap analysis pipeline."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


class Role(StrEnum):
    software_engineer = "software_engineer"
    ai_engineer = "ai_engineer"
    fde = "fde"
    excluded = "excluded"


class Level(StrEnum):
    required = "required"
    preferred = "preferred"
    unspecified = "unspecified"


class Category(StrEnum):
    language = "language"
    framework = "framework"
    cloud_infra = "cloud_infra"
    data = "data"
    ai_ml = "ai_ml"
    practice = "practice"
    customer_facing = "customer_facing"
    soft_skill = "soft_skill"


class Posting(BaseModel, frozen=True):
    id: str
    role: Role | None = None
    title: str
    url: str | None = None
    posted_date: date | None = None
    text: str
    sections: dict[str, str] = {}

    @field_validator("title", "text")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or blank")
        return v


class ExtractedSkill(BaseModel, frozen=True):
    name: str
    category: Category
    level: Level
    evidence: str

    @field_validator("name", "evidence")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or blank")
        return v


class Skill(BaseModel, frozen=True):
    canonical_name: str
    category: Category
    ambiguous: bool = False

    @field_validator("canonical_name")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or blank")
        return v


class Resume(BaseModel, frozen=True):
    id: str
    text: str
    skills: tuple[ExtractedSkill, ...] = ()

    @field_validator("text")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or blank")
        return v


class Gap(BaseModel, frozen=True):
    skill: str
    category: Category
    score: float
    posting_count: int
    required_count: int = 0
    preferred_count: int = 0

    @field_validator("skill")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or blank")
        return v

    @field_validator("score")
    @classmethod
    def _nonnegative_score(cls, v: float) -> float:
        if v < 0:
            raise ValueError("score must be >= 0")
        return v

    @field_validator("posting_count")
    @classmethod
    def _positive_posting_count(cls, v: int) -> int:
        if v < 1:
            raise ValueError("posting_count must be >= 1")
        return v

    @field_validator("required_count", "preferred_count")
    @classmethod
    def _nonnegative_counts(cls, v: int) -> int:
        if v < 0:
            raise ValueError("count must be >= 0")
        return v

    @model_validator(mode="after")
    def _counts_le_posting_count(self) -> Gap:
        if self.required_count + self.preferred_count > self.posting_count:
            raise ValueError("required_count + preferred_count must be <= posting_count")
        return self


class RankedGap(BaseModel, frozen=True):
    rank: int
    gap: Gap

    @field_validator("rank")
    @classmethod
    def _positive_rank(cls, v: int) -> int:
        if v < 1:
            raise ValueError("rank must be >= 1")
        return v


class ExtractionResult(BaseModel, frozen=True):
    skills: tuple[ExtractedSkill, ...]


class AcceptedSkill(BaseModel, frozen=True):
    skill: ExtractedSkill
    canonical_name: str
    category: Category


class VerifyError(BaseModel, frozen=True):
    skill_name: str
    reason: Literal[
        "evidence_not_in_text",
        "skill_not_in_text",
        "too_few_skills",
        "too_many_skills",
    ]
    detail: str = ""


class VerifyReport(BaseModel, frozen=True):
    ok: bool
    accepted: tuple[AcceptedSkill, ...]
    candidates: tuple[ExtractedSkill, ...]
    errors: tuple[VerifyError, ...]


class VerifiedExtractionResult(BaseModel, frozen=True):
    skills: tuple[AcceptedSkill, ...]
    source: Literal["llm", "fallback"]
    candidates: tuple[ExtractedSkill, ...] = ()
    errors: tuple[VerifyError, ...] = ()
    attempts: int = 1
