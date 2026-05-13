"""Task registry. Add new tasks by importing and registering here."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.tasks.base import Task
from harness.tasks.long_context import LongContextTask
from harness.tasks.refactor import RefactorTask
from harness.tasks.reliability import ReliabilityTask
from harness.tasks.vision_to_code import VisionToCodeTask

TASKS: dict[str, type[Task]] = {
    "vision-to-code": VisionToCodeTask,
    "refactor": RefactorTask,
    "long-context": LongContextTask,
    "reliability": ReliabilityTask,
}


def resolve_task(kind: str, fixtures: Path, params: dict[str, Any]) -> Task:
    if kind not in TASKS:
        raise KeyError(f"Unknown task '{kind}'. Available: {sorted(TASKS)}")
    return TASKS[kind](fixtures=fixtures, **params)


__all__ = ["TASKS", "Task", "resolve_task"]
