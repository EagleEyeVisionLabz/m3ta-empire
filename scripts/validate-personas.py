#!/usr/bin/env python3
"""scripts/validate-personas.py

CI smoke test for Brain Persona files.

Walks the three persona storage backends (local, kernel, lyzr), parses each
file, runs the same validation rules as `core/m3ta-os/src/persona-registry.ts`,
and exits non-zero on any failure.

This is the CI counterpart to persona-registry.ts. Rules are kept in sync by
inspection — if you change one, change the other. The trade-off is one extra
validator to maintain in exchange for not pulling Bun + a `yaml` dependency
into every CI run.

Usage (locally):
    LYZR_AGENT_COACH_ID=stub python3 scripts/validate-personas.py
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

try:
    import yaml  # type: ignore
except ImportError:
    print("validate-personas: pyyaml not installed; run `pip install pyyaml`", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

SOURCES: list[tuple[str, str, str]] = [
    ("local",  "apps/qu3bii-dashboard/src/personas", "json"),
    ("kernel", "core/m3ta-os/personas",              "yaml"),
    ("lyzr",   "integrations/lyzr/personas",         "json"),
]

ENV_REF = re.compile(r"\$\{([A-Z0-9_]+)\}")


def resolve_env(value):
    """Resolve ${VAR_NAME} refs inside string fields against os.environ."""
    if isinstance(value, str):
        return ENV_REF.sub(lambda m: os.environ.get(m.group(1), ""), value)
    if isinstance(value, list):
        return [resolve_env(x) for x in value]
    if isinstance(value, dict):
        return {k: resolve_env(v) for k, v in value.items()}
    return value


def validate(persona: dict, source: str, path: pathlib.Path) -> None:
    pid = persona.get("id")
    if not pid:
        raise ValueError(f"persona-registry: missing id ({path})")
    if persona.get("backend") != source:
        raise ValueError(
            f'persona-registry: {pid} declares backend="{persona.get("backend")}" '
            f"but lives in {source} storage ({path})"
        )
    if persona["backend"] == "lyzr":
        agent_id = (persona.get("lyzr") or {}).get("agent_id") or ""
        if not agent_id.strip():
            env_key = (persona.get("lyzr") or {}).get("env_key") or "LYZR_AGENT_*"
            raise ValueError(
                f"persona-registry: lyzr persona {pid} has empty lyzr.agent_id "
                f"after env resolution ({path}); check {env_key} in core/m3ta-os/.env"
            )
    else:
        prompt = persona.get("system_prompt") or ""
        if not prompt.strip():
            raise ValueError(
                f"persona-registry: {persona['backend']} persona {pid} missing system_prompt ({path})"
            )


def main() -> int:
    registry: dict[str, dict] = {}

    for backend, rel_dir, ext in SOURCES:
        abs_dir = REPO_ROOT / rel_dir
        if not abs_dir.is_dir():
            # Backend directory doesn't exist yet — skip silently. Matches the
            # behaviour of persona-registry.ts.
            continue

        for f in sorted(abs_dir.glob(f"*.{ext}")):
            raw = f.read_text(encoding="utf-8")
            parsed = json.loads(raw) if ext == "json" else yaml.safe_load(raw)
            persona = resolve_env(parsed)
            validate(persona, backend, f)

            existing = registry.get(persona["id"])
            if existing:
                raise ValueError(
                    f"persona-registry: id collision: {persona['id']} in {backend} "
                    f"({f.name}) conflicts with {existing['backend']}"
                )
            registry[persona["id"]] = persona

    print(f"✓ loaded {len(registry)} personas:")
    for p in sorted(registry.values(), key=lambda x: (x.get("ui") or {}).get("order", 999)):
        icon = (p.get("ui") or {}).get("icon", "·")
        print(f"  {icon} {p['id']} ({p['backend']}, {p['model_route']})")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"✗ persona validation failed:\n  {exc}", file=sys.stderr)
        sys.exit(1)
