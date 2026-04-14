# CLAUDE.md — SkiLens Development Guide

## Project Overview

**SkiLens** is an open-source Python CLI tool that evaluates whether a learning resource (course, book, paper, tutorial, repo) is worth your time. It analyzes from macro (industry demand, skill half-life) to micro (information density, freshness, difficulty match).

One command. Instant verdict: **LEARN / SKIP / CONSIDER ALTERNATIVES**.

```bash
pip install skillens
skillens "https://www.coursera.org/learn/machine-learning"
```

## Core Philosophy

1. **5-second first result.** The first output must appear within 5 seconds. Use a fast rule-based engine for initial scoring. LLM deep analysis is optional (`--deep`).
2. **Beautiful terminal output.** Use `rich` library for all output — panels, progress bars, colored scores. The terminal IS the product.
3. **URL-first design.** Most users will paste a URL. File and topic modes are secondary.
4. **Pluggable architecture.** Each data source (Coursera, YouTube, arXiv, GitHub, etc.) is a separate provider. Community can contribute new providers via PR.
5. **Model-agnostic.** Support OpenAI, Anthropic, Ollama (local), and a no-LLM fallback mode.

## Architecture

```
skillens/
├── cli.py              # Typer CLI entry point
├── core/
│   ├── evaluator.py    # Main evaluation orchestrator
│   ├── scorer.py       # Scoring engine (rule-based + LLM)
│   ├── models.py       # Pydantic data models
│   └── config.py       # Configuration management
├── providers/          # One file per data source
│   ├── base.py         # Abstract base provider
│   ├── coursera.py
│   ├── youtube.py
│   ├── github_repo.py
│   ├── arxiv.py
│   ├── webpage.py      # Generic webpage fallback
│   ├── local_file.py   # PDF, MD, TXT files
│   └── registry.py     # Provider auto-detection from URL
├── discovery/          # ★ Alternative resource discovery
│   ├── searcher.py     # Web search for alternative resources
│   ├── ranker.py       # Quick-score & rank alternatives
│   └── sources.py      # Search query builders per platform
├── market/             # Market demand analysis
│   ├── jobs.py         # Job market signals (web search based)
│   └── trends.py       # Skill trend analysis
├── llm/                # LLM integration layer
│   ├── base.py         # Abstract LLM interface
│   ├── openai.py
│   ├── anthropic.py
│   ├── ollama.py
│   └── nollm.py        # No-LLM fallback (rule-based only)
├── display/            # Terminal UI rendering
│   ├── report.py       # Rich panel output
│   ├── json_output.py  # JSON output for piping
│   └── colors.py       # Color scheme constants
├── profile/            # User profile management
│   ├── manager.py      # Profile CRUD
│   └── matcher.py      # Skill matching logic
└── utils/
    ├── fetcher.py      # httpx async URL fetcher
    ├── text.py         # Text analysis utilities
    └── cache.py        # Response caching (SQLite)
```

## Data Models

### ResourceMeta (extracted from provider)

```python
class ResourceMeta(BaseModel):
    title: str
    url: str | None = None
    source_type: str  # "course", "video", "paper", "repo", "book", "article"
    platform: str     # "coursera", "youtube", "arxiv", "github", etc.
    
    # Content signals
    description: str = ""
    syllabus: list[str] = []        # Chapter/section titles
    topics: list[str] = []          # Extracted skill/topic tags
    language: str = "en"
    
    # Quality signals
    rating: float | None = None     # Platform rating (0-5)
    review_count: int | None = None
    enrollment_count: int | None = None
    star_count: int | None = None   # For GitHub repos
    citation_count: int | None = None  # For papers
    
    # Time signals
    published_date: datetime | None = None
    last_updated: datetime | None = None
    duration_hours: float | None = None
    
    # Author signals
    author: str = ""
    author_credentials: str = ""
    institution: str = ""
    
    # Content for analysis (truncated)
    content_sample: str = ""  # First ~2000 chars of actual content
```

### Assessment (output)

