"""End-to-end harness smoke test: load mock.yaml and verify the run summary shape."""

from pathlib import Path

from harness.config import load_config
from harness.runner import Runner

ROOT = Path(__file__).resolve().parents[1]


def test_mock_config_runs_end_to_end(tmp_path: Path) -> None:
    config = load_config(ROOT / "configs" / "mock.yaml")
    # Redirect results into the test's tmp dir.
    config = type(config)(
        name=config.name,
        backend=config.backend,
        tasks=config.tasks,
        output_dir=tmp_path,
        seed=config.seed,
    )
    runner = Runner(config)
    summary = runner.run()

    assert summary["total"] == 4
    names = {r["name"] for r in summary["results"]}
    assert names == {"vision-to-code", "refactor", "long-context", "reliability"}

    for r in summary["results"]:
        assert "score" in r
        assert "duration_s" in r
        # The mock backend is fast — sanity check on wall time.
        assert r["duration_s"] < 5.0


def test_mock_long_context_recalls_needle() -> None:
    config = load_config(ROOT / "configs" / "mock.yaml")
    runner = Runner(config)
    summary = runner.run()
    long_ctx = next(r for r in summary["results"] if r["name"] == "long-context")
    # The mock response is exactly the needle value, so recall should be perfect.
    assert long_ctx["score"] == 1.0
    assert long_ctx["passed"] is True
