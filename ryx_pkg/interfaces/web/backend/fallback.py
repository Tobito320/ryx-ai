"""AI fallback helpers for Ollama → Claude.

Provides a minimal Claude client so API routes can fail over when the local
Ollama endpoint is unavailable. The Claude call is intentionally light-weight
and only depends on httpx.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import httpx


class AIFallbackManager:
    """Manage AI fallbacks between local Ollama and Claude API."""

    def __init__(self, api_key: str | None = None, model: str = "claude-3-5-sonnet-20241022") -> None:
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model

    def claude_available(self) -> bool:
        return bool(self.api_key)

    async def call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 1200,
        expect_json: bool = True,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """Call Claude Messages API and optionally parse JSON response."""

        if not self.claude_available():
            return {"error": "Claude API key not configured"}

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        text_parts = [
            part.get("text", "") for part in data.get("content", []) if part.get("type") == "text"
        ]
        combined_text = "".join(text_parts)

        if not expect_json:
            return {"response": combined_text}

        try:
            return json.loads(combined_text)
        except json.JSONDecodeError:
            return {"raw_response": combined_text, "parse_error": True}


def build_ai_fallback_manager() -> AIFallbackManager:
    return AIFallbackManager()
