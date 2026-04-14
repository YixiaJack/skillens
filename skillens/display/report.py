"""Rich terminal report display for SkiLens assessments."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from skillens.core.models import Assessment, Verdict
from skillens.display.i18n import t

console = Console()


def _score_color(score: int) -> str:
    """Return color name based on score value."""
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "dark_orange"
    return "red"


def _score_bar(score: int, width: int = 10, confidence: float = 1.0) -> str:
    """Render a score as a colored bar with an optional low-confidence marker.

    When confidence < 0.35 we append a dim '⋯' to tell the user this
    dimension's score is essentially a guess.
    """
    filled = round(score / 100 * width)
    empty = width - filled
    color = _score_color(score)
    marker = "  [dim]⋯[/dim]" if confidence < 0.35 else ""
    return f"[{color}]{'█' * filled}[/{color}][dim]{'░' * empty}[/dim]  {score}{marker}"


def _verdict_style(verdict: Verdict) -> str:
    """Return style for verdict text."""
    match verdict:
        case Verdict.LEARN:
            return "bold green"
        case Verdict.SKIP:
            return "bold red"
        case Verdict.CONSIDER_ALTERNATIVES:
            return "bold yellow"


def print_report(assessment: Assessment) -> None:
    """Print a beautiful assessment report to the terminal."""
    meta = assessment.resource
    a = assessment

    # Header
    header = f"[bold]{meta.title}[/bold]"
    if meta.platform != "unknown":
        header += f"  [dim]({meta.platform})[/dim]"

    subtitle_parts = []
    if meta.author:
        subtitle_parts.append(f"by {meta.author}")
    if meta.last_updated:
        subtitle_parts.append(f"Updated: {meta.last_updated.strftime('%Y-%m')}")
    elif meta.published_date:
        subtitle_parts.append(f"Published: {meta.published_date.strftime('%Y-%m')}")
    if meta.duration_hours:
        subtitle_parts.append(f"{meta.duration_hours:.0f}h")
    subtitle = " · ".join(subtitle_parts)

    # Build content
    lines = []
    lines.append(header)
    if subtitle:
        lines.append(f"[dim]{subtitle}[/dim]")
    lines.append("")

    # Low-confidence banner — emitted BEFORE the score bars so users see
    # the warning before they read the (potentially meaningless) numbers.
    if a.overall_confidence < 0.4:
        lines.append(
            "  [yellow on red] ⚠  LOW CONFIDENCE [/yellow on red] "
            "[dim]insufficient metadata — scores below are best-effort[/dim]"
        )
        lines.append("")

    def _conf(dim: str) -> float:
        return a.confidences.get(dim, 1.0)

    # Score bars (per-dimension confidence passed in so low-conf bars get ⋯ marker)
    lines.append(
        f"  {t('label.market_demand'):<17}"
        f"{_score_bar(a.market_demand, confidence=_conf('market_demand'))}"
    )
    lines.append(f"  {t('label.half_life'):<17}[cyan]{a.skill_half_life}[/cyan]")
    lines.append(
        f"  {t('label.info_density'):<17}"
        f"{_score_bar(a.info_density, confidence=_conf('info_density'))}"
    )
    lines.append(
        f"  {t('label.freshness'):<17}"
        f"{_score_bar(a.freshness, confidence=_conf('freshness'))}"
    )
    lines.append(
        f"  {t('label.effort'):<17}"
        f"{_score_bar(a.effort_vs_return, confidence=_conf('effort_vs_return'))}"
    )
    if a.profile_match is not None:
        lines.append(f"  {t('label.profile_match'):<17}{_score_bar(a.profile_match)}")
    lines.append("")
    lines.append(
        f"  [bold]{t('label.overall'):<17}"
        f"{_score_bar(a.overall_score, confidence=a.overall_confidence)}[/bold]"
    )
    lines.append("")

    # Verdict
    verdict_style = _verdict_style(a.verdict)
    verdict_display = t(f"verdict.{a.verdict.value}")
    lines.append(f"  [{verdict_style}]⚡ {t('label.verdict')}: {verdict_display}[/{verdict_style}]")
    lines.append(f"  [dim]→ {a.verdict_reason}[/dim]")

    # Strengths
    if a.strengths:
        lines.append("")
        lines.append(f"  [green]{t('label.strengths')}[/green]")
        for s in a.strengths:
            lines.append(f"  [dim]·[/dim] {s}")

    # Concerns
    if a.concerns:
        lines.append("")
        lines.append(f"  [yellow]{t('label.concerns')}[/yellow]")
        for c in a.concerns:
            lines.append(f"  [dim]·[/dim] {c}")

    # Alternatives
    if a.alternatives:
        lines.append("")
        lines.append(f"  [blue]{t('label.alternatives')}[/blue]")
        for alt in a.alternatives:
            lines.append(f"  [dim]·[/dim] {alt}")

    # ★ Discovered & scored alternatives (the killer feature)
    if a.discovered_alternatives:
        lines.append("")
        lines.append(f"  [bold blue]{t('label.better_alternatives')}[/bold blue]")
        for i, alt in enumerate(a.discovered_alternatives, 1):
            delta_str = f"[green]+{alt.score_delta} ↑[/green]" if alt.score_delta > 0 else f"[red]{alt.score_delta} ↓[/red]"
            lines.append(f"")
            lines.append(f"  [bold]{i}. {alt.title}[/bold]     {alt.overall_score}  {delta_str}")
            lines.append(f"     [dim]├─ {alt.reason}[/dim]")
            if alt.url:
                # Show shortened URL
                short_url = alt.url.replace("https://www.", "").replace("https://", "")
                if len(short_url) > 45:
                    short_url = short_url[:42] + "..."
                lines.append(f"     [dim]└─ {short_url}[/dim]")

    # Mode indicator
    lines.append("")
    mode_label = t(f"mode.{a.analysis_mode}")
    mode_text = f"[dim]{mode_label}"
    if a.model_used:
        mode_text += f" · {a.model_used}"
    mode_text += "[/dim]"
    lines.append(f"  {mode_text}")

    content = "\n".join(lines)

    panel = Panel(
        content,
        title=f"[bold blue]{t('header.skillens')}[/bold blue]",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(panel)
