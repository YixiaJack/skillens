# Contributing to SkiLens

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/YixiaJack/skillens.git
cd skillens
python -m venv .venv
# Linux/Mac:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\activate

pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ -v
pytest tests/ -v --cov=skillens  # with coverage
```

## Code Style

We use `ruff` for linting and formatting:

```bash
ruff check .
ruff format .
```

## Adding a New Provider

This is the most impactful contribution you can make. Each provider extracts metadata from a specific learning platform.

### Step 1: Create the provider file

```python
# skillens/providers/your_platform.py
from __future__ import annotations

import re
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from skillens.core.models import ResourceMeta
from skillens.providers.base import BaseProvider


class YourPlatformProvider(BaseProvider):
    """Provider for yourplatform.com courses."""

    @property
    def name(self) -> str:
        return "your_platform"

    @staticmethod
    def can_handle(url: str) -> bool:
        """Return True if URL belongs to this platform."""
        return bool(re.match(r"https?://(www\.)?yourplatform\.com/", url))

    async def extract(self, url: str) -> ResourceMeta:
        """Extract course metadata from the URL."""
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract whatever metadata is available
        title = soup.find("h1").get_text(strip=True) if soup.find("h1") else "Unknown"
        
        return ResourceMeta(
            title=title,
            url=url,
            source_type="course",  # or "video", "paper", "repo", "book", "article"
            platform=self.name,
            description=self._extract_description(soup),
            syllabus=self._extract_syllabus(soup),
            topics=self._extract_topics(soup),
            rating=self._extract_rating(soup),
            published_date=self._extract_date(soup),
            author=self._extract_author(soup),
        )

    def _extract_description(self, soup: BeautifulSoup) -> str:
        meta = soup.find("meta", attrs={"name": "description"})
        return meta["content"] if meta else ""

    def _extract_syllabus(self, soup: BeautifulSoup) -> list[str]:
        # Platform-specific: find section/chapter headings
        return []

    def _extract_topics(self, soup: BeautifulSoup) -> list[str]:
        # Platform-specific: find skill tags
        return []

    def _extract_rating(self, soup: BeautifulSoup) -> float | None:
        return None

    def _extract_date(self, soup: BeautifulSoup) -> datetime | None:
        return None

    def _extract_author(self, soup: BeautifulSoup) -> str:
        return ""
```

### Step 2: Register the provider

Add your provider to `skillens/providers/registry.py`:

```python
from skillens.providers.your_platform import YourPlatformProvider

PROVIDER_ORDER = [
    # ... existing providers
    YourPlatformProvider,  # Add before WebpageProvider
    WebpageProvider,       # Generic fallback — always last
]
```

### Step 3: Add tests

```python
# tests/providers/test_your_platform.py
import pytest
from skillens.providers.your_platform import YourPlatformProvider


class TestYourPlatformProvider:
    def test_can_handle_valid_url(self):
        assert YourPlatformProvider.can_handle("https://yourplatform.com/course/123")

    def test_can_handle_rejects_other(self):
        assert not YourPlatformProvider.can_handle("https://other.com/course")

    @pytest.mark.asyncio
    async def test_extract_returns_meta(self, respx_mock):
        # Mock the HTTP response
        respx_mock.get("https://yourplatform.com/course/123").respond(
            200,
            html="<html><h1>Test Course</h1></html>",
        )
        
        provider = YourPlatformProvider()
        meta = await provider.extract("https://yourplatform.com/course/123")
        
        assert meta.title == "Test Course"
        assert meta.platform == "your_platform"
```

### Step 4: Open a PR

- Branch name: `provider/your-platform`
- PR title: `feat: add YourPlatform provider`
- Include example URLs you tested against

## Other Ways to Contribute

- **Improve scoring heuristics** in `skillens/core/scorer.py`
- **Add LLM providers** (Google Gemini, local models via llama.cpp, etc.)
- **Improve display** — better terminal layouts, charts
- **Add skill-demand data** — curated datasets mapping skills to market demand
- **i18n** — translate output strings to other languages
- **Write docs** — usage examples, tutorials

## Code of Conduct

Be kind. Be constructive. We're all here to learn.
