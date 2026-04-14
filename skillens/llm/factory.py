"""LLM backend factory — reads config.toml and returns the right backend."""

from __future__ import annotations

from skillens.core.config import load_config
from skillens.llm.base import LLMBackend


def get_backend() -> LLMBackend:
    """Return the configured backend, defaulting to OpenAI."""
    cfg = load_config()
    kind = (cfg.get("llm") or "openai").lower()
    model = cfg.get("model")
    api_key = cfg.get("api_key")

    if kind == "openai":
        from skillens.llm.openai import OpenAIBackend

        return OpenAIBackend(model=model or "gpt-4o-mini", api_key=api_key)
    if kind == "anthropic":
        from skillens.llm.anthropic import AnthropicBackend

        return AnthropicBackend(model=model or "claude-sonnet-4-6", api_key=api_key)
    if kind == "ollama":
        from skillens.llm.ollama import OllamaBackend

        return OllamaBackend(model=model or "llama3.2")
    from skillens.llm.nollm import NoLLMBackend

    return NoLLMBackend()
