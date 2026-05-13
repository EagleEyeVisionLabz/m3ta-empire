# coding-models eval harness

A **model-agnostic** eval harness for scoring coding-model candidates that might be wired into M3ta-0s as routed backends.

The harness was bootstrapped after Code Supernova was deprecated (Oct 27, 2025) on every stealth-window provider. Rather than tie the work to a single model, this harness lets any backend (local Ollama, OpenRouter HTTP, OpenCode subprocess, etc.) be scored against the same four tasks so a winning candidate can be picked on evidence.

## What it scores

| Task | What it measures | Scoring |
| --- | --- | --- |
| `vision-to-code` | Mockup-image → working HTML/React | pixel-diff vs. reference render + manual UI fidelity (0–5) |
| `refactor` | Multi-file change on a small TS project | tests pass, cyclomatic complexity delta, import-graph diff |
| `long-context` | Needle-in-haystack recall at ~50K / 100K / 180K tokens | exact-match accuracy per position |
| `reliability` | Long-generation stability | success rate over N runs + error taxonomy (hang, infinite-loading, hallucinated API) |

## How it's structured

```
evals/coding-models/
├── harness/
│   ├── runner.py          # CLI entrypoint, YAML config loader
│   ├── config.py          # config dataclasses + loader
│   ├── backends/          # CodingBackend implementations
│   │   ├── base.py        # ABC: generate(prompt, image?, max_tokens, ...)
│   │   ├── mock.py        # deterministic, used in CI
│   │   ├── ollama.py      # local Ollama HTTP (default :11434)
│   │   └── openrouter.py  # OpenRouter HTTP, OPENROUTER_API_KEY from env
│   ├── tasks/             # Task implementations
│   │   ├── base.py        # ABC: build_prompt(), score(response)
│   │   ├── vision_to_code.py
│   │   ├── refactor.py
│   │   ├── long_context.py
│   │   └── reliability.py
│   └── scoring/           # reusable scorers
│       ├── pixel_diff.py
│       ├── pytest_runner.py
│       └── needle_haystack.py
├── fixtures/              # task inputs (mockups, TS projects, corpora)
├── configs/               # YAML run configs (backend + tasks + thresholds)
├── scripts/run-eval.sh    # convenience wrapper
└── tests/                 # harness unit tests (run against mock backend)
```

## Quick start

```bash
# Install
cd evals/coding-models
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Smoke test (mock backend, no model required, runs in <1s)
python -m harness.runner --config configs/mock.yaml

# Local Ollama (requires Ollama running with the model pulled)
python -m harness.runner --config configs/ollama-local.yaml

# OpenRouter (requires OPENROUTER_API_KEY env)
export OPENROUTER_API_KEY=sk-or-...
python -m harness.runner --config configs/openrouter.yaml
```

Results land in `results/<timestamp>.json` (gitignored).

## Adding a new backend

1. Create `harness/backends/yourbackend.py` subclassing `CodingBackend`.
2. Implement `generate(prompt, image=None, max_tokens=None, reasoning=None) -> BackendResponse`.
3. Register it in `harness/backends/__init__.py` → `BACKENDS` dict.
4. Add a YAML config under `configs/` and wire any required env-var credential names.

## Adding a new task

1. Create `harness/tasks/yourtask.py` subclassing `Task`.
2. Implement `build_prompt(fixture)` and `score(response, fixture) -> TaskResult`.
3. Drop fixtures under `fixtures/yourtask/`.
4. Reference it by name in a YAML config under the `tasks:` list.

## Intentionally out of scope (for now)

- Wiring a backend into `m3ta-mcp` as a tool — that's a follow-up PR after this harness picks a winner.
- Updating the Hermes kernel routing chain — same: follow-up after evidence.
- Production fixtures. The shipped fixtures are tiny smoke-tests; expand once a real backend is selected.
