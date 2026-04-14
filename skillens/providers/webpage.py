"""Generic webpage provider — fallback for any HTTP(S) URL.

Uses httpx + BeautifulSoup to parse Open Graph and standard meta tags.
Always last in the registry order — catches anything the specific
providers don't handle.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from skillens.core.models import ResourceMeta, SourceType
from skillens.providers.base import BaseProvider, ProviderError

_USER_AGENT = (
    "Mozilla/5.0 (compatible; SkiLens/0.1; +https://github.com/YixiaJack/skillens)"
)


class WebpageProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "webpage"

    @staticmethod
    def can_handle(url: str) -> bool:
        return url.startswith(("http://", "https://"))

    async def extract(self, url: str) -> ResourceMeta:
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=15.0,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as e:
            raise ProviderError("webpage", url, f"fetch failed: {e}") from e

        soup = BeautifulSoup(html, "html.parser")

        title = _meta(soup, "og:title") or (soup.title.string if soup.title else "") or url
        description = _meta(soup, "og:description") or _meta(soup, "description") or ""
        author = _meta(soup, "author") or _meta(soup, "article:author") or ""
        published = _parse_date(
            _meta(soup, "article:published_time")
            or _meta(soup, "og:published_time")
            or _meta(soup, "date")
        )
        updated = _parse_date(_meta(soup, "article:modified_time"))
        lang = (soup.html.get("lang") if soup.html else None) or "en"

        keywords = _meta(soup, "keywords") or ""
        topics = [t.strip() for t in keywords.split(",") if t.strip()][:10]

        # Body text sample for content analysis
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        body_text = " ".join(soup.get_text(" ", strip=True).split())

        platform = _platform_from_url(url)

        return ResourceMeta(
            title=title.strip()[:300],
            url=url,
            source_type=SourceType.ARTICLE,
            platform=platform,
            description=description[:500],
            topics=topics,
            language=lang.split("-")[0],
            published_date=published,
            last_updated=updated,
            author=author[:200],
            content_sample=body_text[:2000],
        )


def _meta(soup: BeautifulSoup, name: str) -> str:
    """Return content of first meta tag matching name or property."""
    tag = soup.find("meta", attrs={"property": name}) or soup.find(
        "meta", attrs={"name": name}
    )
    if tag and tag.get("content"):
        return str(tag["content"])
    return ""


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _platform_from_url(url: str) -> str:
    host = urlparse(url).hostname or "unknown"
    return host.removeprefix("www.")
