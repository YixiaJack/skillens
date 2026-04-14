"""Provider registry — auto-detects the right provider for a URL."""

from __future__ import annotations

from importlib.metadata import entry_points

from skillens.providers.arxiv import ArXivProvider
from skillens.providers.base import BaseProvider, ProviderError
from skillens.providers.coursera import CourseraProvider
from skillens.providers.github_repo import GitHubRepoProvider
from skillens.providers.webpage import WebpageProvider
from skillens.providers.youtube import YouTubeProvider

# Core providers in detection order. Specific ones before the generic
# WebpageProvider fallback. Third-party plugins (via entry points) are
# inserted between the core specific providers and WebpageProvider.
_CORE_SPECIFIC: list[type[BaseProvider]] = [
    CourseraProvider,
    YouTubeProvider,
    GitHubRepoProvider,
    ArXivProvider,
]
_PLUGIN_GROUP = "skillens.providers"


def _load_plugins() -> list[type[BaseProvider]]:
    """Discover third-party providers via entry points.

    Third-party packages can register a provider like so in their
    pyproject.toml::

        [project.entry-points."skillens.providers"]
        udemy = "my_pkg.udemy:UdemyProvider"

    Broken plugins are skipped with a printed warning, not raised —
    a bad plugin must not break the core CLI.
    """
    plugins: list[type[BaseProvider]] = []
    try:
        eps = entry_points(group=_PLUGIN_GROUP)
    except TypeError:  # pragma: no cover — pre-3.10 selectable fallback
        eps = entry_points().get(_PLUGIN_GROUP, [])  # type: ignore[assignment]
    for ep in eps:
        try:
            cls = ep.load()
            if isinstance(cls, type) and issubclass(cls, BaseProvider):
                plugins.append(cls)
        except Exception as e:  # noqa: BLE001
            import sys

            print(f"[skillens] failed to load plugin {ep.name}: {e}", file=sys.stderr)
    return plugins


def _build_order() -> list[type[BaseProvider]]:
    return [*_CORE_SPECIFIC, *_load_plugins(), WebpageProvider]


# Eagerly compute once at import time; tests may rebuild it.
PROVIDER_ORDER: list[type[BaseProvider]] = _build_order()


def reload_providers() -> None:
    """Rebuild PROVIDER_ORDER (used by tests that register plugins)."""
    global PROVIDER_ORDER
    PROVIDER_ORDER = _build_order()


def detect_provider(url: str, force_name: str | None = None) -> BaseProvider:
    """Detect and return the appropriate provider for a URL.

    Args:
        url: The URL to evaluate.
        force_name: If set, use this provider regardless of URL matching.

    Returns:
        An instance of the matching provider.

    Raises:
        ProviderError: If no provider can handle the URL.
    """
    if force_name:
        for provider_cls in PROVIDER_ORDER:
            if provider_cls.__name__.lower().startswith(force_name.lower()):
                return provider_cls()
        raise ProviderError("registry", url, f"No provider named '{force_name}'")

    for provider_cls in PROVIDER_ORDER:
        if provider_cls.can_handle(url):
            return provider_cls()

    raise ProviderError(
        "registry",
        url,
        "No provider found for this URL. Try --provider to force one.",
    )
