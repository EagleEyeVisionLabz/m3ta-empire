"""Task abstract base class. All eval tasks implement this surface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harness.backends.base import CodingBackend


@dataclass
class TaskResult:
    """One task's outcome. `passed` is the boolean ship/no-ship signal."""

    name: str
    passed: bool
    score: float  # 0.0 .. 1.0 (or task-specific scale documented in `details`)
    metrics: dict[str, Any] = field(default_factory=dict)
    details: str = ""


class Task(ABC):
    """A single eval task. Owns its fixtures and scoring."""

    name: str = "task"

    def __init__(self, fixtures: Path, **params: Any) -> None:
        self.fixtures = fixtures
        self.params = params

    @abstractmethod
    def run(self, backend: CodingBackend) -> TaskResult:
        """Execute the task against the given backend and return a scored result."""
