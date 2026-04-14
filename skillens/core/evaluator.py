"""Main evaluation orchestrator.

This module ties together providers, scorer, and display to produce
a complete assessment of a learning resource.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

from skillens.core.models import Assessment

console = Console()


async def run_evaluation(
    url: str,
    deep: bool = False,
    json_output: bool = False,
    no_cache: bool = False,
    compare_url: str | None = None,
    force_provider: str | None = None,
    lang: str = "auto",
    verbose: bool = False,
) -> None:
    """Run a full evaluation pipeline for a URL.

    Pipeline:
    1. Detect provider (or use forced provider)
    2. Check cache (unless --no-cache)
    3. Extract metadata via provider
    4. Score via rule-based engine
    5. If --deep, enhance with LLM analysis
    6. ★ Search for better alternatives, quick-score them
    7. Display results (rich panel or JSON)
    """
    # TODO: Implement full pipeline
    # This is the skeleton for Claude Code to fill in.

    from skillens.display.i18n import resolve_lang, set_lang

    set_lang(resolve_lang(lang, url))

    if compare_url:
        await run_compare(url, compare_url, deep=deep)
        return

    from skillens.providers.registry import detect_provider

    with console.status("[bold blue]Analyzing...[/bold blue]"):
        # Step 1: Detect provider
        provider = detect_provider(url, force_name=force_provider)
        if verbose:
            console.print(f"[dim]Provider: {provider.name}[/dim]")

        # Step 2: Extract metadata
        meta = await provider.extract(url)
        if verbose:
            console.print(f"[dim]Extracted: {meta.title}[/dim]")

        # Step 3: Score
        from skillens.core.scorer import score_resource, score_resource_deep

        if deep:
            from skillens.llm.factory import get_backend

            assessment = await score_resource_deep(meta, backend=get_backend())
        else:
            assessment = score_resource(meta, deep=False)

    # Step 4: Discover better alternatives
    no_discover = False  # TODO: wire up --no-discover flag
    if not no_discover:
        with console.status("[bold blue]Searching for better alternatives...[/bold blue]"):
            from skillens.discovery.ranker import discover_and_rank

            alt_results = await discover_and_rank(
                input_meta=meta,
                input_score=assessment.overall_score,
                max_alternatives=3,
            )

            # Attach discovered alternatives to assessment
            from skillens.core.models import AlternativeResource

            for alt in alt_results:
                if alt.is_better:
                    a = alt.assessment
                    assessment.discovered_alternatives.append(
                        AlternativeResource(
                            title=a.resource.title,
                            url=a.resource.url or "",
                            platform=a.resource.platform,
                            overall_score=a.overall_score,
                            score_delta=alt.score_delta,
                            reason=_summarize_why_better(a, assessment),
                        )
                    )

    # Step 4: Display
    if json_output:
        from skillens.display.json_output import print_json

        print_json(assessment)
    else:
        from skillens.display.report import print_report

        print_report(assessment)


async def run_compare(url_a: str, url_b: str, deep: bool = False) -> None:
    """Evaluate two resources and display them side by side."""
    from skillens.core.scorer import score_resource, score_resource_deep
    from skillens.providers.registry import detect_provider

    with console.status("[bold blue]Comparing two resources...[/bold blue]"):
        pa = detect_provider(url_a)
        pb = detect_provider(url_b)
        meta_a = await pa.extract(url_a)
        meta_b = await pb.extract(url_b)
        if deep:
            from skillens.llm.factory import get_backend

            backend = get_backend()
            a = await score_resource_deep(meta_a, backend=backend)
            b = await score_resource_deep(meta_b, backend=backend)
        else:
            a = score_resource(meta_a)
            b = score_resource(meta_b)

    from skillens.display.compare import print_compare

    print_compare(a, b)


async def run_file_evaluation(
    filepath: Path,
    deep: bool = False,
    json_output: bool = False,
) -> None:
    """Evaluate a local file."""
    # TODO: Implement file evaluation
    console.print(f"[yellow]File evaluation not yet implemented: {filepath}[/yellow]")


async def run_topic_evaluation(
    skill: str,
    deep: bool = False,
    json_output: bool = False,
) -> None:
    """Evaluate market demand for a skill/topic via web search."""
    from skillens.market.trends import analyze_topic

    with console.status(f"[bold blue]Analyzing market for '{skill}'...[/bold blue]"):
        result = await analyze_topic(skill)

    if json_output:
        import json as _json

        print(_json.dumps(result, indent=2, ensure_ascii=False))
        return

    from rich.panel import Panel

    lines = [
        f"[bold]{skill}[/bold]",
        "",
        f"  Job postings found:  [cyan]{result['job_hits']}[/cyan]",
        f"  Tutorial results:    [cyan]{result['tutorial_hits']}[/cyan]",
        f"  Half-life estimate:  [cyan]{result['half_life']}[/cyan]",
        f"  Demand score:        [bold]{result['demand_score']}/100[/bold]",
        "",
        "[bold]Top learning resources:[/bold]",
    ]
    for url in result["top_resources"][:5]:
        lines.append(f"  · {url}")
    console.print(Panel("\n".join(lines), title="[bold blue]📊 Topic Analysis[/bold blue]", border_style="blue"))


def _summarize_why_better(alt: "Assessment", original: "Assessment") -> str:
    """Generate a one-line reason why an alternative is better."""
    reasons = []
    if alt.freshness - original.freshness > 15:
        reasons.append("more up-to-date")
    if alt.info_density - original.info_density > 15:
        reasons.append("higher info density")
    if alt.effort_vs_return - original.effort_vs_return > 15:
        reasons.append("better ROI")
    if alt.market_demand - original.market_demand > 15:
        reasons.append("more in-demand skill focus")
    if alt.resource.duration_hours and original.resource.duration_hours:
        if alt.resource.duration_hours < original.resource.duration_hours * 0.5:
            reasons.append("much shorter")
    if not reasons:
        reasons.append("higher overall quality")
    return ", ".join(reasons[:2]).capitalize()
