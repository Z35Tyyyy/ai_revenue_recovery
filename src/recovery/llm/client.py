"""Thin, optional wrapper over the Anthropic SDK.

The whole engine must run with no API key, so this class is *availability-aware*:
when no credential is configured (or the SDK isn't installed, or a call fails) it
returns ``None`` and callers fall back to deterministic templates. Nothing in the
core pipeline or the test suite depends on a live model.
"""

from __future__ import annotations

from recovery.config import get_settings


class LLMClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None
        self._tried = False

    @property
    def available(self) -> bool:
        return self._settings.llm_enabled

    def _ensure(self):
        if self._client is None and not self._tried:
            self._tried = True
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)
            except Exception:
                self._client = None
        return self._client

    def complete(self, system: str, user: str, max_tokens: int = 400) -> str | None:
        """Return the model's text, or ``None`` if unavailable / on any error."""
        if not self.available:
            return None
        client = self._ensure()
        if client is None:
            return None
        try:
            resp = client.messages.create(
                model=self._settings.llm_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
            return "".join(parts).strip()
        except Exception:
            return None
