"""OpenAI LLM backend — uses structured outputs for schema-adherent JSON."""

from __future__ import annotations

import os

from skillens.llm.base import LLMAnalysis, LLMBackend


class OpenAIBackend(LLMBackend):
    def __init__(self, model: str = "gpt-4o-mini", api_key: str | None = None):
        self.model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")

    @property
    def name(self) -> str:
        return f"openai:{self.model}"

    async def analyze(self, prompt: str) -> LLMAnalysis:
        if not self._api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Run: skillens config set api-key <key>"
            )
        try:
            from openai import AsyncOpenAI
        except ImportError as e:
            raise RuntimeError(
                "openai package not installed. Run: pip install skillens[llm]"
            ) from e

        client = AsyncOpenAI(api_key=self._api_key)
        completion = await client.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a learning advisor. Score learning resources "
                        "strictly and concisely. Return scores 0-100."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format=LLMAnalysis,
        )
        parsed = completion.choices[0].message.parsed
        if parsed is None:
            raise RuntimeError("OpenAI returned no parsed output")
        return parsed
