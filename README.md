# m3ta-empire

Public scaffolding for the **M3ta-0s** agent architecture: a Hermes-Agent-kernel-based custom OS-like agent runtime, paired with the `m3ta-mcp` tool server and model-routing infrastructure.

## Repo layout

| Path | Purpose |
| --- | --- |
| `docs/` | M3ta-0s operator runbooks (e.g., `swap-default-model.md`) |
| `evals/coding-models/` | Model-agnostic eval harness for coding-model candidates considered for M3ta-0s routing |

The `m3ta-mcp` server and the Hermes kernel routing config land in their own directories as the project grows.

## Conventions

- Conventional Commits: `chore(scope):`, `feat(scope):`, `docs(scope):`, `ci:`. Subject under 72 chars, body explains the why.
- Branches: `feat/<thing>`, `chore/<thing>`, `docs/<thing>`.
- Pull requests: short titles (<70 chars), `## Summary` and bulleted follow-ups in the body. Squash-merge into `main`. Delete branches after merge.
- See [`CLAUDE.md`](./CLAUDE.md) for AI-assistant working conventions in this repo.

## License

MIT — see [`LICENSE`](./LICENSE).
