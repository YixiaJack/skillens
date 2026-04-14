"""Tests for the scoring engine."""

from datetime import datetime, timezone

from skillens.core.models import ResourceMeta, SourceType, Verdict
from skillens.core.scorer import score_resource


class TestQuickScorer:
    """Test rule-based quick scoring."""

    def _make_meta(self, **kwargs) -> ResourceMeta:
        """Helper to create a ResourceMeta with defaults."""
        defaults = {
            "title": "Test Resource",
            "source_type": SourceType.COURSE,
            "platform": "test",
        }
        defaults.update(kwargs)
        return ResourceMeta(**defaults)

    def test_high_enrollment_boosts_market_demand(self):
        meta = self._make_meta(enrollment_count=200_000)
        result = score_resource(meta, deep=False)
        assert result.market_demand >= 80

    def test_recent_content_scores_high_freshness(self):
        meta = self._make_meta(
            last_updated=datetime.now(timezone.utc),
        )
        result = score_resource(meta, deep=False)
        assert result.freshness >= 90

    def test_old_content_scores_low_freshness(self):
        meta = self._make_meta(
            published_date=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        result = score_resource(meta, deep=False)
        assert result.freshness <= 40

    def test_foundational_topic_has_long_half_life(self):
        meta = self._make_meta(topics=["algorithm", "data structure"])
        result = score_resource(meta, deep=False)
        assert "10" in result.skill_half_life

    def test_fast_moving_topic_has_short_half_life(self):
        meta = self._make_meta(topics=["langchain", "prompt engineering"])
        result = score_resource(meta, deep=False)
        assert "month" in result.skill_half_life.lower()

    def test_high_scores_produce_learn_verdict(self):
        meta = self._make_meta(
            enrollment_count=200_000,
            rating=4.8,
            last_updated=datetime.now(timezone.utc),
            duration_hours=10,
            syllabus=[f"Topic {i}" for i in range(15)],
        )
        result = score_resource(meta, deep=False)
        assert result.verdict == Verdict.LEARN

    def test_low_scores_produce_skip_verdict(self):
        meta = self._make_meta(
            enrollment_count=100,
            rating=2.5,
            published_date=datetime(2018, 1, 1, tzinfo=timezone.utc),
            duration_hours=80,
        )
        result = score_resource(meta, deep=False)
        assert result.verdict in (Verdict.SKIP, Verdict.CONSIDER_ALTERNATIVES)

    def test_overall_score_is_bounded(self):
        meta = self._make_meta()
        result = score_resource(meta, deep=False)
        assert 0 <= result.overall_score <= 100

    def test_strengths_and_concerns_are_populated(self):
        meta = self._make_meta(
            enrollment_count=200_000,
            rating=4.8,
            published_date=datetime(2018, 1, 1, tzinfo=timezone.utc),
        )
        result = score_resource(meta, deep=False)
        # Should have at least one strength (high enrollment + rating)
        assert len(result.strengths) >= 1
        # Should have at least one concern (old content)
        assert len(result.concerns) >= 1

    def test_assessment_has_correct_mode(self):
        meta = self._make_meta()
        result = score_resource(meta, deep=False)
        assert result.analysis_mode == "quick"
