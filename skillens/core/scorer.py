"""Scoring engine — rule-based (quick) and LLM-enhanced (deep).

Design notes (as of 0.2.0):

- Every dimension returns a `Signal(score, confidence, source)`.
  Confidence is 0.0 when we had no real data (silent default) and 1.0
  when we had hard evidence. This lets the display layer be honest:
  a resource with 50/50/50/50 and confidence 0.1 is shown with a
  ⚠ "insufficient data" banner instead of pretending the score is real.

- The overall score is a confidence-weighted average of the four
  dimensions. Weights still reflect the trade-offs SkiLens cares about
  (market > freshness ~ effort > density) but each weight is multiplied
  by the dimension's confidence, so a missing dimension simply
  contributes less instead of poisoning the average with `50`.

- Freshness is exponential decay with a topic-dependent half-life, so
  a 2-year-old Python tutorial is still fresh (half-life ~7y) while a
  2-year-old LangChain tutorial is stale (half-life ~6mo). This
  couples freshness and skill-half-life, which is the correct behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from skillens.core.models import Assessment, ResourceMeta, Verdict

if TYPE_CHECKING:
    from skillens.llm.base import LLMBackend


# --- Signal primitive ----------------------------------------------------


@dataclass
class Signal:
    """A dimension score with its confidence and provenance."""

    score: int  # 0-100
    confidence: float  # 0.0 = default/no data, 1.0 = hard data
    source: str  # "dataset", "enrollment", "default", ...

    def __post_init__(self) -> None:
        self.score = max(0, min(100, int(self.score)))
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


# --- Public entry points -------------------------------------------------


def score_resource(meta: ResourceMeta, deep: bool = False) -> Assessment:
    """Score a resource using rule-based heuristics.

    For LLM-enhanced scoring use `score_resource_deep` (async).
    """
    assessment = _score_quick(meta)
    _apply_profile_match(assessment, meta)
    if deep:
        assessment.analysis_mode = "deep"
    return assessment


async def score_resource_deep(
    meta: ResourceMeta,
    backend: "LLMBackend | None" = None,
) -> Assessment:
    """LLM-enhanced scoring. Falls back to quick scoring if no backend.

    When the LLM succeeds, its scores override the rule-based scores for
    the four LLM-covered dimensions — but we mark them at confidence 0.85
    (not 1.0) because the LLM is working from a scraped sample, not full
    content. Half-life and the overall/verdict are then recomputed.
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
        _apply_profile_match(base, meta)
        return base

    llm_conf = 0.85
    llm_source = f"llm:{backend.name}"
    signals = {
        "market_demand": Signal(analysis.market_demand, llm_conf, llm_source),
        "info_density": Signal(analysis.info_density, llm_conf, llm_source),
        "freshness": Signal(analysis.freshness, llm_conf, llm_source),
        "effort_vs_return": Signal(analysis.effort_vs_return, llm_conf, llm_source),
    }
    _apply_signals(base, signals)

    base.strengths = analysis.strengths[:3]
    base.concerns = analysis.concerns[:3]
    base.alternatives = analysis.alternatives[:3]
    base.verdict_reason = analysis.verdict_reason
    base.analysis_mode = "deep"
    base.model_used = backend.name
    _apply_profile_match(base, meta)
    return base


# --- Quick mode orchestration --------------------------------------------


