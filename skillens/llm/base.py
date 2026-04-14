"""Abstract LLM interface for deep analysis."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class LLMAnalysis(BaseModel):
    """Structured deep-analysis result from an LLM."""

    market_demand: int = Field(ge=0, le=100)
    info_density: int = Field(ge=0, le=100)
    freshness: int = Field(ge=0, le=100)
    effort_vs_return: int = Field(ge=0, le=100)
    strengths: list[str]
    concerns: list[str]
    alternatives: list[str]
    verdict_reason: str


class LLMBackend(ABC):
    """Abstract LLM backend."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def analyze(self, prompt: str) -> LLMAnalysis:
        """Send prompt, return structured analysis."""
