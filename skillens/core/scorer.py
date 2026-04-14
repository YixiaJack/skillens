"""Scoring engine — rule-based (quick) and LLM-enhanced (deep).

The quick scorer uses heuristics to produce scores without any API calls.
The deep scorer sends metadata to an LLM for nuanced analysis.
"""

from __future__ import annotations

from datetime import datetime, timezone

from typing import TYPE_CHECKING

from skillens.core.models import Assessment, ResourceMeta, Verdict

if TYPE_CHECKING:
    from skillens.llm.base import LLMBackend


def score_resource(meta: ResourceMeta, deep: bool = False) -> Assessment:
    """Score a resource using rule-based heuristics.

    For LLM-enhanced scoring use `score_resource_deep` (async).
    """
    assessment = _score_quick(meta)
    _apply_profile_match(assessment, meta)
    if deep:
        assessment.analysis_mode = "deep"
    return assessment


def _apply_profile_match(assessment: Assessment, meta: ResourceMeta) -> None:
    """If a profile exists, attach a profile_match score."""
    try:
        from skillens.profile.manager import load_profile
        from skillens.profile.matcher import match_score

        profile = load_profile()
        if profile is not None:
            assessment.profile_match = match_score(meta, profile)
    except Exception:
        pass


async def score_resource_deep(
    meta: ResourceMeta,
    backend: "LLMBackend | None" = None,
) -> Assessment:
    """LLM-enhanced scoring. Falls back to quick scoring if no backend.

    The LLM's scores override the rule-based scores for the four LLM
    dimensions; half-life and overall/verdict are recomputed.
    """
    base = _score_quick(meta)
    if backend is None:
        base.analysis_mode = "deep"
        return base

    from skillens.llm.prompts import build_analysis_prompt

    try:
        analysis = await backend.analyze(build_analysis_prompt(meta))
    except Exception as e:
        base.analysis_mode = "deep"
        base.concerns.append(f"LLM analysis failed: {e}")
        return base

    base.market_demand = analysis.market_demand
    base.info_density = analysis.info_density
    base.freshness = analysis.freshness
    base.effort_vs_return = analysis.effort_vs_return
    base.strengths = analysis.strengths[:3]
    base.concerns = analysis.concerns[:3]
    base.alternatives = analysis.alternatives[:3]
    base.overall_score = _compute_overall(
        base.market_demand, base.info_density, base.freshness, base.effort_vs_return
    )
    base.verdict, _ = _determine_verdict(base.overall_score, base.market_demand, base.freshness)
    base.verdict_reason = analysis.verdict_reason
    base.analysis_mode = "deep"
    base.model_used = backend.name
    _apply_profile_match(base, meta)
    return base


def _score_quick(meta: ResourceMeta) -> Assessment:
    """Rule-based scoring — no API calls, runs in <1 second."""
    market = _score_market_demand(meta)
    half_life = _estimate_half_life(meta)
    density = _score_info_density(meta)
    fresh = _score_freshness(meta)
    effort = _score_effort_vs_return(meta, market)

    overall = _compute_overall(market, density, fresh, effort)
    verdict, reason = _determine_verdict(overall, market, fresh)

    return Assessment(
        market_demand=market,
        skill_half_life=half_life,
        info_density=density,
        freshness=fresh,
        effort_vs_return=effort,
        overall_score=overall,
        verdict=verdict,
        verdict_reason=reason,
        strengths=_identify_strengths(meta, market, density, fresh),
        concerns=_identify_concerns(meta, market, density, fresh),
        alternatives=[],  # TODO: Suggest alternatives
        resource=meta,
        analysis_mode="quick",
    )


# --- Scoring heuristics ---


def _score_market_demand(meta: ResourceMeta) -> int:
    """Score market demand using the bundled skill-demand dataset,
    falling back to popularity proxies (enrollment / stars).
    """
    from skillens.core.dataset import demand_for

    dataset_score = demand_for(meta.topics, meta.title)

    if meta.enrollment_count and meta.enrollment_count > 100_000:
        proxy = 85
    elif meta.enrollment_count and meta.enrollment_count > 10_000:
        proxy = 70
    elif meta.star_count and meta.star_count > 10_000:
        proxy = 80
    elif meta.star_count and meta.star_count > 1_000:
        proxy = 65
    else:
        proxy = None

    if dataset_score is not None and proxy is not None:
        # Weighted: dataset carries more signal, popularity refines it.
        return round(dataset_score * 0.7 + proxy * 0.3)
    if dataset_score is not None:
        return dataset_score
    if proxy is not None:
        return proxy
    return 50


