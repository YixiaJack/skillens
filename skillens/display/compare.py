"""Side-by-side comparison display for two Assessments."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from skillens.core.models import Assessment

console = Console()


def _delta(a: int, b: int) -> str:
    d = a - b
    if d > 0:
        return f"[green]+{d}[/green]"
    if d < 0:
        return f"[red]{d}[/red]"
    return "[dim]0[/dim]"


def _color(score: int) -> str:
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "dark_orange"
    return "red"


def _cell(score: int) -> str:
    return f"[{_color(score)}]{score}[/{_color(score)}]"


def print_compare(a: Assessment, b: Assessment) -> None:
    """Print two assessments side by side with deltas."""
    table = Table(title="🔍 SkiLens — Side-by-side", header_style="bold blue")
    table.add_column("Dimension", style="bold")
    table.add_column(_truncate(a.resource.title, 28))
    table.add_column(_truncate(b.resource.title, 28))
    table.add_column("Δ (A−B)")

    for label, va, vb in [
        ("Market Demand", a.market_demand, b.market_demand),
        ("Info Density", a.info_density, b.info_density),
        ("Freshness", a.freshness, b.freshness),
        ("Effort vs Return", a.effort_vs_return, b.effort_vs_return),
        ("Overall", a.overall_score, b.overall_score),
    ]:
        table.add_row(label, _cell(va), _cell(vb), _delta(va, vb))

    table.add_row(
        "Half-life",
        f"[cyan]{a.skill_half_life}[/cyan]",
        f"[cyan]{b.skill_half_life}[/cyan]",
        "",
    )
    table.add_row(
        "Verdict",
        f"[bold]{a.verdict.value}[/bold]",
        f"[bold]{b.verdict.value}[/bold]",
        "",
    )

    console.print(table)

    winner = a if a.overall_score >= b.overall_score else b
    other = b if winner is a else a
    diff = winner.overall_score - other.overall_score
    console.print(
        f"\n[bold green]→ Winner:[/bold green] {winner.resource.title} "
        f"([bold]+{diff}[/bold] over the alternative)\n"
    )


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"
