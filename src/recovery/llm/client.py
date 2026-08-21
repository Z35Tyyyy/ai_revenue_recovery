"""Thin, optional, provider-agnostic wrapper for dunning-copy generation.

Supports three providers, chosen by ``LLM_PROVIDER``:

* ``anthropic`` — Claude, via the Anthropic SDK.
* ``groq``      — open models (e.g. Llama 3.3 70B) via Groq's OpenAI-compatible API.
* ``openai``    — OpenAI models via the OpenAI SDK.

The whole engine must run with no key at all, so this class is availability-aware:
when no credential is configured (or the SDK isn't installed, or a call fails) it
returns ``None`` and callers fall back to deterministic templates. Nothing in the
core pipeline, the eval, or the tests depends on a live model.
"""

from __future__ import annotations

from recovery.config import get_settings

_GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class LLMClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = None
        self._kind = None
        self._tried = False

    @property
    def available(self) -> bool:
        return self._settings.llm_enabled

    @property
    def provider(self) -> str:
        return self._settings.llm_provider

    def _ensure(self):
        if self._client is None and not self._tried:
            self._tried = True
            provider = self._settings.llm_provider
            try:
                if provider == "anthropic":
                    import anthropic

                    self._client = anthropic.Anthropic(api_key=self._settings.active_llm_key)
                    self._kind = "anthropic"
                else:  # groq / openai are OpenAI-compatible
                    from openai import OpenAI

                    base_url = _GROQ_BASE_URL if provider == "groq" else None
                    self._client = OpenAI(
                        api_key=self._settings.active_llm_key, base_url=base_url
                    )
                    self._kind = "openai"
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
        model = self._settings.resolved_llm_model
        try:
            if self._kind == "anthropic":
                resp = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
                return "".join(parts).strip()
            # OpenAI-compatible (Groq / OpenAI)
            resp = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return None
