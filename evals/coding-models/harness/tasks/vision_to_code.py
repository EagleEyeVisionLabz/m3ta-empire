"""Vision-to-code task: image of a UI mockup → working HTML/React."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from harness.backends.base import CodingBackend
from harness.scoring.pixel_diff import score_html_against_reference
from harness.tasks.base import Task, TaskResult


class VisionToCodeTask(Task):
    """Feed a mockup image plus a short brief; expect runnable HTML back.

    Fixture shape: a directory of `<case>.json` files, each describing:
      {
        "name": "single-button-page",
        "brief": "Render this single-button landing page as HTML+CSS.",
        "image": "single-button-page.png",
        "reference_html": "single-button-page.expected.html",
        "min_score": 0.6,
        "viewport": [800, 600]
      }

    Scoring: render the model HTML and the reference HTML in a headless
    canvas (or fall back to a structural diff if headless rendering isn't
    available locally); return [0..1] pixel-similarity (or structural).
    """

    name = "vision-to-code"

    def __init__(
        self,
        fixtures: Path,
        cases: list[str] | None = None,
        reasoning: str = "medium",
        max_tokens: int = 4096,
        timeout_s: float = 90.0,
    ) -> None:
        super().__init__(fixtures)
        self.cases = cases
        self.reasoning = reasoning
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s

    def _iter_cases(self) -> list[Path]:
        if self.cases:
            return [self.fixtures / f"{name}.json" for name in self.cases]
        return sorted(self.fixtures.glob("*.json"))

    def run(self, backend: CodingBackend) -> TaskResult:
        case_files = self._iter_cases()
        if not case_files:
            return TaskResult(
                name=self.name,
                passed=False,
                score=0.0,
                metrics={"cases": 0},
                details=f"No case files found under {self.fixtures}",
            )

        per_case: list[dict[str, Any]] = []
        total = 0.0

        for case_file in case_files:
            spec = json.loads(case_file.read_text())
            image_path = case_file.parent / spec["image"]
            ref_path = case_file.parent / spec["reference_html"]
            min_score = float(spec.get("min_score", 0.6))

            response = backend.generate(
                prompt=spec["brief"],
                image=str(image_path),
                max_tokens=self.max_tokens,
                reasoning=self.reasoning,
                timeout_s=self.timeout_s,
            )

            generated_html = _extract_html_block(response.text)
            ref_html = ref_path.read_text() if ref_path.exists() else ""
            similarity = score_html_against_reference(generated_html, ref_html)

            per_case.append(
                {
                    "case": spec["name"],
                    "similarity": similarity,
                    "min_score": min_score,
                    "passed": similarity >= min_score,
                    "finish_reason": response.finish_reason,
                    "latency_ms": response.latency_ms,
                }
            )
            total += similarity

        n = len(per_case)
        mean = total / n if n else 0.0
        passed = all(c["passed"] for c in per_case)

        return TaskResult(
            name=self.name,
            passed=passed,
            score=mean,
            metrics={"cases": n, "mean_similarity": mean, "per_case": per_case},
            details=f"{sum(c['passed'] for c in per_case)}/{n} cases met min_score",
        )


def _extract_html_block(text: str) -> str:
    """Strip markdown fences and pull out the first <html>...</html> block if present."""
    text = text.strip()
    if "```" in text:
        # Take the contents of the first fenced block.
        parts = text.split("```")
        if len(parts) >= 3:
            inner = parts[1]
            # Drop the optional language tag on the first line.
            first_newline = inner.find("\n")
            if first_newline != -1 and not inner[:first_newline].lstrip().startswith("<"):
                inner = inner[first_newline + 1 :]
            text = inner
    # Optionally narrow to <html>...</html> if the wrapper is included.
    lower = text.lower()
    start = lower.find("<html")
    end = lower.rfind("</html>")
    if start != -1 and end != -1 and end > start:
        return text[start : end + len("</html>")]
    return text
