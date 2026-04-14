<div align="center">

# 🔍 SkiLens

### **Is this worth learning?** Ask *before* you invest 40 hours.

One command. Instant verdict: **LEARN · SKIP · CONSIDER ALTERNATIVES**.

[![PyPI](https://img.shields.io/pypi/v/skillens?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/skillens/)
[![Python](https://img.shields.io/pypi/pyversions/skillens?logo=python&logoColor=white)](https://pypi.org/project/skillens/)
[![License](https://img.shields.io/github/license/YixiaJack/skillens)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-67%20passed-brightgreen)](tests/)
[![Stars](https://img.shields.io/github/stars/YixiaJack/skillens?style=social)](https://github.com/YixiaJack/skillens/stargazers)

```bash
pip install skillens
skillens "https://www.coursera.org/learn/machine-learning"
```

</div>

---

## 😤 The problem

You find a course. It looks promising. **40 hours later**:

- 🕰️ Content is 3 years outdated, pre-transformer era
- 📉 The framework it teaches is getting automated away
- 📚 The same material exists in a 2-hour YouTube video
- 🎯 It doesn't match where your career is actually heading

> *"The hardest part of learning isn't learning — it's deciding what to learn."*

**SkiLens answers "should I learn this?" before you commit.** Paste a URL. Get a verdict in 3 seconds. Optionally find better alternatives.

---

## ⚡ 30-second demo

```bash
$ skillens "https://www.coursera.org/learn/machine-learning"
```

```
╭──────────────────────── 🔍 SkiLens ─────────────────────────╮
│                                                              │
│   Machine Learning — Stanford (coursera)                     │
│   by Andrew Ng · Updated: 2024-03 · 60h                      │
│                                                              │
│   Market Demand    ████████░░  78    ↗ growing               │
│   Skill Half-life  ██████████  ~10y  ✦ evergreen             │
│   Info Density     ██████░░░░  62    → moderate              │
│   Freshness        █████░░░░░  48    ↘ aging                 │
│   Effort vs Return ███████░░░  71    → solid                 │
│                                                              │
│   Overall          ███████░░░  68                            │
│                                                              │
│   ⚡ Verdict: LEARN (with caveats)                           │
│   → Foundational ML is timeless, but content predates        │
│     the transformer era                                      │
│                                                              │
│   ✅ Strengths                                               │
│   · Exceptional pedagogy from Andrew Ng                      │
│   · Covers math foundations thoroughly                       │
│                                                              │
│   ⚠️  Concerns                                               │
│   · No coverage of LLMs / transformers                       │
│   · TensorFlow 1.x examples are outdated                     │
│                                                              │
│   💡 Better Alternatives Found                               │
│                                                              │
│   1. Deep RL Course (Hugging Face)     82  +14 ↑            │
│      ├─ Fresher (2025), hands-on code                        │
│      └─ youtube.com/...                                      │
│                                                              │
│   2. Spinning Up in Deep RL (OpenAI)   79  +11 ↑            │
│      ├─ Excellent info density, free                         │
│      └─ github.com/openai/spinningup                         │
│                                                              │
╰──────────────────────────────────────────────────────────────╯
```

**Zero config. No API key needed.** The killer feature — *discovering better alternatives* — works out of the box.

---

## 🚀 Quick start

```bash
# 1. install
pip install skillens

# 2. point it at anything
skillens "https://..."

# 3. there is no step 3
```

SkiLens auto-detects the platform and extracts the right metadata. No flags, no setup.

---

## 🎯 What gets evaluated

| Dimension | What it measures | How |
|---|---|---|
| **Market Demand** | Is this skill actually in demand? | Bundled skill-demand dataset + popularity proxies |
| **Skill Half-life** | How long until this knowledge is stale? | Topic classification (foundational / established / fast-moving) |
| **Info Density** | How much signal per hour invested? | Syllabus analysis, unique-topic ratio |
| **Freshness** | Is the content up-to-date? | Published / last-updated dates, deprecation detection |
| **Effort vs Return** | Is the time investment justified? | Duration × demand cross-reference |
| **Profile Match** *(optional)* | How well does it fit *your* background? | Token-overlap scoring against your skills / target role |

Scores are combined into a single **0–100 overall**, mapped to one of three verdicts: `LEARN`, `SKIP`, `CONSIDER ALTERNATIVES`.

---

## 🌐 Works on everything

```bash
# URLs — platform auto-detected
skillens "https://www.coursera.org/learn/machine-learning"
skillens "https://youtube.com/watch?v=..."
skillens "https://github.com/openai/gym"
skillens "https://arxiv.org/abs/2301.00001"
skillens "https://any-blog-or-tutorial.com/..."

# Skill / topic — market analysis via web search
skillens topic "reinforcement learning"
skillens topic "rust programming"

# Side-by-side comparison
skillens "https://courseA" --compare "https://courseB"

# JSON output for scripting
skillens "https://..." --json | jq .verdict
```

### Supported platforms

| Platform | Status | What's extracted |
|---|---|---|
| 🎓 **Coursera** | ✅ | Syllabus, rating, enrollment, instructor, institution (via JSON-LD) |
| 📺 **YouTube** | ✅ | Title, views, duration, description, tags (via yt-dlp) |
| 💻 **GitHub** | ✅ | Stars, activity, topics, README, language |
| 📄 **arXiv** | ✅ | Abstract, authors, categories, dates |
| 🌍 **Generic webpage** | ✅ | Open Graph / JSON-LD / meta fallback |
| 🎨 **Plugins** | ✅ | Third-party providers via entry points — see below |

---

## 🧠 Deep mode (optional LLM)

Quick mode (default) needs zero config. For nuanced analysis, plug in any LLM:

```bash
# OpenAI (default)
skillens config set llm openai
skillens config set api-key sk-...
skillens "https://..." --deep

# Anthropic Claude
skillens config set llm anthropic
skillens config set api-key sk-ant-...

# Local Ollama (100% private, $0)
skillens config set llm ollama
skillens config set model llama3.2
```

All three backends use **structured outputs** (OpenAI tool-calling, Anthropic `tool_use`, Ollama JSON schema) — the LLM can't go off-rails and the scores always validate against a Pydantic schema.

Deep mode falls back to quick-mode scoring automatically if the LLM call fails, so `--deep` is always safe to enable.

---

## 👤 Personalize

Tell SkiLens who you are once, and every evaluation gets a personal-fit score:

```bash
skillens profile set --skills "python,pytorch,rl,robotics" \
                     --role "ML engineer" \
                     --years 5
```

```
Market Demand    ████████░░  78
Freshness        █████░░░░░  48
Profile Match    █████████░  85   ← new: strong alignment with your stack
```

The matcher lives at [`skillens/profile/matcher.py`](skillens/profile/matcher.py) — it's pure Python, no LLM needed. Sweet spot is **10–15% token overlap** (new but not redundant); heavy overlap gets penalized as "you already know this".

---

## 🔌 Plugin ecosystem

Add a provider for any platform without forking SkiLens. Third-party packages register via entry points:

```toml
# your-package/pyproject.toml
[project.entry-points."skillens.providers"]
udemy = "my_package.udemy:UdemyProvider"
```

```python
# my_package/udemy.py
from skillens.providers.base import BaseProvider
from skillens.core.models import ResourceMeta, SourceType

class UdemyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "udemy"

    @staticmethod
    def can_handle(url: str) -> bool:
        return "udemy.com/course/" in url

    async def extract(self, url: str) -> ResourceMeta:
        # fetch, parse, return ResourceMeta(...)
        ...
```

`pip install` the package — SkiLens auto-discovers it at runtime. Broken plugins fail silently with a stderr warning; they can't crash the CLI.

---

## 🤖 MCP server mode

Use SkiLens as a tool inside **Claude Desktop**, **Cursor**, or any MCP client:

```bash
pip install "skillens[mcp]"
skillens mcp   # speaks stdio by default
```

Three tools are exposed: `evaluate_url(url)`, `analyze_topic(skill)`, `get_profile()`. Drop this into your Claude Desktop config:

```json
{
  "mcpServers": {
    "skillens": { "command": "skillens", "args": ["mcp"] }
  }
}
```

Now your agent can ask *"is this course worth it?"* mid-conversation and get a structured verdict back.

---

## 🌏 中文 / i18n

```bash
skillens "https://bilibili.com/video/BV1..." --lang zh
```

```
│   市场需求       ████████░░  78                             │
│   技能半衰期     ██████████  ~10y                           │
│   信息密度       ██████░░░░  62                             │
│                                                              │
│   ⚡ 结论: 值得学                                            │
```

Currently `en` and `zh`. Auto-detects Chinese from `.bilibili.com` / `.zhihu.com` / `.cn` URLs when `--lang auto` is set.

---

## 🛠️ Architecture

```
skillens/
├── cli.py               Typer CLI with bare-URL injection
├── core/
│   ├── evaluator.py     Pipeline orchestrator
│   ├── scorer.py        Rule-based + LLM scoring engine
│   ├── dataset.py       Bundled skill-demand dataset
│   ├── config.py        ~/.skillens/config.toml
│   └── models.py        Pydantic data models
├── providers/           Coursera · YouTube · GitHub · arXiv · Webpage + plugins
├── llm/                 OpenAI · Anthropic · Ollama backends + factory
├── discovery/           ★ Alternative-resource discovery via DDG
├── market/              Skill/topic trend analysis
├── profile/             Profile storage + token-overlap matcher
├── display/             Rich panels · JSON · compare table · i18n
├── mcp_server.py        FastMCP server exposing evaluate_url / analyze_topic
└── data/
    └── skill_demand.json  2026.04 curated keyword → demand map
```

---

## 📦 Install options

```bash
pip install skillens                    # base — zero config, works immediately
pip install "skillens[youtube]"         # adds yt-dlp for rich YouTube metadata
pip install "skillens[llm]"             # adds openai + anthropic
pip install "skillens[discover]"        # adds DuckDuckGo search for alternatives
pip install "skillens[mcp]"             # adds MCP server support
pip install "skillens[pdf]"             # adds PyMuPDF for local PDFs
pip install "skillens[all]"             # everything
```

---

## 🧪 Development

```bash
git clone https://github.com/YixiaJack/skillens
cd skillens
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -e ".[dev]"
pytest                                               # 67 tests, ~0.4s
```

Pass rate: **67 / 67** ✅ (1 MCP test skips when the optional `mcp` extra isn't installed, as designed).

---

## 🤝 Contributing

The easiest contribution is a **new provider**. The [Plugin ecosystem](#-plugin-ecosystem) section shows the full template — you don't even need to fork SkiLens, just ship your own package with the right entry point.

Other welcome contributions:
- New language packs in [`display/i18n.py`](skillens/display/i18n.py)
- Skill-demand dataset updates in [`data/skill_demand.json`](skillens/data/skill_demand.json)
- New LLM backends in [`llm/`](skillens/llm/)

See [CONTRIBUTING.md](CONTRIBUTING.md) for full details.

---

## 🗺️ Roadmap

- [x] Core CLI + rule-based scoring engine
- [x] YouTube · Coursera · GitHub · arXiv · Webpage providers
- [x] Rich terminal output with score bars
- [x] JSON output mode
- [x] Alternative-resource discovery (the ★ killer feature)
- [x] OpenAI / Anthropic / Ollama deep mode
- [x] Profile management + personal match scoring
- [x] `--compare` side-by-side mode
- [x] Bundled skill-demand dataset
- [x] MCP server mode
- [x] Chinese output (`--lang zh`)
- [x] Provider plugin system via entry points
- [ ] VS Code extension wrapper
- [ ] Browser extension (evaluate as you browse)
- [ ] Obsidian plugin integration
- [ ] Auto-updating dataset via scheduled GitHub Action

---

## 🧭 Philosophy

> In a world with infinite content, **curation is the bottleneck**.
>
> SkiLens shifts evaluation from *"after 40 hours"* to *"before the first hour."*

Three invariants the project will never break:

1. **5-second first result.** Rule-based scoring always beats the LLM to the punch.
2. **Zero config for basic use.** `pip install && skillens URL` must just work.
3. **The terminal *is* the product.** No web dashboard. No SaaS. Forever.

---

## 📄 License

MIT — do whatever you want with it.

---

<div align="center">

**If SkiLens saved you from a bad course, give it a ⭐**

Built with 🔥 by [@YixiaJack](https://github.com/YixiaJack)

</div>
