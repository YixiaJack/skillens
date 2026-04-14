"""Ollama backend — local LLM via HTTP chat endpoint with JSON-schema format.

No extra dependency needed — we call the REST API directly with httpx.
Requires a running Ollama server (default: http://localhost:11434).
"""

from __future__ import annotations

import json
import os

import httpx

from skillens.llm.base import LLMAnalysis, LLMBackend


class OllamaBackend(LLMBackend):
    def __init__(self, model: str = "llama3.2", host: str | None = None):
        self.model = model
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

    @property
    def name(self) -> str:
        return f"ollama:{self.model}"

    async def analyze(self, prompt: str) -> LLMAnalysis:
        schema = LLMAnalysis.model_json_schema()
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a strict learning advisor. Score 0-100.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                resp = await client.post(f"{self.host}/api/chat", json=payload)
                resp.raise_for_status()
            except httpx.HTTPError as e:
                raise RuntimeError(f"Ollama request failed: {e}") from e

        data = resp.json()
        content = (data.get("message") or {}).get("content") or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Ollama returned non-JSON: {content[:200]}") from e
        return LLMAnalysis.model_validate(parsed)
