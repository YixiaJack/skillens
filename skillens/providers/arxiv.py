"""arXiv provider — extracts paper metadata via the arXiv Atom API."""

from __future__ import annotations

import re
from datetime import datetime
from xml.etree import ElementTree as ET

import httpx

from skillens.core.models import ResourceMeta, SourceType
from skillens.providers.base import BaseProvider, ProviderError

_ARXIV_URL_RE = re.compile(
    r"^https?://arxiv\.org/(?:abs|pdf)/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?/?$",
    re.IGNORECASE,
)

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArXivProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "arxiv"

    @staticmethod
    def can_handle(url: str) -> bool:
        return bool(_ARXIV_URL_RE.match(url))

    async def extract(self, url: str) -> ResourceMeta:
        m = _ARXIV_URL_RE.match(url)
        if not m:
            raise ProviderError("arxiv", url, "not an arXiv URL")
        paper_id = m.group(1)

        api_url = f"http://export.arxiv.org/api/query?id_list={paper_id}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(api_url)
                resp.raise_for_status()
                xml_text = resp.text
        except httpx.HTTPError as e:
            raise ProviderError("arxiv", url, f"API error: {e}") from e

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            raise ProviderError("arxiv", url, f"bad XML: {e}") from e

        entry = root.find("atom:entry", _NS)
        if entry is None:
            raise ProviderError("arxiv", url, f"no entry for {paper_id}")

        def _text(elem_name: str) -> str:
            el = entry.find(elem_name, _NS)
            return (el.text or "").strip() if el is not None else ""

        title = _text("atom:title").replace("\n", " ")
        summary = _text("atom:summary").replace("\n", " ")
        published = _parse_iso(_text("atom:published"))
        updated = _parse_iso(_text("atom:updated"))

        authors = [
            (a.findtext("atom:name", default="", namespaces=_NS) or "").strip()
            for a in entry.findall("atom:author", _NS)
        ]

        categories = [
            c.get("term", "")
            for c in entry.findall("atom:category", _NS)
            if c.get("term")
        ]

        return ResourceMeta(
            title=title[:300],
            url=f"https://arxiv.org/abs/{paper_id}",
            source_type=SourceType.PAPER,
            platform="arxiv",
            description=summary[:500],
            topics=categories[:10],
            language="en",
            published_date=published,
            last_updated=updated,
            author=", ".join(authors[:3]),
            content_sample=summary[:2000],
        )


def _parse_iso(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
