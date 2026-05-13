"""Model-agnostic eval harness for coding-model candidates.

Public API:
    Runner        — top-level eval orchestrator
    CodingBackend — ABC for model adapters
    Task          — ABC for eval tasks
"""

from harness.backends.base import BackendResponse, CodingBackend
from harness.runner import Runner
from harness.tasks.base import Task, TaskResult

__all__ = [
    "BackendResponse",
    "CodingBackend",
    "Runner",
    "Task",
    "TaskResult",
]