def _estimate_half_life(meta: ResourceMeta) -> str:
    """Estimate how long the skill will remain relevant."""
    topics_lower = " ".join(meta.topics + [meta.title]).lower()

    # Foundational topics
    foundational = ["algorithm", "data structure", "linear algebra", "calculus",
                    "probability", "statistics", "discrete math"]
    if any(kw in topics_lower for kw in foundational):
        return "~10+ years"

    # Established frameworks
    established = ["python", "javascript", "sql", "react", "pytorch",
                   "tensorflow", "docker", "kubernetes", "git"]
    if any(kw in topics_lower for kw in established):
        return "~3-5 years"

    # Fast-moving areas
    fast_moving = ["langchain", "llamaindex", "gpt", "prompt engineering",
                   "chatgpt", "midjourney", "stable diffusion", "cursor"]
    if any(kw in topics_lower for kw in fast_moving):
        return "~6-18 months"

    return "~2-3 years"  # Default


def _score_info_density(meta: ResourceMeta) -> int:
    """Score information density based on syllabus and content analysis."""
    score = 50  # Base score

    if meta.syllabus:
        unique_topics = len(set(meta.syllabus))
        # More unique topics = higher density (up to a point)
        if unique_topics > 20:
            score += 20
        elif unique_topics > 10:
            score += 10

    if meta.rating and meta.rating >= 4.5:
        score += 10
    elif meta.rating and meta.rating >= 4.0:
        score += 5

    return min(score, 100)


def _score_freshness(meta: ResourceMeta) -> int:
    """Score based on how recent the content is."""
    if not meta.last_updated and not meta.published_date:
        return 50  # Unknown — neutral score

    ref_date = meta.last_updated or meta.published_date
    if ref_date is None:
        return 50

    now = datetime.now(timezone.utc)
    if ref_date.tzinfo is None:
        ref_date = ref_date.replace(tzinfo=timezone.utc)

    age_days = (now - ref_date).days

    if age_days < 90:
        return 95
    if age_days < 365:
        return 80
    if age_days < 730:
        return 60
    if age_days < 1095:
        return 40
    return 20  # Older than 3 years


def _score_effort_vs_return(meta: ResourceMeta, market_demand: int) -> int:
    """Score ROI: is the time investment justified?"""
    if not meta.duration_hours:
        return max(50, market_demand - 10)  # Unknown duration — slight discount

    # Short + high demand = great ROI
    if meta.duration_hours <= 5 and market_demand >= 70:
        return 90
    if meta.duration_hours <= 20 and market_demand >= 60:
        return 75
    if meta.duration_hours > 60 and market_demand < 50:
        return 30
    if meta.duration_hours > 40 and market_demand < 60:
        return 40

    return 60  # Default


def _compute_overall(market: int, density: int, fresh: int, effort: int) -> int:
    """Weighted average of all scores."""
    return round(market * 0.30 + density * 0.20 + fresh * 0.25 + effort * 0.25)


def _determine_verdict(overall: int, market: int, fresh: int) -> tuple[Verdict, str]:
    """Determine verdict based on scores."""
    if overall >= 70:
        return Verdict.LEARN, "Strong fundamentals with good market alignment."
    if overall >= 50:
        if fresh < 40:
            return Verdict.CONSIDER_ALTERNATIVES, "Content is solid but aging — check for newer versions."
        if market < 40:
            return Verdict.CONSIDER_ALTERNATIVES, "Interesting content but limited market demand."
        return Verdict.CONSIDER_ALTERNATIVES, "Decent resource but not the best use of your time."
    return Verdict.SKIP, "Low ROI — better alternatives likely exist."


def _identify_strengths(
    meta: ResourceMeta, market: int, density: int, fresh: int
) -> list[str]:
    """Identify 2-3 strengths."""
    strengths = []
    if market >= 70:
        strengths.append("High market demand for this skill")
    if fresh >= 80:
        strengths.append("Content is very recent and up-to-date")
    if meta.rating and meta.rating >= 4.5:
        strengths.append(f"Excellent community rating ({meta.rating:.1f}/5)")
    if meta.enrollment_count and meta.enrollment_count > 50_000:
        strengths.append(f"Popular — {meta.enrollment_count:,} enrolled")
    if meta.institution:
        strengths.append(f"From {meta.institution}")
    return strengths[:3]


def _identify_concerns(
    meta: ResourceMeta, market: int, density: int, fresh: int
) -> list[str]:
    """Identify 2-3 concerns."""
    concerns = []
    if fresh < 40:
        concerns.append("Content may be outdated")
    if market < 40:
        concerns.append("Limited job market demand")
    if meta.duration_hours and meta.duration_hours > 50:
        concerns.append(f"Very long ({meta.duration_hours:.0f}h) — consider if you need all of it")
    if density < 40:
        concerns.append("May have low information density")
    if meta.rating and meta.rating < 3.5:
        concerns.append(f"Below-average rating ({meta.rating:.1f}/5)")
    return concerns[:3]
