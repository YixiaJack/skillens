"""Coursera provider — extracts course metadata from the public page.

Strategy: fetch the HTML and parse JSON-LD (`<script type="application/ld+json">`)
which Coursera embeds for SEO — it contains the Course schema with name,
description, provider, aggregateRating, etc. Falls back to Open Graph meta
tags for fields the JSON-LD doesn't cover.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup

# ISO 8601 duration: PT60H, PT1H30M, PT90M, P7D, etc. We only care about
# the hours/minutes/days for a course time estimate.
_ISO_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+(?:\.\d+)?)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+(?:\.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(?:\.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(?:\.\d+)?)S)?"
    r")?$"
)
# "1,234,567 already enrolled" / "1.2M enrolled" — any number before "enroll"
_ENROLL_RE = re.compile(
    r"([\d,]+|\d+(?:\.\d+)?[KkMm])\s+(?:already\s+)?enroll", re.IGNORECASE
)

from skillens.core.models import ResourceMeta, SourceType
from skillens.providers.base import BaseProvider, ProviderError

_COURSERA_URL_RE = re.compile(
    r"^https?://(?:www\.)?coursera\.org/(?:learn|specializations|professional-certificates|projects)/[\w\-]+",
    re.IGNORECASE,
)

_USER_AGENT = (
    "Mozilla/5.0 (compatible; SkiLens/0.1; +https://github.com/YixiaJack/skillens)"
)


class CourseraProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "coursera"

    @staticmethod
    def can_handle(url: str) -> bool:
        return bool(_COURSERA_URL_RE.match(url))

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
            raise ProviderError("coursera", url, f"fetch failed: {e}") from e

        soup = BeautifulSoup(html, "html.parser")
        course = _find_course_jsonld(soup)

        # Title
        title = (
            (course.get("name") if course else None)
            or _meta(soup, "og:title")
            or (soup.title.string if soup.title else "")
            or url
        )

        # Description
        description = (
            (course.get("description") if course else None)
            or _meta(soup, "og:description")
            or _meta(soup, "description")
            or ""
        )

        # Rating
        rating: float | None = None
        review_count: int | None = None
        if course:
            agg = course.get("aggregateRating") or {}
            if isinstance(agg, dict):
                try:
                    rating = float(agg.get("ratingValue")) if agg.get("ratingValue") else None
                    rc = agg.get("ratingCount") or agg.get("reviewCount")
                    review_count = int(rc) if rc else None
                except (TypeError, ValueError):
                    pass

        # Institution / provider
        institution = ""
        if course:
            provider = course.get("provider")
            if isinstance(provider, list) and provider:
                provider = provider[0]
            if isinstance(provider, dict):
                institution = provider.get("name") or ""
            elif isinstance(provider, str):
                institution = provider

        # Instructor(s)
        author = ""
        if course:
            instructors = course.get("instructor") or course.get("author")
            names = _extract_names(instructors)
            author = ", ".join(names[:3])

        # Syllabus — best-effort from hasCourseInstance or syllabusSections;
        # Coursera's public JSON-LD usually omits this, so we scan headings too.
        syllabus: list[str] = []
        for h in soup.select("h3, h4"):
            text = h.get_text(" ", strip=True)
            if 10 < len(text) < 120 and "module" in text.lower():
                syllabus.append(text)
        syllabus = syllabus[:20]

        # Topics: try JSON-LD keywords / about / teaches first, then fall back
        # to the "Skills you'll gain" HTML section which Coursera always renders.
        topics: list[str] = []
        if course:
            for field in ("keywords", "about", "teaches", "educationalUse"):
                value = course.get(field)
                if not value:
                    continue
                if isinstance(value, str):
                    topics.extend(
                        [t.strip() for t in value.split(",") if t.strip()]
                    )
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            topics.append(item)
                        elif isinstance(item, dict) and item.get("name"):
                            topics.append(str(item["name"]))
        if not topics:
            topics = _extract_skills_section(soup)
        # Dedupe preserving order, cap at 10
        seen: set[str] = set()
        deduped: list[str] = []
        for t in topics:
            key = t.lower()
            if key and key not in seen:
                seen.add(key)
                deduped.append(t)
        topics = deduped[:10]

        # Dates
        published = _parse_iso(course.get("datePublished")) if course else None
        updated = _parse_iso(course.get("dateModified")) if course else None

        # Duration: JSON-LD timeRequired is ISO 8601 (e.g. "PT60H")
        duration_hours: float | None = None
        if course:
            tr = course.get("timeRequired") or course.get("duration")
            if isinstance(tr, str):
                duration_hours = _parse_iso_duration_hours(tr)

        # Enrollment — JSON-LD numberOfStudents first, then rendered HTML text
        enrollment_count: int | None = None
        if course:
            for key in ("numberOfStudents", "totalStudents"):
                if val := course.get(key):
                    try:
                        enrollment_count = int(val)
                        break
                    except (TypeError, ValueError):
                        pass
        if enrollment_count is None:
            enrollment_count = _extract_enrollment_count(soup)

        return ResourceMeta(
            title=str(title).strip()[:300],
            url=url,
            source_type=SourceType.COURSE,
            platform="coursera",
            description=description[:500],
            syllabus=syllabus,
            topics=topics,
            language="en",
            rating=rating,
            review_count=review_count,
            enrollment_count=enrollment_count,
            published_date=published,
            last_updated=updated,
            duration_hours=duration_hours,
            author=author[:200],
            institution=institution[:200],
            content_sample=description[:2000],
        )


def _extract_skills_section(soup: BeautifulSoup) -> list[str]:
    """Find the 'Skills you'll gain' section and return its items.

    Coursera's markup changes often, so we probe several locations:
    the heading text, aria-labels, data-testid attrs. Best-effort.
    """
    skills: list[str] = []
    for heading in soup.find_all(["h2", "h3", "h4"]):
        text = heading.get_text(" ", strip=True).lower()
        if "skills you" in text or "what you'll learn" in text:
            container = heading.parent
            if container is None:
                continue
            for item in container.find_all(["li", "span", "a"]):
                t = item.get_text(" ", strip=True)
                if t and 2 <= len(t) <= 60 and t.lower() not in text:
                    skills.append(t)
            if skills:
                return skills[:15]
    # aria-labelled fallback
    for node in soup.find_all(attrs={"aria-label": True}):
        label = str(node.get("aria-label", "")).lower()
        if "skills" in label:
            for item in node.find_all(["li", "span"]):
                t = item.get_text(" ", strip=True)
                if t and 2 <= len(t) <= 60:
                    skills.append(t)
            if skills:
                return skills[:15]
    return []


def _extract_enrollment_count(soup: BeautifulSoup) -> int | None:
    """Find the '1,234,567 already enrolled' text anywhere on the page."""
    text = soup.get_text(" ", strip=True)
    match = _ENROLL_RE.search(text)
    if not match:
        return None
    raw = match.group(1)
    try:
        if raw.lower().endswith("m"):
            return int(float(raw[:-1]) * 1_000_000)
        if raw.lower().endswith("k"):
            return int(float(raw[:-1]) * 1_000)
        return int(raw.replace(",", ""))
    except ValueError:
        return None


def _parse_iso_duration_hours(value: str) -> float | None:
    """Parse ISO 8601 duration and return total hours.

    Supports H/M/D components. `PT60H` → 60.0, `PT1H30M` → 1.5,
    `P7D` → 168.0. Unknown format returns None.
    """
    if not value:
        return None
    m = _ISO_DURATION_RE.match(value.strip())
    if not m:
        return None
    days = float(m.group("days") or 0)
    hours = float(m.group("hours") or 0)
    minutes = float(m.group("minutes") or 0)
    seconds = float(m.group("seconds") or 0)
    total_hours = days * 24 + hours + minutes / 60 + seconds / 3600
    return round(total_hours, 2) if total_hours > 0 else None


def _find_course_jsonld(soup: BeautifulSoup) -> dict[str, Any] | None:
    """Find the first JSON-LD block whose @type is Course."""
    for tag in soup.find_all("script", type="application/ld+json"):
        if not tag.string:
            continue
        try:
            data = json.loads(tag.string)
        except json.JSONDecodeError:
            continue
        for obj in _iter_objects(data):
            t = obj.get("@type")
            if t == "Course" or (isinstance(t, list) and "Course" in t):
                return obj
    return None


def _iter_objects(data: Any):
    if isinstance(data, dict):
        yield data
        for v in data.values():
            yield from _iter_objects(v)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_objects(item)


def _extract_names(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [value.get("name", "")] if value.get("name") else []
    if isinstance(value, list):
        names: list[str] = []
        for item in value:
            names.extend(_extract_names(item))
        return [n for n in names if n]
    return []


def _meta(soup: BeautifulSoup, name: str) -> str:
    tag = soup.find("meta", attrs={"property": name}) or soup.find(
        "meta", attrs={"name": name}
    )
    if tag and tag.get("content"):
        return str(tag["content"])
    return ""


def _parse_iso(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
