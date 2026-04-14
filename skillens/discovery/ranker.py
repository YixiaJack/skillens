"""Quick-score discovered alternatives and rank them against the input.

This module takes candidate URLs found by the searcher, extracts their
metadata via providers, scores them with the same engine, and returns
ranked results with comparison deltas.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from skillens.core.models import Assessment, ResourceMeta
from skillens.core.scorer import score_resource


@dataclass
class AlternativeResult:
    """A scored alternative with comparison to the original."""

    assessment: Assessment
    score_delta: int  # positive = better than input

    @property
    def is_better(self) -> bool:
        """Only recommend if meaningfully better (>5 points)."""
        return self.score_delta > 5


async def discover_and_rank(
    input_meta: ResourceMeta,
    input_score: int,
    max_alternatives: int = 3,
) -> list[AlternativeResult]:
    """Full discovery pipeline: search → extract → score → rank.

    Args:
        input_meta: Metadata of the resource being evaluated
        input_score: Overall score of the input resource
        max_alternatives: How many alternatives to return

    Returns:
        Top alternatives sorted by score, best first.
        Only includes alternatives that score > 40.
    """
    from skillens.discovery.searcher import search_alternatives
    from skillens.providers.registry import detect_provider
    from skillens.providers.base import ProviderError

    # Step 1: Search for candidate URLs
    candidate_urls = await search_alternatives(input_meta)

    if not candidate_urls:
        return []

    # Step 2: Extract & score each candidate concurrently
    async def _evaluate_one(url: str) -> AlternativeResult | None:
        try:
            provider = detect_provider(url)
            alt_meta = await provider.extract(url)
            alt_assessment = score_resource(alt_meta, deep=False)

            # Filter out low-quality results
            if alt_assessment.overall_score < 40:
                return None

            delta = alt_assessment.overall_score - input_score
            return AlternativeResult(alt_assessment, delta)
        except (ProviderError, Exception):
            return None

    # Run extractions concurrently with a timeout
    tasks = [_evaluate_one(url) for url in candidate_urls]
    results_raw = await asyncio.gather(*tasks, return_exceptions=True)

    # Filter successful results
    results: list[AlternativeResult] = [
        r for r in results_raw
        if isinstance(r, AlternativeResult) and r is not None
    ]

    # Step 3: Sort by score (best first) and return top N
    results.sort(key=lambda r: r.assessment.overall_score, reverse=True)
    return results[:max_alternatives]
