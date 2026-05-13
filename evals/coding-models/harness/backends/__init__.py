"""Backend registry. Add new backends by importing and registering here."""

from __future__ import annotations

from typing import Any

from harness.backends.base import CodingBackend
from harness.backends.mock import MockBackend
from harness.backends.ollama import OllamaBackend
from harness.backends.openrouter import OpenRouterBackend

BACKENDS: dict[str, type[CodingBackend]] = {
    "mock": MockBackend,
    "ollama": OllamaBackend,
    "openrouter": OpenRouterBackend,
}


def resolve_backend(kind: str, params: dict[str, Any]) -> CodingBackend:
    if kind not in BACKENDS:
        raise KeyError(f"Unknown backend '{kind}'. Available: {sorted(BACKENDS)}")
    return BACKENDS[kind](**params)


__all__ = ["BACKENDS", "CodingBackend", "resolve_backend"]