def _score_quick(meta: ResourceMeta) -> Assessment:
    """Rule-based scoring — no API calls, runs in <1 second."""
    market = _score_market_demand(meta)
    density = _score_info_density(meta)
    fresh = _score_freshness(meta)
    effort = _score_effort_vs_return(meta, market)
    half_life_label = _estimate_half_life(meta)

    signals = {
        "market_demand": market,
        "info_density": density,
        "freshness": fresh,
        "effort_vs_return": effort,
    }
    overall, overall_conf = _compute_overall(signals)
    verdict, reason = _determine_verdict(overall, overall_conf, market, fresh)

    return Assessment(
        market_demand=market.score,
        skill_half_life=half_life_label,
        info_density=density.score,
        freshness=fresh.score,
        effort_vs_return=effort.score,
        confidences={k: round(v.confidence, 2) for k, v in signals.items()},
        sources={k: v.source for k, v in signals.items()},
        overall_score=overall,
        overall_confidence=round(overall_conf, 2),
        verdict=verdict,
        verdict_reason=reason,
        strengths=_identify_strengths(meta, market, density, fresh),
        concerns=_identify_concerns(meta, market, density, fresh, overall_conf),
        alternatives=[],
        resource=meta,
        analysis_mode="quick",
    )


def _apply_signals(assessment: Assessment, signals: dict[str, Signal]) -> None:
    """Overwrite an assessment's per-dim fields from a signals dict
    and recompute the overall score/verdict."""
    assessment.market_demand = signals["market_demand"].score
    assessment.info_density = signals["info_density"].score
    assessment.freshness = signals["freshness"].score
    assessment.effort_vs_return = signals["effort_vs_return"].score
    assessment.confidences = {k: round(v.confidence, 2) for k, v in signals.items()}
    assessment.sources = {k: v.source for k, v in signals.items()}
    overall, overall_conf = _compute_overall(signals)
    assessment.overall_score = overall
    assessment.overall_confidence = round(overall_conf, 2)
    verdict, _ = _determine_verdict(
        overall,
        overall_conf,
        signals["market_demand"],
        signals["freshness"],
    )
    assessment.verdict = verdict


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


# --- Per-dimension scorers -----------------------------------------------


def _score_market_demand(meta: ResourceMeta) -> Signal:
    """Demand score, sourced from the skill dataset and/or popularity proxies.

    Confidence hierarchy:
      1.00: dataset hit AND popularity proxy agree
      0.90: dataset hit alone
      0.70: strong popularity proxy alone (>100k enrolled or >10k stars)
      0.50: moderate popularity proxy alone
      0.10: nothing — score degrades to 50 with low confidence
    """
    from skillens.core.dataset import demand_for

    dataset_score = demand_for(meta.topics, meta.title)

    proxy: int | None = None
    if meta.enrollment_count and meta.enrollment_count > 100_000:
        proxy = 85
    elif meta.enrollment_count and meta.enrollment_count > 10_000:
        proxy = 72
    elif meta.star_count and meta.star_count > 10_000:
        proxy = 80
    elif meta.star_count and meta.star_count > 1_000:
        proxy = 65

    if dataset_score is not None and proxy is not None:
        return Signal(
            round(dataset_score * 0.7 + proxy * 0.3),
            1.00,
            "dataset+popularity",
        )
    if dataset_score is not None:
        return Signal(dataset_score, 0.90, "dataset")
    if proxy is not None and proxy >= 75:
        return Signal(proxy, 0.70, "popularity")
    if proxy is not None:
        return Signal(proxy, 0.50, "popularity")
    return Signal(50, 0.10, "default")


def _estimate_half_life(meta: ResourceMeta) -> str:
    """Human-readable half-life label, derived from the dataset when possible."""
    from skillens.core.dataset import halflife_for

    days = halflife_for(meta.topics, meta.title)
    if days >= 3650:  # 10+ years
        return f"~{days // 365}+ years"
    if days >= 730:  # 2-9 years
        return f"~{days // 365} years"
    if days >= 335:  # ~1 year — give a bit of slack for 335-730
        return "~1 year"
    # Sub-year: report in months
    months = max(1, round(days / 30))
    return f"~{months} months"


