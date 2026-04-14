"""No-LLM backend — returns an empty analysis (used for testing)."""

from __future__ import annotations

from skillens.llm.base import LLMAnalysis, LLMBackend


class NoLLMBackend(LLMBackend):
    @property
    def name(self) -> str:
        return "none"

    async def analyze(self, prompt: str) -> LLMAnalysis:
        raise RuntimeError("No LLM backend configured. Run: skillens config set llm openai")
