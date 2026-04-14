"""Tests for the 0.2.0 confidence-weighted scoring behavior."""

from datetime import datetime, timedelta, timezone

import pytest

from skillens.core.models import ResourceMeta, SourceType, Verdict
from skillens.core.scorer import (
    _score_freshness,
    _score_info_density,
    _score_market_demand,
    score_resource,
)


def _make_meta(**kw) -> ResourceMeta:
    defaults = {"title": "Test", "source_type": SourceType.COURSE, "platform": "x"}
    defaults.update(kw)
    return ResourceMeta(**defaults)


class TestNoSilentDefaults:
    """A resource with zero metadata must be marked low-confidence,
    not silently scored as 'average'."""

    def test_empty_meta_gets_low_overall_confidence(self):
        meta = _make_meta()  # nothing at all
        result = score_resource(meta)
        assert result.overall_confidence < 0.35

    def test_empty_meta_produces_insufficient_data_verdict(self):
        meta = _make_meta()
        result = score_resource(meta)
        assert result.verdict == Verdict.CONSIDER_ALTERNATIVES
        assert "insufficient" in result.verdict_reason.lower()

    def test_empty_meta_concerns_include_data_warning(self):
        meta = _make_meta()
        result = score_resource(meta)
        assert any("metadata" in c.lower() for c in result.concerns)

    def test_per_dimension_confidence_is_reported(self):
        meta = _make_meta()
        result = score_resource(meta)
        for dim in ("market_demand", "info_density", "freshness", "effort_vs_return"):
            assert dim in result.confidences
            assert 0.0 <= result.confidences[dim] <= 1.0

    def test_rich_meta_gets_high_confidence(self):
        meta = _make_meta(
            title="Deep Learning with PyTorch",
            topics=["pytorch", "deep learning", "neural network"],
            last_updated=datetime.now(timezone.utc) - timedelta(days=30),
            duration_hours=20,
            rating=4.8,
            syllabus=[f"Module {i}" for i in range(12)],
            enrollment_count=50_000,
        )
        result = score_resource(meta)
        assert result.overall_confidence >= 0.7


class TestMarketDemandSignal:
    def test_dataset_hit_high_confidence(self):
        meta = _make_meta(topics=["machine learning"])
        signal = _score_market_demand(meta)
        assert signal.confidence >= 0.85
        assert signal.source.startswith("dataset")
        assert signal.score >= 85

    def test_blend_when_both_present(self):
        meta = _make_meta(topics=["llm"], enrollment_count=200_000)
        signal = _score_market_demand(meta)
        assert signal.confidence == 1.0
        assert signal.source == "dataset+popularity"

    def test_popularity_only_medium_confidence(self):
        meta = _make_meta(enrollment_count=200_000)
        signal = _score_market_demand(meta)
        assert 0.6 <= signal.confidence <= 0.75
        assert signal.source == "popularity"

    def test_default_is_explicitly_low_confidence(self):
        meta = _make_meta()
        signal = _score_market_demand(meta)
        assert signal.source == "default"
        assert signal.confidence < 0.15


class TestExponentialFreshness:
    """Freshness decays exponentially with topic-dependent half-life."""

    def test_fresh_content_scores_near_100(self):
        meta = _make_meta(
            topics=["python"],  # 2555d halflife
            last_updated=datetime.now(timezone.utc),
        )
        signal = _score_freshness(meta)
        assert signal.score >= 95

    def test_stable_topic_ages_slowly(self):
        # A Python course from 2 years ago should still be fresh
        # (halflife ~7y → age 2y → 0.5^(2/7) ≈ 0.82 → ~82)
        meta = _make_meta(
            topics=["python"],
            last_updated=datetime.now(timezone.utc) - timedelta(days=730),
        )
        signal = _score_freshness(meta)
        assert signal.score >= 75

    def test_fast_moving_topic_ages_fast(self):
        # A LangChain course from 2 years ago should be very stale
        # (halflife ~180d → age 730d → 0.5^(730/180) ≈ 0.059 → ~6)
        meta = _make_meta(
            topics=["langchain"],
            last_updated=datetime.now(timezone.utc) - timedelta(days=730),
        )
        signal = _score_freshness(meta)
        assert signal.score < 20

    def test_no_date_is_low_confidence(self):
        meta = _make_meta(topics=["python"])
        signal = _score_freshness(meta)
        assert signal.confidence < 0.2
        assert signal.source == "default"


class TestInfoDensitySignal:
    def test_syllabus_boosts_score(self):
        meta = _make_meta(syllabus=[f"Module {i}" for i in range(25)])
        signal = _score_info_density(meta)
        assert signal.score > 60

    def test_no_signals_is_low_confidence(self):
        meta = _make_meta()
        signal = _score_info_density(meta)
        assert signal.confidence < 0.3


class TestOverallConfidenceWeighting:
    def test_high_confidence_dimensions_dominate_overall(self):
        """A strong signal on one dimension should pull the weighted overall
        toward it, even if other dimensions are defaulting."""
        meta = _make_meta(
            topics=["llm"],  # market demand = 95 at conf 0.9
            last_updated=datetime.now(timezone.utc),  # freshness 100 at conf 0.9
        )
        result = score_resource(meta)
        # The two high-confidence signals should pull overall well above 50
        assert result.overall_score > 70
        assert result.overall_confidence > 0.45