def _score_info_density(meta: ResourceMeta) -> Signal:
    """Estimate info density from syllabus structure, ratings, and content sample.

    No single strong signal here — it's always a judgment call. Max confidence
    is 0.75 unless deep mode actually reads the content.
    """
    base = 50
    contributions = 0

    if meta.syllabus:
        unique_sections = len(set(meta.syllabus))
        if unique_sections >= 20:
            base += 20
        elif unique_sections >= 10:
            base += 12
        elif unique_sections >= 5:
            base += 6
        contributions += 1

    if meta.rating is not None:
        if meta.rating >= 4.7:
            base += 10
        elif meta.rating >= 4.3:
            base += 5
        elif meta.rating < 3.8:
            base -= 10
        contributions += 1

    if meta.content_sample:
        # Rough type-token ratio proxy: unique lowercase words / total.
        tokens = [w for w in meta.content_sample.lower().split() if len(w) > 2]
        if tokens:
            ttr = len(set(tokens)) / len(tokens)
            if ttr >= 0.55:
                base += 8
            elif ttr <= 0.25:
                base -= 8
            contributions += 1

    base = max(0, min(100, base))
    confidence = min(0.75, 0.20 + 0.20 * contributions)
    source = "default" if contributions == 0 else f"{contributions}-signal"
    return Signal(base, confidence, source)


def _score_freshness(meta: ResourceMeta) -> Signal:
    """Exponential-decay freshness using topic-dependent half-life.

    freshness = 100 * 0.5 ** (age_days / topic_halflife_days)

    This means:
    - age == 0 → score 100
    - age == half-life → score 50 (content is "half decayed")
    - age == 2x half-life → score 25
    - age == 3x half-life → score ~12

    And the half-life is pulled from the skill dataset, so a 3-year-old
    Python course (half-life ~7y) still scores ~75, while a 3-year-old
    LangChain tutorial (half-life ~6mo) scores ~1.
    """
    from skillens.core.dataset import halflife_for

    ref_date = meta.last_updated or meta.published_date
    if ref_date is None:
        return Signal(50, 0.05, "default")

    now = datetime.now(timezone.utc)
    if ref_date.tzinfo is None:
        ref_date = ref_date.replace(tzinfo=timezone.utc)
    age_days = max(0, (now - ref_date).days)

    halflife = halflife_for(meta.topics, meta.title)
    score = round(100 * (0.5 ** (age_days / halflife)))
    score = max(0, min(100, score))

    confidence = 0.90 if meta.last_updated else 0.75
    source = "last_updated" if meta.last_updated else "published_date"
    return Signal(score, confidence, source)


def _score_effort_vs_return(meta: ResourceMeta, market: Signal) -> Signal:
    """ROI: duration vs market demand. Requires duration_hours for high confidence."""
    if not meta.duration_hours:
        # Without duration we literally don't know ROI. Degrade to a
        # neutral-ish value anchored on market demand, at low confidence.
        fallback = max(40, min(70, market.score - 5))
        return Signal(fallback, 0.25, "market_proxy")

    d = meta.duration_hours
    m = market.score
    if d <= 5 and m >= 70:
        score = 92
    elif d <= 10 and m >= 70:
        score = 85
    elif d <= 20 and m >= 60:
        score = 78
    elif d <= 40 and m >= 60:
        score = 68
    elif d > 60 and m < 50:
        score = 25
    elif d > 40 and m < 60:
        score = 38
    else:
        score = 60

    return Signal(score, 0.85, "duration+market")


# --- Aggregation + verdict -----------------------------------------------


# Weights reflect trade-offs: market demand is the most load-bearing signal
# (is this skill worth knowing at all?), freshness and effort come next,
# info density is hardest to measure without reading the content so it's
# weighted lowest.
_WEIGHTS = {
    "market_demand": 0.30,
    "info_density": 0.20,
    "freshness": 0.25,
    "effort_vs_return": 0.25,
}


