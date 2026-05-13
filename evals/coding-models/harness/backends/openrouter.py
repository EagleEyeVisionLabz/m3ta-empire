"""OpenRouter HTTP backend. Reaches any model OpenRouter exposes."""

from __future__ import annotations

import base64
import os
import time
from typing import Any

import requests

from harness.backends.base import BackendResponse, CodingBackend


class OpenRouterBackend(CodingBackend):
    """OpenAI-compatible chat-completions client pointed at OpenRouter."""

    name = "openrouter"

    def __init__(
        self,
        model: str,
        base_url: str = "https://openrouter.ai/api/v1",
        api_key_env: str = "OPENROUTER_API_KEY",
        temperature: float = 0.2,
        system_prompt: str | None = None,
        http_referer: str | None = None,
        x_title: str | None = None,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.temperature = float(temperature)
        self.system_prompt = system_prompt
        self.http_referer = http_referer
        self.x_title = x_title
        self._session = requests.Session()

    def _api_key(self) -> str:
        key = os.environ.get(self.api_key_env)
        if not key:
            raise RuntimeError(
                f"Missing OpenRouter API key in env var '{self.api_key_env}'"
            )
        return key

    def generate(
        self,
        prompt: str,
        *,
        image: bytes | str | None = None,
        max_tokens: int | None = None,
        reasoning: str | None = None,
        timeout_s: float = 60.0,
    ) -> BackendResponse:
        messages: list[dict[str, Any]] = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        if image is None:
            messages.append({"role": "user", "content": prompt})
        else:
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": _image_to_data_url(image)}},
                    ],
                }
            )

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if max_tokens:
            payload["max_tokens"] = int(max_tokens)
        if reasoning:
            payload["reasoning"] = {"effort": reasoning}

        headers = {
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
        }
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.x_title:
            headers["X-Title"] = self.x_title

        t0 = time.time()
        try:
            resp = self._session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout_s,
            )
            resp.raise_for_status()
        except requests.Timeout:
            return BackendResponse(
                text="",
                finish_reason="timeout",
                latency_ms=int((time.time() - t0) * 1000),
                raw={"error": "openrouter request timed out"},
            )
        except requests.RequestException as exc:
            return BackendResponse(
                text="",
                finish_reason="error",
                latency_ms=int((time.time() - t0) * 1000),
                raw={"error": str(exc), "body": getattr(exc.response, "text", None)},
            )

        data = resp.json()
        choice = (data.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content", "") or ""
        finish = choice.get("finish_reason") or "stop"
        return BackendResponse(
            text=text,
            finish_reason=finish,
            latency_ms=int((time.time() - t0) * 1000),
            raw=data,
        )

    def close(self) -> None:
        self._session.close()


def _image_to_data_url(image: bytes | str) -> str:
    if isinstance(image, str) and image.startswith(("http://", "https://", "data:")):
        return image
    if isinstance(image, bytes):
        b64 = base64.b64encode(image).decode("ascii")
        return f"data:image/png;base64,{b64}"
    with open(image, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"
