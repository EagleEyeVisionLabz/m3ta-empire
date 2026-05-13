# AI-Assistant Working Conventions

This file documents conventions for AI assistants contributing to `m3ta-empire`. The rules apply to any assistant or tool generating commits, PRs, code, or docs in this repo.

## Hard rules

1. **No assistant or model identifiers in committed artifacts.** Commit messages, PR titles, PR bodies, code comments, and docs must never reference the name, vendor, or version of the AI tool that produced them. Author the work under the human's identity; no "Co-Authored-By: <assistant>" trailers; no marketing strings like "Generated with X".
2. **Prefer editing existing files over creating new ones.** Don't introduce a new file when an existing one will do.
3. **Never commit secrets.** No tokens, API keys, model credentials, or `.env` content. `.gitignore` covers the obvious paths; if unsure, ask the maintainer.
4. **Stage files explicitly.** No `git add -A` or `git add .` — name each file. This prevents accidentally committing generated artifacts.

## Commits

- Conventional Commits: `chore(scope): subject`, `feat(scope): subject`, `docs(scope): subject`, `ci: subject`, `fix(scope): subject`.
- Subject < 72 chars, imperative mood.
- Body explains the **why**, not the what. Wrap at ~80 chars.

## Branches & PRs

- Branch names: `feat/<thing>`, `chore/<thing>`, `docs/<thing>`, `fix/<thing>`.
- PR titles: short (< 70 chars), no scope prefix needed.
- PR body: a `## Summary` section in prose, followed by a `## Follow-ups for the maintainer` bulleted checklist.
- Squash-merge into `main` for linear history. Delete the feature branch after merge.

## Code style

- Python: 4-space indent, type hints on public APIs, ruff-friendly formatting.
- Shell scripts: `#!/usr/bin/env bash`, `set -euo pipefail`, shellcheck-clean.
- YAML configs: 2-space indent, no tabs.
- Tests: live under `tests/` next to the package they exercise.

## When in doubt

Open an issue or ask the maintainer before making the change. Don't substitute a different resource (different repo, branch, model, API) just because the requested one isn't reachable — surface the blocker.
