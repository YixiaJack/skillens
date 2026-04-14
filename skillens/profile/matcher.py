"""Profile matching — compute how well a resource fits a user's background."""

from __future__ import annotations

import re

from skillens.core.models import ResourceMeta, UserProfile

_WORD_RE = re.compile(r"[a-zA-Z0-9+#.]+")


def _tokens(text: str) -> set[str]:
    return {w.lower() for w in _WORD_RE.findall(text) if len(w) > 1}


def match_score(meta: ResourceMeta, profile: UserProfile) -> int:
    """Score 0-100 based on skill overlap and signal strength.

    Logic:
    - Collect a bag of tokens from resource title/topics/syllabus.
    - Collect a bag of tokens from profile.skills + resume_text.
    - Overlap ratio → 0-70 base. Bonus if target_role keywords appear.
    - If the resource is clearly aimed at a *different* level
      (e.g., all topics already mastered), cap at 50.
    """
    resource_tokens = _tokens(
        " ".join(
            [meta.title, " ".join(meta.topics), " ".join(meta.syllabus), meta.description]
        )
    )
    if not resource_tokens:
        return 50

    profile_tokens: set[str] = set()
    for s in profile.skills:
        profile_tokens |= _tokens(s)
    if profile.resume_text:
        profile_tokens |= _tokens(profile.resume_text)

    if not profile_tokens:
        return 50

    overlap = resource_tokens & profile_tokens
    coverage = len(overlap) / max(len(resource_tokens), 1)
    # Base: how much of the resource maps to things the user already knows.
    # Moderate overlap (0.1–0.4) = sweet spot; too much = redundant.
    if coverage < 0.05:
        base = 35  # Totally new — may be too steep
    elif coverage < 0.15:
        base = 80  # Right stretch
    elif coverage < 0.35:
        base = 70
    elif coverage < 0.6:
        base = 55
    else:
        base = 40  # Mostly redundant

    # Role alignment bonus
    if profile.target_role:
        role_tokens = _tokens(profile.target_role)
        if role_tokens & resource_tokens:
            base = min(base + 10, 100)

    return base
