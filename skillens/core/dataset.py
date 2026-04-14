"""Bundled skill-demand dataset loader.

The dataset lives at `skillens/data/skill_demand.json` and maps skill
keywords to a (demand, halflife_days) pair. Loaded once, cached in-process.

Schema:
    {
      "_meta": {...},
      "skills": {
        "pytorch": {"demand": 88, "halflife_days": 1825},
        ...
      }
    }
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files


@dataclass(frozen=True)
class SkillEntry:
    demand: int
    halflife_days: int


# Default half-life for skills NOT in the dataset — "moderate churn, ~3 years".
# Used as a conservative middle ground when we have no real signal.
DEFAULT_HALFLIFE_DAYS = 1095


@lru_cache(maxsize=1)
def _load() -> dict[str, SkillEntry]:
    try:
        text = files("skillens.data").joinpath("skill_demand.json").read_text(
            encoding="utf-8"
        )
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    raw_skills = data.get("skills") or {}
    out: dict[str, SkillEntry] = {}
    for key, value in raw_skills.items():
        if isinstance(value, dict):
            out[key.lower()] = SkillEntry(
                demand=int(value.get("demand", 50)),
                halflife_days=int(value.get("halflife_days", DEFAULT_HALFLIFE_DAYS)),
            )
        else:
            # Back-compat: old format where value was just an int.
            out[key.lower()] = SkillEntry(
                demand=int(value),
                halflife_days=DEFAULT_HALFLIFE_DAYS,
            )
    return out


def _matching_entries(keywords: list[str], title: str) -> list[SkillEntry]:
    """Return all SkillEntries whose key appears as a whole-word-ish match
    in the title + keywords haystack.

    We match on word boundaries (after lowercasing and collapsing dots/plus
    signs into word chars so "c++" and "next.js" still work) so that short
    keys like "go" don't accidentally match inside "alGOrithm".
    """
    table = _load()
    if not table:
        return []

    haystack = " ".join([title, *keywords]).lower()
    # Normalize: replace non-alphanumeric (except +# that are part of c++/c#)
    # with spaces, then collapse whitespace.
    normalized = re.sub(r"[^a-z0-9+#\-. ]+", " ", haystack)
    normalized = f" {re.sub(r'\\s+', ' ', normalized)} "

    matches: list[SkillEntry] = []
    for key, entry in table.items():
        # Pad the key with spaces to force word-boundary semantics against
        # the padded haystack. Works for multi-word keys ("machine learning").
        if f" {key} " in normalized:
            matches.append(entry)
    return matches


def demand_for(keywords: list[str], title: str = "") -> int | None:
    """Return the HIGHEST demand across matching entries, or None.

    "Highest demand" is right here: if a resource touches multiple skills,
    the hottest one is what makes it worth learning — a course covering
    both `sql` (80) and `llm` (95) should score as an LLM course.
    """
    matches = _matching_entries(keywords, title)
    if not matches:
        return None
    return max(m.demand for m in matches)


def halflife_for(keywords: list[str], title: str = "") -> int:
    """Return the SHORTEST half-life across matching entries.

    "Shortest" is right here: a course bundling stable fundamentals with
    one fast-moving tool decays at the speed of the fastest-moving piece.
    The LangChain section is what makes the whole tutorial obsolete.

    Falls back to DEFAULT_HALFLIFE_DAYS when nothing matches, so the
    exponential-decay freshness formula always has a denominator.
    """
    matches = _matching_entries(keywords, title)
    if not matches:
        return DEFAULT_HALFLIFE_DAYS
    return min(m.halflife_days for m in matches)