```python
class Assessment(BaseModel):
    # Scores (0-100)
    market_demand: int          # How hot is this skill in the job market
    skill_half_life: str        # Estimated: "~6 months", "~2 years", "~10 years"
    info_density: int           # New concepts per unit content
    freshness: int              # How up-to-date is the content
    effort_vs_return: int       # ROI of time investment
    profile_match: int | None   # Match with user's background (if profile set)
    
    # Overall
    overall_score: int          # Weighted composite
    verdict: str                # "LEARN" | "SKIP" | "CONSIDER_ALTERNATIVES"
    verdict_reason: str         # One-line explanation
    
    # Details
    strengths: list[str]        # 2-3 bullet points
    concerns: list[str]         # 2-3 bullet points
    alternatives: list[str]     # 2-3 suggested alternatives
    
    # Meta
    analysis_mode: str          # "quick" | "deep"
    model_used: str | None      # LLM model used, if any
    timestamp: datetime
```

## CLI Interface

### Primary Commands

```bash
# Evaluate a URL (auto-detect provider)
skillens "https://www.coursera.org/learn/machine-learning"
skillens "https://youtube.com/watch?v=dQw4w9WgXcQ"
skillens "https://github.com/openai/gym"
skillens "https://arxiv.org/abs/2301.00001"

# Evaluate a local file
skillens analyze paper.pdf
skillens analyze syllabus.md

# Evaluate a skill/topic (market analysis only)
skillens topic "reinforcement learning"
skillens topic "rust programming"

# Profile management
skillens profile set --github YixiaJack
skillens profile set --skills "python,pytorch,RL,robotics"
skillens profile set --resume resume.pdf
skillens profile show
skillens profile clear

# Configuration
skillens config set llm openai          # or anthropic, ollama, none
skillens config set api-key <key>
skillens config set model gpt-4o-mini   # specific model
```

### Flags

```bash
--deep          # Use LLM for deep analysis (slower, better)
--json          # Output as JSON (for piping)
--no-color      # Disable color output
--no-cache      # Skip cache
--lang zh       # Output language (default: auto-detect from URL)
--compare URL2  # Compare two resources side by side
--provider NAME # Force a specific provider
--verbose       # Show debug info
```

## Provider Implementation Guide

Each provider must implement:

```python
class BaseProvider(ABC):
    """Base class for all resource providers."""
    
    @staticmethod
    @abstractmethod
    def can_handle(url: str) -> bool:
        """Return True if this provider can handle the given URL."""
        pass
    
    @abstractmethod
    async def extract(self, url: str) -> ResourceMeta:
        """Extract metadata from the URL."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display."""
        pass
```

### Provider Registry (auto-detection)

```python
# registry.py iterates all providers and calls can_handle()
# First match wins. Order matters — specific providers before generic.
PROVIDER_ORDER = [
    CourseraProvider,
    YouTubeProvider,
    GitHubRepoProvider,
    ArXivProvider,
    # ... more specific providers
    WebpageProvider,  # Generic fallback — always last
]
```

## Scoring Engine

### Quick Mode (rule-based, no LLM)

Score each dimension using heuristics:

1. **Market Demand (0-100):** Derived from topic keywords matched against a bundled skill-demand dataset (updated quarterly). For `--deep` mode, supplements with live web search for job postings.

2. **Skill Half-life:** Classify topic into categories:
   - Foundational (math, algorithms, data structures): ~10+ years
   - Established frameworks (React, PyTorch): ~3-5 years  
   - Cutting-edge tools (specific LLM wrappers): ~6-18 months
   - Use a keyword-to-category mapping, extensible via config.

3. **Info Density (0-100):** 
   - Syllabus analysis: unique topic count / total sections
   - If content available: unique technical terms / word count
   - Penalize: excessive intros, repetitive content, filler

4. **Freshness (0-100):**
   - Based on `last_updated` or `published_date` relative to now
   - Penalize if referencing deprecated tools/versions (detected via keyword matching)
   - Bonus if referencing latest versions

5. **Effort vs Return (0-100):**
   - Cross-reference estimated duration with market demand
   - Short + high demand = high score
   - Long + low demand = low score

### Deep Mode (LLM-enhanced)

Send `ResourceMeta` to LLM with this prompt structure:

```
You are a learning advisor. Analyze this learning resource and provide scores.

Resource: {title}
Platform: {platform}
Published: {published_date}
Duration: {duration_hours}h
Syllabus: {syllabus}
Content sample: {content_sample}
Topics: {topics}

Evaluate on these dimensions (0-100):
1. Market Demand: How valuable is this skill in the current job market?
2. Info Density: How much useful, non-redundant information does this contain?
3. Freshness: Is the content up-to-date with current best practices?
4. Effort vs Return: Is the time investment justified by the learning outcome?

Also provide:
- 2-3 specific strengths
- 2-3 specific concerns
- 2-3 alternative resources that might be better
- A one-line verdict reason

Respond in JSON format.
```

