"""Backend abstract base class. All adapters implement this surface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class BackendResponse:
    """Normalized return type from any backend."""

    text: str
    finish_reason: str = "stop"  # "stop" | "length" | "timeout" | "error"
    latency_ms: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class CodingBackend(ABC):
    """Adapter contract for any coding-capable model exposed via any transport."""

    name: str = "backend"

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        image: bytes | str | None = None,
        max_tokens: int | None = None,
        reasoning: str | None = None,  # "low" | "medium" | "high" | None
        timeout_s: float = 60.0,
    ) -> BackendResponse:
        """Run one generation call. Implementations MUST honor timeout_s."""

    def close(self) -> None:
        """Release any persistent resources (HTTP sessions, subprocesses, etc.)."""
        return None
