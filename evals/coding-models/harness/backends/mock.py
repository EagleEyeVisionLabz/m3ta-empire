"""Deterministic in-process backend. Used in CI and for harness unit tests."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from harness.backends.base import BackendResponse, CodingBackend


class MockBackend(CodingBackend):
    """Echoes back canned responses keyed by prompt-hash prefix.

    Looks up `responses` (dict) by the first matching prefix of the prompt;
    falls back to `default_response` otherwise. Deterministic by design.
    """

    name = "mock"

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        default_response: str = "MOCK_OK",
        latency_ms: int = 5,
        fail_on: list[str] | None = None,
    ) -> None:
        self.responses = responses or {}
        self.default_response = default_response
        self.latency_ms = max(0, int(latency_ms))
        self.fail_on = fail_on or []

    def generate(
        self,
        prompt: str,
        *,
        image: bytes | str | None = None,
        max_tokens: int | None = None,
        reasoning: str | None = None,
        timeout_s: float = 60.0,
    ) -> BackendResponse:
        if self.latency_ms:
            time.sleep(self.latency_ms / 1000.0)

        for trigger in self.fail_on:
            if trigger in prompt:
                return BackendResponse(
                    text="",
                    finish_reason="error",
                    latency_ms=self.latency_ms,
                    raw={"reason": f"mock fail triggered by '{trigger}'"},
                )

        # Pick the first matching prefix; otherwise fall back.
        text = self.default_response
        for prefix, response in self.responses.items():
            if prompt.startswith(prefix):
                text = response
                break

        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        return BackendResponse(
            text=text,
            finish_reason="stop",
            latency_ms=self.latency_ms,
            raw={"prompt_sha256_prefix": digest, "had_image": image is not None},
        )

    def __repr__(self) -> str:
        return f"MockBackend(default={self.default_response!r}, n_keyed={len(self.responses)})"
