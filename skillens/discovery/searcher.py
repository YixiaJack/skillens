"""Search the web for alternative learning resources on the same topic.

Uses DuckDuckGo search (no API key needed) to find candidate resources
on YouTube, Coursera, GitHub, and the general web.
"""

from __future__ import annotations

import datetime

from skillens.core.models import ResourceMeta


async def search_alternatives(
    meta: ResourceMeta,
    max_results: int = 10,
) -> list[str]:
    """Search for alternative resources covering the same topics.

    Strategy:
    1. Extract 2-3 core topic keywords from the input resource
    2. Build platform-specific search queries
    3. Run searches and collect candidate URLs
    4. Deduplicate and filter out the input URL

    Returns a list of candidate URLs to evaluate.
    """
    keywords = _extract_search_keywords(meta)
    queries = _build_queries(keywords, meta.source_type)

    candidate_urls: list[str] = []
    for query in queries:
        urls = await _web_search(query, max_per_query=5)
        candidate_urls.extend(urls)

    # Deduplicate and remove input URL
    seen: set[str] = set()
    unique: list[str] = []
    for url in candidate_urls:
        normalized = url.rstrip("/").lower().split("?")[0]  # strip query params
        if normalized not in seen and normalized != (meta.url or "").rstrip("/").lower().split("?")[0]:
            seen.add(normalized)
            unique.append(url)

    return unique[:max_results]


def _extract_search_keywords(meta: ResourceMeta) -> list[str]:
    """Extract 2-3 core topic keywords from resource metadata."""
    if meta.topics:
        return meta.topics[:3]

    # Fallback: use title words, filtering noise
    stop_words = {
        "course", "tutorial", "introduction", "complete", "guide",
        "learn", "beginner", "advanced", "the", "a", "an", "for", "to",
        "with", "and", "in", "on", "of", "how", "what", "why", "best",
        "free", "full", "new", "2024", "2025", "2026",
    }
    words = [w for w in meta.title.lower().split() if w not in stop_words and len(w) > 2]
    return words[:3]


def _build_queries(keywords: list[str], source_type: str) -> list[str]:
    """Build search queries targeting different platforms."""
    topic = " ".join(keywords)
    year = datetime.datetime.now().year

    queries = [
        f"{topic} course {year}",
        f"{topic} tutorial site:youtube.com",
        f"{topic} site:github.com",
        f"best {topic} resource {year}",
    ]
    return queries


async def _web_search(query: str, max_per_query: int = 5) -> list[str]:
    """Run a web search and return result URLs.

    Uses duckduckgo-search package if available, else returns empty.
    Install with: pip install duckduckgo-search

    TODO: Implement actual search. Options:
    - duckduckgo-search (pip install duckduckgo-search)
    - SearXNG self-hosted instance
    - Google Custom Search API (requires key)
    """
    try:
        try:
            from ddgs import DDGS  # type: ignore[import-untyped]
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore[import-untyped]

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_per_query))
            return [r["href"] for r in results if "href" in r]
    except ImportError:
        return []
    except Exception:
        return []
