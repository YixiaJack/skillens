"""User profile storage (`~/.skillens/profile.json`)."""

from __future__ import annotations

import json

from skillens.core.config import config_dir
from skillens.core.models import UserProfile


def profile_path():
    return config_dir() / "profile.json"


def load_profile() -> UserProfile | None:
    path = profile_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return UserProfile(**data)
    except Exception:
        return None


def save_profile(profile: UserProfile) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    profile_path().write_text(
        json.dumps(profile.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def clear_profile() -> None:
    path = profile_path()
    if path.exists():
        path.unlink()


def update_profile(**fields) -> UserProfile:
    """Merge fields into the existing profile (or create a new one)."""
    current = load_profile() or UserProfile()
    data = current.model_dump()
    for k, v in fields.items():
        if v is not None:
            data[k] = v
    new = UserProfile(**data)
    save_profile(new)
    return new
