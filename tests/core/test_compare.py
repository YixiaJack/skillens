"""Tests for --compare mode display."""

from datetime import datetime, timezone

from skillens.core.models import Assessment, ResourceMeta, SourceType, Verdict
from skillens.display.compare import print_compare


def _assessment(title: str, overall: int, freshness: int = 70) -> Assessment:
    meta = ResourceMeta(title=title, source_type=SourceType.COURSE, platform="x")
    return Assessment(
        market_demand=70,
        skill_half_life="~2-3 years",
        info_density=60,
        freshness=freshness,
        effort_vs_return=65,
        overall_score=overall,
        verdict=Verdict.LEARN if overall >= 70 else Verdict.CONSIDER_ALTERNATIVES,
        verdict_reason="test",
        resource=meta,
        timestamp=datetime.now(timezone.utc),
    )


def test_print_compare_runs(capsys):
    a = _assessment("Course A", 82, freshness=90)
    b = _assessment("Course B", 65, freshness=50)
    print_compare(a, b)
    out = capsys.readouterr().out
    assert "Course A" in out
    assert "Course B" in out
    assert "Winner" in out
