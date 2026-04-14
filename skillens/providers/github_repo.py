"""GitHub repository provider — extracts repo metadata via the REST API.

Uses the public unauthenticated endpoint; set a GITHUB_TOKEN env var if
you hit the 60 req/hour rate limit.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import httpx

from skillens.core.models import ResourceMeta, SourceType
from skillens.providers.base import BaseProvider, ProviderError

_GH_URL_RE = re.compile(
    r"^https?://github\.com/([\w.\-]+)/([\w.\-]+?)(?:\.git)?/?(?:[#?].*)?$",
    re.IGNORECASE,
)


class GitHubRepoProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "github"

    @staticmethod
    def can_handle(url: str) -> bool:
        m = _GH_URL_RE.match(url)
        if not m:
            return False
        # Exclude non-repo paths like /features, /settings, /orgs/...
        path = m.group(2).lower()
        return path not in {"features", "pricing", "about", "settings", "marketplace"}

    async def extract(self, url: str) -> ResourceMeta:
        m = _GH_URL_RE.match(url)
        if not m:
            raise ProviderError("github", url, "not a GitHub repo URL")
        owner, repo = m.group(1), m.group(2)

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SkiLens/0.1",
        }
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"

        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
                resp = await client.get(api_url)
                resp.raise_for_status()
                data = resp.json()
                # Also fetch README for content sample (best-effort)
                readme_text = ""
                try:
                    readme_resp = await client.get(
                        f"{api_url}/readme",
                        headers={**headers, "Accept": "application/vnd.github.raw"},
                    )
                    if readme_resp.status_code == 200:
                        readme_text = readme_resp.text
                except httpx.HTTPError:
                    pass
        except httpx.HTTPError as e:
            raise ProviderError("github", url, f"API error: {e}") from e

        pushed = _parse_iso(data.get("pushed_at"))
        created = _parse_iso(data.get("created_at"))

        return ResourceMeta(
            title=data.get("full_name") or f"{owner}/{repo}",
            url=data.get("html_url") or url,
            source_type=SourceType.REPO,
            platform="github",
            description=(data.get("description") or "")[:500],
            topics=list(data.get("topics") or [])[:10],
            language=(data.get("language") or "en").lower(),
            star_count=data.get("stargazers_count"),
            review_count=data.get("watchers_count"),
            published_date=created,
            last_updated=pushed,
            author=(data.get("owner") or {}).get("login") or owner,
            content_sample=readme_text[:2000],
        )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
