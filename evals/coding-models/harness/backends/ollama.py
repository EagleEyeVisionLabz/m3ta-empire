"""Local Ollama backend. Talks to the Ollama HTTP API (default :11434)."""

from __future__ import annotations

import base64
import time
from typing import Any

import requests

from harness.backends.base import BackendResponse, CodingBackend


class OllamaBackend(CodingBackend):
    """Adapter for a local Ollama server. Supports text and vision-capable models."""

    name = "ollama"

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        temperature: float = 0.2,
        num_ctx: int | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = float(temperature)
        self.num_ctx = num_ctx
        self._session = requests.Session()

    def generate(
        self,
        prompt: str,
        *,
        image: bytes | str | None = None,
        max_tokens: int | None = None,
        reasoning: str | None = None,
        timeout_s: float = 60.0,
    ) -> BackendResponse:
        options: dict[str, Any] = {"temperature": self.temperature}
        if max_tokens:
            options["num_predict"] = int(max_tokens)
        if self.num_ctx:
            options["num_ctx"] = int(self.num_ctx)

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }

        if image is not None:
            payload["images"] = [_encode_image(image)]

        t0 = time.time()
        try:
            resp = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=timeout_s,
            )
            resp.raise_for_status()
        except requests.Timeout:
            return BackendResponse(
                text="",
                finish_reason="timeout",
                latency_ms=int((time.time() - t0) * 1000),
                raw={"error": "ollama request timed out"},
            )
        except requests.RequestException as exc:
            return BackendResponse(
                text="",
                finish_reason="error",
                latency_ms=int((time.time() - t0) * 1000),
                raw={"error": str(exc)},
            )

        data = resp.json()
        return BackendResponse(
            text=data.get("response", ""),
            finish_reason="length" if data.get("done_reason") == "length" else "stop",
            latency_ms=int((time.time() - t0) * 1000),
            raw=data,
        )

    def close(self) -> None:
        self._session.close()


def _encode_image(image: bytes | str) -> str:
    """Encode an image to base64 for the Ollama vision API."""
    if isinstance(image, bytes):
        return base64.b64encode(image).decode("ascii")
    # If already a base64 string, return as-is; if a file path, read & encode.
    if image.startswith("data:") or _looks_like_base64(image):
        return image.split(",", 1)[-1] if "," in image else image
    with open(image, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _looks_like_base64(s: str) -> bool:
    if len(s) < 16:
        return False
    return all(c.isalnum() or c in "+/=" for c in s.strip())
