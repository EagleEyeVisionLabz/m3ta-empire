"""Node test runner. Invokes `npm test` in a directory and parses the result."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


_VITEST_SUMMARY = re.compile(r"Tests\s+(\d+)\s+passed.*?\((\d+)\)", re.IGNORECASE | re.DOTALL)
_JEST_SUMMARY = re.compile(r"Tests:\s+(\d+)\s+passed,\s+(\d+)\s+total", re.IGNORECASE)


def run_node_tests(project_root: Path, timeout_s: int = 300) -> dict[str, Any]:
    """Run `npm test` inside project_root. Best-effort parse of common reporters."""
    if not (project_root / "package.json").exists():
        return {"exit_code": -1, "error": "no package.json", "passing": 0, "total": 0}
    if shutil.which("npm") is None:
        return {"exit_code": -1, "error": "npm not on PATH", "passing": 0, "total": 0}

    try:
        install = subprocess.run(
            ["npm", "install", "--silent", "--no-audit", "--no-fund"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        if install.returncode != 0:
            return {
                "exit_code": install.returncode,
                "error": "npm install failed",
                "stderr": install.stderr[-2000:],
                "passing": 0,
                "total": 0,
            }

        test = subprocess.run(
            ["npm", "test", "--silent"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return {"exit_code": -2, "error": f"timeout after {exc.timeout}s", "passing": 0, "total": 0}

    output = (test.stdout or "") + "\n" + (test.stderr or "")
    passing, total = _parse_reporter(output)

    # Allow tests to also publish a structured result file.
    structured = project_root / "test-results.json"
    if structured.exists():
        try:
            data = json.loads(structured.read_text())
            passing = int(data.get("passing", passing))
            total = int(data.get("total", total))
        except (json.JSONDecodeError, ValueError):
            pass

    return {
        "exit_code": test.returncode,
        "passing": passing,
        "total": total,
        "tail": output[-1500:],
    }


def _parse_reporter(output: str) -> tuple[int, int]:
    m = _VITEST_SUMMARY.search(output)
    if m:
        passing = int(m.group(1))
        total = int(m.group(2))
        return passing, total
    m = _JEST_SUMMARY.search(output)
    if m:
        passing = int(m.group(1))
        total = int(m.group(2))
        return passing, total
    # Heuristic fallback: count "✓" marks.
    checks = output.count("✓")
    return checks, max(checks, 0)