## ★ Discovery Engine (Alternative Recommendation)

**This is the killer feature.** SkiLens doesn't just say "this course is 60/100" — it actively searches for better alternatives, quick-scores them, and shows a ranked comparison. The tool is a learning **advisor**, not just a **scorer**.

### Pipeline

```
User input URL
     │
     ▼
[1] Extract metadata (provider)
     │
     ▼
[2] Score the input resource
     │
     ▼
[3] Extract key topics from resource ──────────────────┐
     │                                                  │
     ▼                                                  ▼
[4] Build search queries per platform      "reinforcement learning course"
     │                                     "RL tutorial 2025"
     ▼                                     "policy gradient PyTorch"
[5] Web search for alternatives ───────────────────────┐
     │                                                  │
     ▼                                                  ▼
[6] Quick-extract metadata from top results    (Coursera, YouTube, GitHub, arXiv hits)
     │
     ▼
[7] Quick-score each alternative (same scorer)
     │
     ▼
[8] Rank by overall_score, filter out duplicates & the input itself
     │
     ▼
[9] Display top 3 alternatives WITH their scores vs. input
```

### Implementation: `skillens/discovery/`

#### `searcher.py` — Find alternative resources

```python
"""Search the web for alternative learning resources on the same topic."""

from __future__ import annotations

import httpx

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
    async with httpx.AsyncClient() as client:
        for query in queries:
            urls = await _web_search(client, query, max_per_query=5)
            candidate_urls.extend(urls)
    
    # Deduplicate and remove input URL
    seen = set()
    unique = []
    for url in candidate_urls:
        normalized = url.rstrip("/").lower()
        if normalized not in seen and normalized != (meta.url or "").rstrip("/").lower():
            seen.add(normalized)
            unique.append(url)
    
    return unique[:max_results]


def _extract_search_keywords(meta: ResourceMeta) -> list[str]:
    """Extract 2-3 core topic keywords from resource metadata.
    
    Priority:
    1. Explicit topics/tags from metadata
    2. Key nouns from title (strip platform names, "course", "tutorial" etc.)
    3. Syllabus section titles (most specific/unique ones)
    """
    # TODO: Implement keyword extraction
    # Use meta.topics if available, else parse meta.title
    if meta.topics:
        return meta.topics[:3]
    
    # Fallback: use title words, filtering stop words
    stop_words = {"course", "tutorial", "introduction", "complete", "guide",
                  "learn", "beginner", "advanced", "the", "a", "an", "for", "to",
                  "with", "and", "in", "on", "of"}
    words = [w for w in meta.title.lower().split() if w not in stop_words and len(w) > 2]
    return words[:3]


def _build_queries(keywords: list[str], source_type: str) -> list[str]:
    """Build search queries targeting different platforms.
    
    For a resource about "reinforcement learning":
    - "reinforcement learning course 2025 site:coursera.org"
    - "reinforcement learning tutorial site:youtube.com"  
    - "reinforcement learning site:github.com stars:>1000"
    - "reinforcement learning" (general, catches blogs/books)
    """
    topic = " ".join(keywords)
    import datetime
    year = datetime.datetime.now().year
    
    queries = [
        f"{topic} course {year}",                    # General course search
        f"{topic} tutorial site:youtube.com",         # YouTube
        f"{topic} site:github.com",                   # GitHub repos
        f"{topic} best resource {year}",              # Meta-recommendations
    ]
    return queries


async def _web_search(client: httpx.AsyncClient, query: str, max_per_query: int = 5) -> list[str]:
    """Run a web search and return result URLs.
    
    Uses DuckDuckGo HTML search (no API key needed) or 
    Google Custom Search API if configured.
    
    TODO: Implement actual web search
    For MVP, can use:
    - duckduckgo-search Python package (pip install duckduckgo-search)
    - Or httpx GET to DuckDuckGo HTML and parse results
    - Or Google Custom Search API (requires key)
    """
    return []
```

#### `ranker.py` — Quick-score and rank alternatives

