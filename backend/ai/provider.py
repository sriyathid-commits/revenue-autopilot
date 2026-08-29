"""Optional LLM provider. The application never requires an API key."""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from backend.config import get_settings


class AIProvider:
    def available(self) -> bool:
        return bool(get_settings().openai_api_key)

    def complete_json(self, prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if not self.available():
            return fallback
        settings = get_settings()
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.post(
                    f"{settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.openai_model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Return only valid JSON. You are a fintech risk analyst for synthetic test data.",
                            },
                            {"role": "user", "content": prompt},
                        ],
                        "temperature": 0,
                    },
                )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                return fallback
            merged = dict(fallback)
            merged.update(parsed)
            return merged
        except Exception:
            return fallback


ai_provider = AIProvider()
