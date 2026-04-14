"""Core data models for SkiLens."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    COURSE = "course"
    VIDEO = "video"
    PAPER = "paper"
    REPO = "repo"
    BOOK = "book"
    ARTICLE = "article"
    UNKNOWN = "unknown"


class Verdict(str, Enum):
    LEARN = "LEARN"
    SKIP = "SKIP"
    CONSIDER_ALTERNATIVES = "CONSIDER_ALTERNATIVES"


class ResourceMeta(BaseModel):
    """Metadata extracted from a learning resource by a provider."""

    title: str
    url: str | None = None
    source_type: SourceType = SourceType.UNKNOWN
    platform: str = "unknown"

    # Content signals
    description: str = ""
    syllabus: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    language: str = "en"

    # Quality signals
    rating: float | None = None
    review_count: int | None = None
    enrollment_count: int | None = None
    star_count: int | None = None
    citation_count: int | None = None

    # Time signals
    published_date: datetime | None = None
    last_updated: datetime | None = None
    duration_hours: float | None = None

    # Author signals
    author: str = ""
    author_credentials: str = ""
    institution: str = ""

    # Content sample for LLM analysis (truncated to ~2000 chars)
    content_sample: str = ""


class AlternativeResource(BaseModel):
    """A discovered alternative resource with comparison score."""

    title: str
    url: str
    platform: str
    overall_score: int = Field(ge=0, le=100)
    score_delta: int  # positive = better than input
    reason: str  # one-line why it's better/worse


class Assessment(BaseModel):
    """Evaluation result for a learning resource."""

    # Scores (0-100)
    market_demand: int = Field(ge=0, le=100)
    skill_half_life: str = "unknown"  # "~6 months", "~2 years", "~10 years"
    info_density: int = Field(ge=0, le=100)
    freshness: int = Field(ge=0, le=100)
    effort_vs_return: int = Field(ge=0, le=100)
    profile_match: int | None = None

    # Overall
    overall_score: int = Field(ge=0, le=100)
    verdict: Verdict
    verdict_reason: str

    # Details
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)  # Simple text suggestions

    # ★ Discovered & scored alternatives
    discovered_alternatives: list[AlternativeResource] = Field(default_factory=list)

    # Meta
    resource: ResourceMeta
    analysis_mode: str = "quick"  # "quick" | "deep"
    model_used: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class UserProfile(BaseModel):
    """User's background for personalized scoring."""

    github_username: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    target_role: str | None = None
    resume_text: str | None = None
