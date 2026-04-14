"""Deterministic SkiLens demo for README GIF / VHS recording.

Uses fixed fake data so the output is reproducible and network-independent.
Prints the same kind of Rich panel the real CLI produces, then pauses so
VHS can capture the final frame cleanly.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from skillens.core.models import (
    AlternativeResource,
    Assessment,
    ResourceMeta,
    SourceType,
    Verdict,
)
from skillens.display.report import print_report


def build_demo_assessment() -> Assessment:
    meta = ResourceMeta(
        title="Machine Learning — Stanford",
        url="https://www.coursera.org/learn/machine-learning",
        source_type=SourceType.COURSE,
        platform="coursera",
        description="Foundations of machine learning from Andrew Ng.",
        author="Andrew Ng",
        institution="Stanford University",
        rating=4.9,
        review_count=180_000,
        last_updated=datetime(2024, 3, 15, tzinfo=timezone.utc),
        duration_hours=60,
        topics=["machine learning", "regression", "neural networks"],
    )
    return Assessment(
        market_demand=78,
        skill_half_life="~10+ years",
        info_density=62,
        freshness=48,
        effort_vs_return=71,
        overall_score=68,
        verdict=Verdict.LEARN,
        verdict_reason="Foundational ML is timeless, but content predates the transformer era.",
        strengths=[
            "Exceptional pedagogy from Andrew Ng",
            "Covers math foundations thoroughly",
            "Popular — 180,000+ enrolled",
        ],
        concerns=[
            "No coverage of LLMs / transformers",
            "TensorFlow 1.x examples are outdated",
        ],
        alternatives=[],
        discovered_alternatives=[
            AlternativeResource(
                title="Deep RL Course (Hugging Face)",
                url="https://huggingface.co/learn/deep-rl-course",
                platform="huggingface",
                overall_score=82,
                score_delta=14,
                reason="Fresher (2025), hands-on code",
            ),
            AlternativeResource(
                title="Spinning Up in Deep RL (OpenAI)",
                url="https://github.com/openai/spinningup",
                platform="github",
                overall_score=79,
                score_delta=11,
                reason="Excellent info density, free",
            ),
        ],
        resource=meta,
        analysis_mode="quick",
    )


def main() -> None:
    print()
    print("$ skillens \"https://www.coursera.org/learn/machine-learning\"")
    print()
    time.sleep(0.6)
    print_report(build_demo_assessment())
    time.sleep(0.4)


def export_svg(out_path: Path) -> None:
    """Render the demo to an SVG terminal screenshot (GitHub-friendly)."""
    import skillens.display.report as report_mod

    recording_console = Console(
        record=True,
        width=92,
        force_terminal=True,
        color_system="truecolor",
    )
    # Patch the module-level console so print_report uses the recorder.
    original = report_mod.console
    report_mod.console = recording_console
    try:
        recording_console.print()
        recording_console.print(
            '[bold]$[/bold] skillens [green]"https://www.coursera.org/learn/machine-learning"[/green]'
        )
        recording_console.print()
        print_report(build_demo_assessment())
    finally:
        report_mod.console = original

    out_path.parent.mkdir(parents=True, exist_ok=True)
    recording_console.save_svg(
        str(out_path),
        title="SkiLens — is this worth learning?",
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--svg":
        out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/demo.svg")
        export_svg(out)
    else:
        main()
