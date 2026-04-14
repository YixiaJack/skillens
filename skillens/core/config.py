"""Configuration storage (`~/.skillens/config.toml`).

Keys:
    llm: "openai" | "anthropic" | "ollama" | "none"
    api_key: string
    model: string
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]


def config_dir() -> Path:
    return Path(os.environ.get("SKILLENS_HOME") or Path.home() / ".skillens")


def config_path() -> Path:
    return config_dir() / "config.toml"


def load_config() -> dict[str, Any]:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(data: dict[str, Any]) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    lines = []
    for k, v in data.items():
        if isinstance(v, str):
            escaped = v.replace('"', '\\"')
            lines.append(f'{k} = "{escaped}"')
        elif isinstance(v, bool):
            lines.append(f"{k} = {'true' if v else 'false'}")
        else:
            lines.append(f"{k} = {v}")
    config_path().write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_value(key: str, value: str) -> None:
    data = load_config()
    data[key.replace("-", "_")] = value
    save_config(data)


def get_value(key: str, default: str | None = None) -> str | None:
    return load_config().get(key.replace("-", "_"), default)
