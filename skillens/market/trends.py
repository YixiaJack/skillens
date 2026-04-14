"""Skill/topic market analysis via web search.

Uses the same DDG-backed searcher as discovery. Counts job postings
and tutorial hits as proxies for demand and supply.
"""

from __future__ import annotations

from skillens.core.scorer import _estimate_half_life
from skillens.core.models import ResourceMeta, SourceType
from skillens.discovery.searcher import _web_search


async def analyze_topic(skill: str) -> dict:
    """Return a dict with demand signals and top learning resources."""
    job_query = f"{skill} jobs hiring 2026"
    tutorial_query = f"{skill} tutorial course"

    job_urls = await _web_search(job_query, max_per_query=10)
    tutorial_urls = await _web_search(tutorial_query, max_per_query=10)

    job_hits = len(job_urls)
    tutorial_hits = len(tutorial_urls)

    # Demand score: lots of jobs → high; few jobs + lots of tutorials → saturated
    if job_hits >= 8:
        demand = 85
    elif job_hits >= 5:
        demand = 70
    elif job_hits >= 2:
        demand = 55
    else:
        demand = 35

    fake_meta = ResourceMeta(
        title=skill,
        topics=[skill],
        source_type=SourceType.UNKNOWN,
    )
    half_life = _estimate_half_life(fake_meta)

    return {
        "skill": skill,
        "job_hits": job_hits,
        "tutorial_hits": tutorial_hits,
        "demand_score": demand,
        "half_life": half_life,
        "top_resources": tutorial_urls[:5],
    }
