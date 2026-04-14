"""Bundled skill-demand dataset loader.

The dataset lives at `skillens/data/skill_demand.json` and maps skill
keywords to a demand score (0-100). Loaded once, cached in-process.
"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files


@lru_cache(maxsize=1)
def _load() -> dict[str, int]:
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
    return {k.lower(): int(v) for k, v in (data.get("skills") or {}).items()}


def demand_for(keywords: list[str], title: str = "") -> int | None:
    """Return the max demand score across matching keywords, or None.

    Matches on substring — e.g., a resource topic "Deep RL" matches the
    "reinforcement learning" key if either side contains the other.
    """
    table = _load()
    if not table:
        return None

    haystack = " ".join([title, *keywords]).lower()
    best: int | None = None
    for key, score in table.items():
        if key in haystack:
            if best is None or score > best:
                best = score
    return best
