"""MCP (Model Context Protocol) server mode.

Exposes SkiLens as MCP tools so agents (Claude Desktop, Cursor, etc.)
can evaluate learning resources programmatically.

Requires the `mcp` package (optional extra: `pip install skillens[mcp]`).
Launch with::

    skillens mcp

By default runs over stdio, which is the right transport for Claude
Desktop / Cursor integrations.
"""

from __future__ import annotations


def build_server():
    """Build and return the FastMCP server instance.

    Separated from `run()` so tests can import and poke at it without
    actually launching a transport loop.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as e:
        raise RuntimeError(
            "mcp package not installed. Run: pip install skillens[mcp]"
        ) from e

    from skillens.core.scorer import score_resource
    from skillens.providers.registry import detect_provider

    mcp = FastMCP("skillens")

    @mcp.tool()
    async def evaluate_url(url: str) -> dict:
        """Evaluate a learning resource by URL.

        Returns a JSON assessment with scores, verdict, strengths,
        concerns, and alternatives. Fast (quick mode, no LLM).
        """
        provider = detect_provider(url)
        meta = await provider.extract(url)
        assessment = score_resource(meta, deep=False)
        return assessment.model_dump(mode="json")

    @mcp.tool()
    async def analyze_topic(skill: str) -> dict:
        """Analyze market demand for a skill or topic.

        Returns demand score, half-life estimate, and top learning
        resources found via web search.
        """
        from skillens.market.trends import analyze_topic as _analyze

        return await _analyze(skill)

    @mcp.tool()
    def get_profile() -> dict:
        """Return the current user profile (for personalized scoring)."""
        from skillens.profile.manager import load_profile

        profile = load_profile()
        return profile.model_dump(mode="json") if profile else {}

    return mcp


def run(transport: str = "stdio") -> None:
    """Launch the MCP server."""
    server = build_server()
    server.run(transport=transport)
