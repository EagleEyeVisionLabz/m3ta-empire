"""CLI entrypoint and orchestrator.

Usage:
    python -m harness.runner --config configs/mock.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from harness.backends import resolve_backend
from harness.config import RunConfig, load_config
from harness.tasks import resolve_task
from harness.tasks.base import TaskResult


class Runner:
    """Top-level orchestrator: one backend × N tasks."""

    def __init__(self, config: RunConfig) -> None:
        self.config = config
        self.backend = resolve_backend(config.backend.kind, config.backend.params)
        self.tasks = [resolve_task(t.kind, t.fixtures, t.params) for t in config.tasks]

    def run(self) -> dict:
        results: list[dict] = []
        run_started = time.time()

        for task in self.tasks:
            t0 = time.time()
            try:
                outcome: TaskResult = task.run(self.backend)
                outcome_dict = asdict(outcome)
                outcome_dict["error"] = None
            except Exception as exc:  # noqa: BLE001 — surface any failure
                outcome_dict = {
                    "name": task.name,
                    "passed": False,
                    "score": 0.0,
                    "metrics": {},
                    "details": str(exc),
                    "error": type(exc).__name__,
                }
            outcome_dict["duration_s"] = round(time.time() - t0, 3)
            results.append(outcome_dict)

        summary = {
            "run_name": self.config.name,
            "backend": self.config.backend.kind,
            "started_at": run_started,
            "finished_at": time.time(),
            "results": results,
            "passed": sum(1 for r in results if r["passed"]),
            "total": len(results),
        }
        return summary

    def write_results(self, summary: dict) -> Path:
        ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime(summary["started_at"]))
        out = self.config.output_dir / f"{ts}-{self.config.name}.json"
        out.write_text(json.dumps(summary, indent=2, sort_keys=True))
        return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the coding-models eval harness.")
    parser.add_argument("--config", required=True, type=Path, help="Path to a run config YAML")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-task console output")
    args = parser.parse_args(argv)

    config = load_config(args.config)
    runner = Runner(config)
    summary = runner.run()
    out_path = runner.write_results(summary)

    if not args.quiet:
        print(f"\n[{summary['run_name']}] backend={summary['backend']}")
        for r in summary["results"]:
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"  {mark} {r['name']:<24} score={r['score']:.2f} duration={r['duration_s']}s")
        print(f"\n{summary['passed']}/{summary['total']} passed → {out_path}")

    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
