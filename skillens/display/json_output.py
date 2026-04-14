"""JSON output mode for piping and scripting."""

from __future__ import annotations

import json

from skillens.core.models import Assessment


def print_json(assessment: Assessment) -> None:
    """Print assessment as JSON to stdout."""
    data = assessment.model_dump(mode="json")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))
