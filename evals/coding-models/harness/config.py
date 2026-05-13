"""Config loading. YAML in → dataclasses out. No backend or task imports here."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class BackendConfig:
    """One backend instance, identified by `kind` and configured via `params`."""

    kind: str  # registry key, e.g. "mock", "ollama", "openrouter"
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskConfig:
    """One task instance, with fixture path and optional task-specific params."""

    kind: str  # registry key, e.g. "vision-to-code", "refactor"
    fixtures: Path
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunConfig:
    """Top-level run config: one backend × N tasks."""

    name: str
    backend: BackendConfig
    tasks: list[TaskConfig]
    output_dir: Path
    seed: int = 0


def _expand_env(value: Any) -> Any:
    """Recursively expand ${VAR} env-var references in strings."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_config(path: Path) -> RunConfig:
    """Load a YAML run config from disk."""
    raw = yaml.safe_load(path.read_text())
    raw = _expand_env(raw)

    base = path.parent

    backend = BackendConfig(
        kind=raw["backend"]["kind"],
        params=raw["backend"].get("params", {}) or {},
    )

    tasks: list[TaskConfig] = []
    for entry in raw["tasks"]:
        fixtures = (base / entry["fixtures"]).resolve()
        tasks.append(
            TaskConfig(
                kind=entry["kind"],
                fixtures=fixtures,
                params=entry.get("params", {}) or {},
            )
        )

    output_dir = (base / raw.get("output_dir", "../results")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    return RunConfig(
        name=raw.get("name", path.stem),
        backend=backend,
        tasks=tasks,
        output_dir=output_dir,
        seed=int(raw.get("seed", 0)),
    )
