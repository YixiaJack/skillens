"""YouTube provider — extracts video metadata via yt-dlp.

yt-dlp is an optional dependency (`pip install skillens[youtube]`). If not
installed, the generic WebpageProvider will handle YouTube URLs instead.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from skillens.core.models import ResourceMeta, SourceType
from skillens.providers.base import BaseProvider, ProviderError

_YT_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.|music\.)?"
    r"(?:youtube\.com/(?:watch\?v=|shorts/|playlist\?list=|embed/)|youtu\.be/)",
    re.IGNORECASE,
)


class YouTubeProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "youtube"

    @staticmethod
    def can_handle(url: str) -> bool:
        return bool(_YT_URL_RE.match(url))

    async def extract(self, url: str) -> ResourceMeta:
        try:
            import yt_dlp  # type: ignore[import-untyped]
        except ImportError as e:
            raise ProviderError(
                "youtube",
                url,
                "yt-dlp not installed. Run: pip install skillens[youtube]",
            ) from e

        def _fetch() -> dict:
            opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "extract_flat": False,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                return ydl.extract_info(url, download=False) or {}

        try:
            info = await asyncio.to_thread(_fetch)
        except Exception as e:
            raise ProviderError("youtube", url, str(e)) from e

        published: datetime | None = None
        if upload_date := info.get("upload_date"):
            try:
                published = datetime.strptime(upload_date, "%Y%m%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                published = None

        duration_hours: float | None = None
        if secs := info.get("duration"):
            duration_hours = round(secs / 3600, 2)

        description = info.get("description") or ""
        tags = info.get("tags") or info.get("categories") or []

        return ResourceMeta(
            title=info.get("title") or "(untitled)",
            url=info.get("webpage_url") or url,
            source_type=SourceType.VIDEO,
            platform="youtube",
            description=description[:500],
            topics=list(tags)[:10],
            language=info.get("language") or "en",
            review_count=info.get("like_count"),
            enrollment_count=info.get("view_count"),
            published_date=published,
            duration_hours=duration_hours,
            author=info.get("uploader") or info.get("channel") or "",
            content_sample=description[:2000],
        )