def _compute_overall(signals: dict[str, Signal]) -> tuple[int, float]:
    """Confidence-weighted average of dimension scores.

    Each dimension contributes `weight * confidence * score`, and the
    denominator is `sum(weight * confidence)`. A dimension with confidence 0
    effectively drops out. If *all* dimensions are zero-confidence, we fall
    back to the raw weighted average so the user still sees *something*.
    """
    weighted_score = 0.0
    weighted_conf = 0.0
    for key, sig in signals.items():
        w = _WEIGHTS.get(key, 0.0)
        weighted_score += w * sig.confidence * sig.score
        weighted_conf += w * sig.confidence

    if weighted_conf < 1e-6:  # everyone's guessing
        raw = sum(_WEIGHTS[k] * signals[k].score for k in signals)
        return round(raw), 0.05

    overall_score = round(weighted_score / weighted_conf)
    overall_confidence = sum(
        _WEIGHTS[k] * signals[k].confidence for k in signals
    )
    return overall_score, overall_confidence


def _determine_verdict(
    overall: int, overall_confidence: float, market: Signal, fresh: Signal
) -> tuple[Verdict, str]:
    """Verdict depends on overall score AND confidence.

    If we don't trust the number, we refuse to recommend or reject —
    we return CONSIDER_ALTERNATIVES with an honest "insufficient data"
    reason so the user goes looking for more info.
    """
    if overall_confidence < 0.35:
        return (
            Verdict.CONSIDER_ALTERNATIVES,
            "Insufficient data to evaluate this resource — interpret scores with caution.",
        )
    if overall >= 72:
        return Verdict.LEARN, "Strong fundamentals with good market alignment."
    if overall >= 55:
        if fresh.score < 40 and fresh.confidence >= 0.5:
            return (
                Verdict.CONSIDER_ALTERNATIVES,
                "Content is solid but aging — check for newer versions.",
            )
        if market.score < 45 and market.confidence >= 0.5:
            return (
                Verdict.CONSIDER_ALTERNATIVES,
                "Interesting content but limited market demand.",
            )
        return (
            Verdict.CONSIDER_ALTERNATIVES,
            "Decent resource but not the clear best use of your time.",
        )
    return Verdict.SKIP, "Low ROI — better alternatives likely exist."


# --- Strengths / concerns ------------------------------------------------


def _identify_strengths(
    meta: ResourceMeta, market: Signal, density: Signal, fresh: Signal
) -> list[str]:
    strengths: list[str] = []
    if market.score >= 78 and market.confidence >= 0.7:
        strengths.append("High market demand for this skill")
    if fresh.score >= 80 and fresh.confidence >= 0.7:
        strengths.append("Content is very recent and up-to-date")
    if meta.rating is not None and meta.rating >= 4.7:
        strengths.append(f"Excellent community rating ({meta.rating:.1f}/5)")
    if meta.enrollment_count and meta.enrollment_count > 50_000:
        strengths.append(f"Popular — {meta.enrollment_count:,} enrolled")
    if meta.institution:
        strengths.append(f"From {meta.institution}")
    return strengths[:3]


def _identify_concerns(
    meta: ResourceMeta,
    market: Signal,
    density: Signal,
    fresh: Signal,
    overall_confidence: float,
) -> list[str]:
    concerns: list[str] = []
    if overall_confidence < 0.35:
        concerns.append(
            "Not enough metadata was extracted — scores are best-effort guesses"
        )
    if fresh.score < 40 and fresh.confidence >= 0.5:
        concerns.append("Content may be outdated for a fast-moving topic")
    if market.score < 45 and market.confidence >= 0.5:
        concerns.append("Limited job-market demand")
    if meta.duration_hours and meta.duration_hours > 50:
        concerns.append(
            f"Very long ({meta.duration_hours:.0f}h) — consider if you need all of it"
        )
    if density.score < 40 and density.confidence >= 0.5:
        concerns.append("May have low information density")
    if meta.rating is not None and meta.rating < 3.8:
        concerns.append(f"Below-average rating ({meta.rating:.1f}/5)")
    return concerns[:3]