```python
"""Quick-score discovered alternatives and rank them against the input."""

from __future__ import annotations

from skillens.core.models import Assessment, ResourceMeta
from skillens.core.scorer import score_resource


class AlternativeResult:
    """A scored alternative with comparison to the original."""
    def __init__(self, assessment: Assessment, score_delta: int):
        self.assessment = assessment
        self.score_delta = score_delta  # positive = better than input
    
    @property
    def is_better(self) -> bool:
        return self.score_delta > 5  # Need meaningful difference


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
        Top alternatives sorted by score, best first
    """
    from skillens.discovery.searcher import search_alternatives
    from skillens.providers.registry import detect_provider
    
    # Step 1: Search for candidate URLs
    candidate_urls = await search_alternatives(input_meta)
    
    # Step 2: Extract & score each candidate (with timeout/error handling)
    results: list[AlternativeResult] = []
    for url in candidate_urls:
        try:
            provider = detect_provider(url)
            alt_meta = await provider.extract(url)
            alt_assessment = score_resource(alt_meta, deep=False)
            delta = alt_assessment.overall_score - input_score
            results.append(AlternativeResult(alt_assessment, delta))
        except Exception:
            continue  # Skip failures silently
    
    # Step 3: Sort by score (best first) and return top N
    results.sort(key=lambda r: r.assessment.overall_score, reverse=True)
    return results[:max_alternatives]
```

### Display: Alternatives Section

When alternatives are found, the terminal output adds a comparison section:

```
│  💡 Better Alternatives Found                    │
│                                                  │
│  1. Deep RL Course (Hugging Face)     82  +14 ↑  │
│     ├─ Fresher (2025), hands-on code             │
│     └─ youtube.com/watch?v=...                   │
│                                                  │
│  2. Spinning Up in Deep RL (OpenAI)   79  +11 ↑  │
│     ├─ Excellent info density, free              │
│     └─ github.com/openai/spinningup             │
│                                                  │
│  3. RL Specialization (Coursera)      71   +3 ↑  │
│     ├─ More structured, with cert               │
│     └─ coursera.org/specializations/...          │
```

Key design:
- Show the **score delta** (`+14 ↑`) so users instantly see how much better each alternative is
- Show **one-line reason** why it's better (fresher? denser? shorter?)
- Show the **URL** so users can go directly
- Only show alternatives that score **higher** than the input. If none found, say "No clearly better alternatives found for this topic."

### Flags

```bash
--no-discover     # Skip alternative search (faster)
--discover-only   # ONLY search for alternatives, don't score the input
--max-alt 5       # Return more alternatives (default: 3)
```

### Technical Notes

1. **Web search without API key:** Use `duckduckgo-search` package (MIT license, no key needed). Add as optional dependency: `pip install skillens[discover]`.

2. **Rate limiting:** Max 5 search queries per evaluation. Each query returns max 5 URLs. So max 25 candidates to evaluate. With async extraction this takes ~5-10 seconds.

3. **Caching:** Cache discovered alternatives per topic (not per URL) in `~/.skillens/cache.db`. TTL: 7 days. Same topic = same alternatives.

4. **Deduplication:** Normalize URLs before comparing. Same course on different URLs (e.g., with tracking params) should be deduped.

5. **Quality filter:** Only include alternatives with `overall_score >= 40`. Don't recommend garbage just because it exists.

### Phase Priority

This goes into **Phase 2** (after core providers work). The pipeline is:
- Phase 2a: Implement `searcher.py` with DuckDuckGo search
- Phase 2b: Implement `ranker.py` connecting searcher → providers → scorer
- Phase 2c: Update `evaluator.py` to call discovery after scoring
- Phase 2d: Update `display/report.py` with alternatives comparison section

## Display Design

### Main Report Panel

Use `rich` library. The report should look like this in the terminal:

```
╭──────────────────────────────────────────────────╮
│  🔍 SkiLens Assessment                          │
│                                                  │
│  Machine Learning — Stanford (Coursera)          │
│  by Andrew Ng · Last updated: 2024-03 · 60h     │
├──────────────────────────────────────────────────┤
│                                                  │
│  Market Demand    ████████░░  78    ↗ growing    │
│  Skill Half-life  ██████████  ~10y  ✦ evergreen │
│  Info Density     ██████░░░░  62    → moderate   │
│  Freshness        █████░░░░░  48    ↘ aging      │
│  Effort vs Return ███████░░░  71    → solid      │
│                                                  │
│  Overall          ███████░░░  68                 │
├──────────────────────────────────────────────────┤
│                                                  │
│  ⚡ Verdict: LEARN (with caveats)                │
│  → Foundational ML knowledge is timeless, but    │
│    content predates transformer era              │
│                                                  │
│  ✅ Strengths                                    │
│  · Exceptional pedagogy from Andrew Ng           │
│  · Covers math foundations thoroughly            │
│                                                  │
│  ⚠️  Concerns                                    │
│  · No coverage of LLMs/transformers              │
│  · TensorFlow 1.x examples are outdated          │
│                                                  │
│  💡 Alternatives                                 │
│  · fast.ai Practical Deep Learning (2024)        │
│  · Stanford CS229 updated lectures               │
│                                                  │
╰──────────────────────────────────────────────────╯
```

