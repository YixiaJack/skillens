"""SkiLens CLI — Is this worth learning?"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

app = typer.Typer(
    name="skillens",
    help="🔍 Evaluate whether a learning resource is worth your time.",
    no_args_is_help=True,
    add_completion=False,
)

# Sub-command groups
profile_app = typer.Typer(help="Manage your learning profile.")
config_app = typer.Typer(help="Configure SkiLens settings.")
app.add_typer(profile_app, name="profile")
app.add_typer(config_app, name="config")


@app.command()
def evaluate(
    url: str = typer.Argument(help="URL of the learning resource to evaluate."),
    deep: bool = typer.Option(False, "--deep", help="Use LLM for deep analysis."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip cache."),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color output."),
    compare: Optional[str] = typer.Option(None, "--compare", help="Compare with another URL."),
    provider: Optional[str] = typer.Option(None, "--provider", help="Force a specific provider."),
    lang: str = typer.Option("auto", "--lang", help="Output language (en, zh, auto)."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show debug info."),
) -> None:
    """Evaluate a learning resource by URL."""
    import asyncio

    from skillens.core.evaluator import run_evaluation

    asyncio.run(
        run_evaluation(
            url=url,
            deep=deep,
            json_output=json_output,
            no_cache=no_cache,
            compare_url=compare,
            force_provider=provider,
            lang=lang,
            verbose=verbose,
        )
    )


@app.command()
def analyze(
    filepath: Path = typer.Argument(help="Path to a local file (PDF, MD, TXT)."),
    deep: bool = typer.Option(False, "--deep", help="Use LLM for deep analysis."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Evaluate a local file (PDF, Markdown, or text)."""
    import asyncio

    from skillens.core.evaluator import run_file_evaluation

    asyncio.run(
        run_file_evaluation(
            filepath=filepath,
            deep=deep,
            json_output=json_output,
        )
    )


@app.command()
def mcp(
    transport: str = typer.Option("stdio", "--transport", help="MCP transport: stdio or sse."),
) -> None:
    """Launch SkiLens as an MCP server for agent integration."""
    from skillens.mcp_server import run

    run(transport=transport)


@app.command()
def topic(
    skill: str = typer.Argument(help="Skill or topic to evaluate (e.g., 'reinforcement learning')."),
    deep: bool = typer.Option(False, "--deep", help="Use LLM for deep analysis."),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON."),
) -> None:
    """Evaluate market demand for a skill or topic."""
    import asyncio

    from skillens.core.evaluator import run_topic_evaluation

    asyncio.run(
        run_topic_evaluation(
            skill=skill,
            deep=deep,
            json_output=json_output,
        )
    )


# --- Profile sub-commands ---


@profile_app.command("set")
def profile_set(
    github: Optional[str] = typer.Option(None, "--github", help="GitHub username."),
    skills: Optional[str] = typer.Option(None, "--skills", help="Comma-separated skills."),
    resume: Optional[Path] = typer.Option(None, "--resume", help="Path to resume PDF or text."),
    role: Optional[str] = typer.Option(None, "--role", help="Target role (e.g., 'ML engineer')."),
    years: Optional[int] = typer.Option(None, "--years", help="Years of experience."),
) -> None:
    """Set your learning profile for personalized scoring."""
    from rich import print as rprint

    from skillens.profile.manager import update_profile

    fields: dict = {}
    if github:
        fields["github_username"] = github
    if skills:
        fields["skills"] = [s.strip() for s in skills.split(",") if s.strip()]
    if role:
        fields["target_role"] = role
    if years is not None:
        fields["experience_years"] = years
    if resume:
        if not resume.exists():
            rprint(f"[red]✗[/red] Resume file not found: {resume}")
            raise typer.Exit(1)
        try:
            fields["resume_text"] = resume.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            rprint(f"[red]✗[/red] Could not read resume: {e}")
            raise typer.Exit(1) from e

    if not fields:
        rprint("[yellow]Nothing to update. Pass --github / --skills / --role / --years / --resume.[/yellow]")
        raise typer.Exit(0)

    profile = update_profile(**fields)
    rprint("[green]✓[/green] Profile updated.")
    for k, v in profile.model_dump().items():
        if v:
            rprint(f"  [dim]{k}:[/dim] {v if not isinstance(v, str) or len(v) < 60 else v[:57] + '...'}")


@profile_app.command("show")
def profile_show() -> None:
    """Show your current profile."""
    from rich import print as rprint

    from skillens.profile.manager import load_profile

    profile = load_profile()
    if profile is None:
        rprint("[dim]No profile set. Use 'skillens profile set' to configure.[/dim]")
        return
    rprint("[bold]Current profile:[/bold]")
    for k, v in profile.model_dump().items():
        if v:
            display = v if not isinstance(v, str) or len(v) < 80 else v[:77] + "..."
            rprint(f"  [cyan]{k}:[/cyan] {display}")


@profile_app.command("clear")
def profile_clear() -> None:
    """Clear your profile."""
    from rich import print as rprint

    from skillens.profile.manager import clear_profile

    clear_profile()
    rprint("[green]✓[/green] Profile cleared.")


# --- Config sub-commands ---


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Config key (e.g., 'llm', 'api-key', 'model')."),
    value: str = typer.Argument(help="Config value."),
) -> None:
    """Set a configuration value."""
    from rich import print as rprint

    from skillens.core.config import set_value

    set_value(key, value)
    rprint(f"[green]✓[/green] {key} = {value}")


@config_app.command("show")
def config_show() -> None:
    """Show current configuration."""
    from rich import print as rprint

    from skillens.core.config import load_config

    cfg = load_config()
    if not cfg:
        rprint("[dim]Default configuration (no overrides set).[/dim]")
        return
    for k, v in cfg.items():
        display = v if k != "api_key" else "***" + str(v)[-4:] if v else ""
        rprint(f"  [cyan]{k}:[/cyan] {display}")


_KNOWN_COMMANDS = {"evaluate", "analyze", "topic", "mcp", "profile", "config", "--help", "-h"}


def _force_utf8_streams() -> None:
    """Force stdout/stderr to UTF-8 so Rich emoji doesn't crash on Windows
    consoles with legacy codepages (cp936/GBK on zh-CN, cp1252 on en-US cmd,
    etc.). PowerShell 7+ already defaults to UTF-8, but Git Bash, cmd.exe,
    and older consoles bind Python's streams to the system ANSI codepage
    at interpreter start — which then can't encode '🔍', '⚡', box-drawing
    characters, etc., and crashes with UnicodeEncodeError mid-render.

    `TextIOWrapper.reconfigure` is available on Python 3.7+ and is the
    documented fix. errors='replace' means a truly unencodable byte becomes
    '?' instead of crashing — we never want a pretty-print to kill the CLI.
    """
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main() -> None:
    """Entry point for the CLI.

    If the first argument looks like a URL, inject the 'evaluate' subcommand
    so users can type `skillens "https://..."` directly.
    """
    import sys

    _force_utf8_streams()

    if len(sys.argv) >= 2:
        first = sys.argv[1]
        if first.startswith(("http://", "https://")) and first not in _KNOWN_COMMANDS:
            sys.argv.insert(1, "evaluate")
    app()


if __name__ == "__main__":
    main()
