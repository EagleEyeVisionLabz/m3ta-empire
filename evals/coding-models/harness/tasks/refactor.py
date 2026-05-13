"""Multi-file refactor task: apply a described change to a small TS project, run its tests."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from harness.backends.base import CodingBackend
from harness.scoring.pytest_runner import run_node_tests
from harness.tasks.base import Task, TaskResult


class RefactorTask(Task):
    """Hand the backend a project tarball + a refactor brief, expect updated files back.

    Fixture shape:
      fixtures/refactor/
        sample/                  # tree of files the model receives
          package.json
          src/index.ts
          tests/index.test.ts
        brief.md                 # what to change
        expected.json            # { "min_passing_tests": 1 }

    The backend response is expected to contain a JSON document with the
    same shape as `expected_files.json`, mapping relative paths → new file
    contents. We apply those, then run `npm test` and score by test pass-rate.
    """

    name = "refactor"

    def __init__(
        self,
        fixtures: Path,
        project_subdir: str = "sample",
        brief_filename: str = "brief.md",
        expected_filename: str = "expected.json",
        reasoning: str = "medium",
        max_tokens: int = 8192,
        timeout_s: float = 120.0,
        run_tests: bool = False,  # disabled by default in CI (no node toolchain)
    ) -> None:
        super().__init__(fixtures)
        self.project_subdir = project_subdir
        self.brief_filename = brief_filename
        self.expected_filename = expected_filename
        self.reasoning = reasoning
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.run_tests = run_tests

    def _gather_project_text(self, project_root: Path) -> str:
        lines: list[str] = []
        for path in sorted(project_root.rglob("*")):
            if path.is_dir() or "node_modules" in path.parts:
                continue
            rel = path.relative_to(project_root)
            try:
                content = path.read_text()
            except UnicodeDecodeError:
                continue
            lines.append(f"=== FILE: {rel.as_posix()} ===")
            lines.append(content)
            lines.append("")
        return "\n".join(lines)

    def run(self, backend: CodingBackend) -> TaskResult:
        project_root = self.fixtures / self.project_subdir
        brief = (self.fixtures / self.brief_filename).read_text()
        expected = json.loads((self.fixtures / self.expected_filename).read_text())

        project_text = self._gather_project_text(project_root)
        prompt = (
            "You are refactoring a small TypeScript project.\n\n"
            f"BRIEF:\n{brief}\n\n"
            "Return ONLY a JSON object mapping relative paths to new file contents.\n"
            "Do not wrap the JSON in markdown. Schema: {\"files\": {\"<relpath>\": \"<contents>\"}}\n\n"
            f"PROJECT FILES:\n{project_text}\n"
        )

        response = backend.generate(
            prompt=prompt,
            max_tokens=self.max_tokens,
            reasoning=self.reasoning,
            timeout_s=self.timeout_s,
        )

        try:
            payload = _parse_json_block(response.text)
            new_files: dict[str, str] = payload["files"]
        except (KeyError, ValueError) as exc:
            return TaskResult(
                name=self.name,
                passed=False,
                score=0.0,
                metrics={
                    "finish_reason": response.finish_reason,
                    "latency_ms": response.latency_ms,
                },
                details=f"Could not parse refactor response: {exc}",
            )

        # Apply changes to a temp copy and (optionally) run tests.
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp) / "work"
            shutil.copytree(project_root, workdir)
            for rel, content in new_files.items():
                target = workdir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)

            if not self.run_tests:
                return TaskResult(
                    name=self.name,
                    passed=True,  # syntactic-only pass (parsed valid response)
                    score=0.5,
                    metrics={
                        "files_updated": len(new_files),
                        "tests_run": False,
                        "finish_reason": response.finish_reason,
                        "latency_ms": response.latency_ms,
                    },
                    details="Tests not run (set run_tests=true to enable).",
                )

            test_result = run_node_tests(workdir)

        passing = test_result.get("passing", 0)
        min_pass = int(expected.get("min_passing_tests", 1))
        total = max(1, test_result.get("total", 1))
        score = passing / total

        return TaskResult(
            name=self.name,
            passed=passing >= min_pass and test_result.get("exit_code") == 0,
            score=score,
            metrics={
                "files_updated": len(new_files),
                "test_result": test_result,
                "finish_reason": response.finish_reason,
                "latency_ms": response.latency_ms,
            },
            details=f"{passing}/{total} tests passed",
        )


def _parse_json_block(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a possibly-fenced response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1 :]
        if text.endswith("```"):
            text = text[:-3]
    return json.loads(text)
