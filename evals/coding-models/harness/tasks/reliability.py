"""Reliability task: loop long-gen prompts and tally failure modes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from harness.backends.base import CodingBackend
from harness.tasks.base import Task, TaskResult


# Heuristic markers for known failure modes Goldie's Supernova review surfaced.
HALLUCINATED_API_PATTERNS = [
    re.compile(r"import\s+\{\s*[A-Za-z]+\s*\}\s+from\s+['\"]@imaginary/", re.IGNORECASE),
    re.compile(r"\.thereIsNoSuchMethod\("),
]

INFINITE_LOADING_PATTERNS = [
    re.compile(r"while\s*\(\s*true\s*\)\s*\{[^}]*loading", re.IGNORECASE),
    re.compile(r"setInterval\(\s*\(\)\s*=>\s*setLoading\(true\)", re.IGNORECASE),
]


class ReliabilityTask(Task):
    """Run N long-generation prompts; tally hangs, timeouts, hallucinated APIs, infinite-loaders.

    Fixture shape:
      fixtures/reliability/
        tasks.json   # { "tasks": [ {"id": "...", "prompt": "...", "max_tokens": 4096}, ... ] }

    Pass/fail: configurable `min_success_rate` (default 0.7).
    """

    name = "reliability"

    def __init__(
        self,
        fixtures: Path,
        tasks_filename: str = "tasks.json",
        runs_per_task: int = 1,
        min_success_rate: float = 0.7,
        reasoning: str = "medium",
        max_tokens: int = 4096,
        timeout_s: float = 60.0,
    ) -> None:
        super().__init__(fixtures)
        self.tasks_filename = tasks_filename
        self.runs_per_task = max(1, int(runs_per_task))
        self.min_success_rate = float(min_success_rate)
        self.reasoning = reasoning
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def run(self, backend: CodingBackend) -> TaskResult:
        spec = json.loads((self.fixtures / self.tasks_filename).read_text())
        tasks: list[dict[str, Any]] = spec["tasks"]

        results: list[dict[str, Any]] = []
        successes = 0
        hangs = 0
        hallucinated = 0
        infinite_loaders = 0

        for task in tasks:
            for run_idx in range(self.runs_per_task):
                response = backend.generate(
                    prompt=task["prompt"],
                    max_tokens=int(task.get("max_tokens", self.max_tokens)),
                    reasoning=self.reasoning,
                    timeout_s=self.timeout_s,
                )
                failure_modes: list[str] = []

                if response.finish_reason == "timeout":
                    hangs += 1
                    failure_modes.append("timeout")
                if response.finish_reason == "error":
                    failure_modes.append("error")

                if any(p.search(response.text) for p in HALLUCINATED_API_PATTERNS):
                    hallucinated += 1
                    failure_modes.append("hallucinated_api")
                if any(p.search(response.text) for p in INFINITE_LOADING_PATTERNS):
                    infinite_loaders += 1
                    failure_modes.append("infinite_loading")

                if not failure_modes and response.text.strip():
                    successes += 1

                results.append(
                    {
                        "id": task["id"],
                        "run": run_idx,
                        "finish_reason": response.finish_reason,
                        "latency_ms": response.latency_ms,
                        "chars": len(response.text),
                        "failure_modes": failure_modes,
                    }
                )

        n = len(results)
        rate = successes / n if n else 0.0

        return TaskResult(
            name=self.name,
            passed=rate >= self.min_success_rate,
            score=rate,
            metrics={
                "runs": n,
                "successes": successes,
                "hangs": hangs,
                "hallucinated_api": hallucinated,
                "infinite_loaders": infinite_loaders,
                "per_run": results,
            },
            details=f"{successes}/{n} clean runs (rate={rate:.2f}, threshold={self.min_success_rate})",
        )
