"""Anthropic Claude backend — uses tool_use to force JSON-schema output."""

from __future__ import annotations

import os

from skillens.llm.base import LLMAnalysis, LLMBackend


class AnthropicBackend(LLMBackend):
    def __init__(self, model: str = "claude-sonnet-4-6", api_key: str | None = None):
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

    @property
    def name(self) -> str:
        return f"anthropic:{self.model}"

    async def analyze(self, prompt: str) -> LLMAnalysis:
        if not self._api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        try:
            from anthropic import AsyncAnthropic
        except ImportError as e:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install skillens[llm]"
            ) from e

        schema = LLMAnalysis.model_json_schema()
        # Pydantic schemas include $defs etc.; Anthropic accepts them as-is.

        client = AsyncAnthropic(api_key=self._api_key)
        message = await client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=(
                "You are a strict learning advisor. Always respond by calling "
                "the `score_resource` tool exactly once."
            ),
            tools=[
                {
                    "name": "score_resource",
                    "description": "Return structured scoring for a learning resource.",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": "score_resource"},
            messages=[{"role": "user", "content": prompt}],
        )

        for block in message.content:
            if getattr(block, "type", None) == "tool_use":
                return LLMAnalysis.model_validate(block.input)
        raise RuntimeError("Anthropic returned no tool_use block")