Use these colors:
- Score ≥ 80: green
- Score 60-79: yellow  
- Score 40-59: orange/dim yellow
- Score < 40: red
- Verdict LEARN: bold green
- Verdict SKIP: bold red
- Verdict CONSIDER_ALTERNATIVES: bold yellow

## Technical Requirements

### Dependencies (keep minimal)

```
typer[all]>=0.9.0        # CLI framework
rich>=13.0               # Terminal UI
httpx>=0.25.0            # Async HTTP client
pydantic>=2.0            # Data models
beautifulsoup4>=4.12     # HTML parsing
yt-dlp                   # YouTube metadata (optional dep)
pymupdf>=1.23            # PDF text extraction (optional dep)
openai>=1.0              # OpenAI API (optional dep)
anthropic>=0.20          # Anthropic API (optional dep)
```

### Python Version
- Minimum: Python 3.10 (for `match` statements and `X | Y` union types)
- Target: Python 3.11+

### Testing
- Use `pytest` with `pytest-asyncio`
- Mock all HTTP calls in tests
- Each provider must have at least 3 test cases
- Score engine must have deterministic test cases

### Caching
- Cache fetched metadata in `~/.skillens/cache.db` (SQLite)
- Cache key: URL hash
- Default TTL: 24 hours
- `--no-cache` flag bypasses cache

### Config Storage
- Config file: `~/.skillens/config.toml`
- Profile file: `~/.skillens/profile.json`

## Development Workflow

```bash
# Setup
git clone https://github.com/YixiaJack/skillens.git
cd skillens
python -m venv .venv && source .venv/bin/activate  # or on Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Run
skillens "https://..."

# Test
pytest tests/ -v

# Lint
ruff check .
ruff format .
```

## Implementation Priority

### Phase 1: MVP (ship this first)
1. CLI skeleton with Typer
2. YouTube provider (easiest — yt-dlp handles everything)
3. Generic webpage provider (fallback)
4. Rule-based scorer (no LLM needed)
5. Rich terminal output
6. JSON output mode
7. Basic README with demo GIF

### Phase 2: Core Providers
1. Coursera provider
2. GitHub repo provider
3. arXiv provider
4. `skillens topic` command with web search
5. OpenAI LLM integration for `--deep` mode

### Phase 3: Personalization
1. Profile management
2. Profile matching in scorer
3. `--compare` mode
4. Anthropic + Ollama LLM backends

### Phase 4: Community
1. Provider plugin system
2. MCP server mode
3. Bundled skill-demand dataset (auto-updated)
4. i18n (Chinese output support)

## Code Style

- Use `async/await` for all I/O operations
- Type hints on all functions
- Docstrings on all public methods
- No classes where a function suffices
- Prefer composition over inheritance (except providers)
- Error messages must be human-readable, never tracebacks for users
- All user-facing strings go through a central display layer

## Key Design Decisions

1. **Why Typer over Click?** Typer auto-generates help docs and is more Pythonic. It's built on Click anyway.
2. **Why not Playwright/Selenium for scraping?** Too heavy as a dependency. Use httpx + BeautifulSoup for HTML, platform APIs where available. Keep `pip install` fast.
3. **Why SQLite for cache instead of filesystem?** Atomic writes, TTL queries, single file. No edge cases with file paths.
4. **Why rule-based scoring as default?** Most users won't have API keys. The tool must be useful with zero configuration. LLM is an enhancement, not a requirement.
5. **Why not a web app?** CLI is the optimal form for GitHub virality. Web app can be built later by community using `--json` output.

## Important Notes

- This is an open-source project targeting GitHub trending. README quality and demo GIF are as important as code quality.
- The tool must work with `pip install skillens && skillens "URL"` — zero config required for basic use.
- Never require an API key for basic functionality. The no-LLM mode must still produce useful results.
- Keep the total dependency count under 10 for the base install. Use optional dependency groups for LLM providers and PDF support.
