"""Tests for LLM-enhanced deep scoring (with a fake backend)."""

import pytest

from skillens.core.models import ResourceMeta, SourceType, Verdict
from skillens.core.scorer import score_resource_deep
from skillens.llm.base import LLMAnalysis, LLMBackend


class FakeBackend(LLMBackend):
    @property
    def name(self) -> str:
        return "fake:v1"

    async def analyze(self, prompt: str) -> LLMAnalysis:
        return LLMAnalysis(
            market_demand=90,
            info_density=85,
            freshness=95,
            effort_vs_return=80,
            strengths=["clear", "practical", "fresh"],
            concerns=["pricey"],
            alternatives=["alt one", "alt two"],
            verdict_reason="Excellent fit.",
        )


class FailingBackend(LLMBackend):
    @property
    def name(self) -> str:
        return "fail"

    async def analyze(self, prompt: str) -> LLMAnalysis:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_deep_scoring_uses_llm_scores():
    meta = ResourceMeta(title="Test", source_type=SourceType.COURSE, platform="x")
    result = await score_resource_deep(meta, backend=FakeBackend())

    assert result.analysis_mode == "deep"
    assert result.model_used == "fake:v1"
    assert result.market_demand == 90
    assert result.info_density == 85
    assert result.freshness == 95
    assert result.effort_vs_return == 80
    assert result.verdict_reason == "Excellent fit."
    assert result.verdict == Verdict.LEARN
    assert "clear" in result.strengths


@pytest.mark.asyncio
async def test_deep_scoring_falls_back_when_llm_fails():
    meta = ResourceMeta(title="Test", source_type=SourceType.COURSE, platform="x")
    result = await score_resource_deep(meta, backend=FailingBackend())

    assert result.analysis_mode == "deep"
    assert any("LLM analysis failed" in c for c in result.concerns)


@pytest.mark.asyncio
async def test_deep_scoring_without_backend_returns_quick():
    meta = ResourceMeta(title="Test", source_type=SourceType.COURSE, platform="x")
    result = await score_resource_deep(meta, backend=None)
    assert result.analysis_mode == "deep"
    assert result.model_used is None
