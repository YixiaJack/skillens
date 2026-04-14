"""Abstract base class for all resource providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from skillens.core.models import ResourceMeta


class BaseProvider(ABC):
    """Base class for all resource providers.

    Each provider handles one type of learning resource (e.g., Coursera courses,
    YouTube videos, GitHub repos). Providers are responsible for:
    1. Detecting whether they can handle a given URL
    2. Extracting structured metadata from that URL
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for display and logging."""
        ...

    @staticmethod
    @abstractmethod
    def can_handle(url: str) -> bool:
        """Return True if this provider can handle the given URL.

        This is called during auto-detection. Providers are checked in order
        defined in registry.py — first match wins.
        """
        ...

    @abstractmethod
    async def extract(self, url: str) -> ResourceMeta:
        """Extract metadata from the URL.

        Should fetch the page/API and return a ResourceMeta with as many
        fields populated as possible. Missing fields should use defaults.

        Raises:
            httpx.HTTPStatusError: If the URL returns a non-2xx status.
            ProviderError: If extraction fails for provider-specific reasons.
        """
        ...


class ProviderError(Exception):
    """Raised when a provider fails to extract metadata."""

    def __init__(self, provider: str, url: str, reason: str) -> None:
        self.provider = provider
        self.url = url
        self.reason = reason
        super().__init__(f"[{provider}] Failed to extract {url}: {reason}")
