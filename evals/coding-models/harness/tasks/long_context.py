"""Long-context needle-in-haystack task."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from harness.backends.base import CodingBackend
from harness.scoring.needle_haystack import score_needle_recall
from harness.tasks.base import Task, TaskResult


class LongContextTask(Task):
    """Plant unique "needle" strings at specific positions in a corpus, ask the model to recall them.

    Fixture shape:
      fixtures/long_context/
        corpus.md           # haystack text (long)
        needles.json        # { "needles": [ {"id": "...", "position": 0.1, "value": "..."}, ... ] }

    `position` is a fraction in [0, 1] indicating where in the corpus the needle is inserted.
    """

    name = "long-context"

    def __init__(
        self,
        fixtures: Path,
        corpus_filename: str = "corpus.md",
        needles_filename: str = "needles.json",
        positions: list[float] | None = None,  # subset filter, e.g. [0.1, 0.5, 0.9]
        reasoning: str = "low",
        max_tokens: int = 1024,
        timeout_s: float = 90.0,
    ) -> None:
        super().__init__(fixtures)
        self.corpus_filename = corpus_filename
        self.needles_filename = needles_filename
        self.positions = positions
        self.reasoning = reasoning
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def run(self, backend: CodingBackend) -> TaskResult:
        corpus = (self.fixtures / self.corpus_filename).read_text()
        needle_spec = json.loads((self.fixtures / self.needles_filename).read_text())
        needles: list[dict[str, Any]] = needle_spec["needles"]

        if self.positions:
            wanted = set(self.positions)
            needles = [n for n in needles if float(n["position"]) in wanted]

        # Insert each needle into a corpus copy at its position.
        haystack = _insert_needles(corpus, needles)

        per_needle: list[dict[str, Any]] = []
        correct = 0

        for needle in needles:
            question = (
                "Below is a long corpus of text. Inside it, exactly one line begins with "
                f"`NEEDLE-{needle['id']}:`. Read carefully and reply with ONLY the value "
                "after the colon, with no quotes, no preamble, and no explanation.\n\n"
                "===== CORPUS START =====\n"
                f"{haystack}\n"
                "===== CORPUS END ====="
            )
            response = backend.generate(
                prompt=question,
                max_tokens=self.max_tokens,
                reasoning=self.reasoning,
                timeout_s=self.timeout_s,
            )

            expected = str(needle["value"]).strip()
            recall_score = score_needle_recall(response.text, expected)
            passed = recall_score >= 0.99

            per_needle.append(
                {
                    "id": needle["id"],
                    "position": needle["position"],
                    "expected": expected,
                    "recall_score": recall_score,
                    "passed": passed,
                    "finish_reason": response.finish_reason,
                    "latency_ms": response.latency_ms,
                }
            )
            if passed:
                correct += 1

        n = len(per_needle)
        score = correct / n if n else 0.0

        return TaskResult(
            name=self.name,
            passed=score >= 0.66,
            score=score,
            metrics={"needles": n, "correct": correct, "per_needle": per_needle},
            details=f"{correct}/{n} needles recalled",
        )


def _insert_needles(corpus: str, needles: list[dict[str, Any]]) -> str:
    """Insert NEEDLE-<id>: <value> lines at fractional positions in the corpus."""
    if not needles:
        return corpus

    rng = random.Random(0)  # deterministic ordering when positions collide
    sorted_needles = sorted(needles, key=lambda n: (float(n["position"]), rng.random()))

    lines = corpus.splitlines()
    n_lines = len(lines)
    output: list[str] = []
    cursor = 0

    for needle in sorted_needles:
        idx = min(n_lines, max(0, int(round(float(needle["position"]) * n_lines))))
        output.extend(lines[cursor:idx])
        output.append(f"NEEDLE-{needle['id']}: {needle['value']}")
        cursor = idx

    output.extend(lines[cursor:])
    return "\n".join(output)
