# refactor an existing module

## Intent

Restructure an existing package or module without changing its observable
behavior. The diff should be readable as a refactor; new behavior belongs
in a separate task.

## Inputs

- `target_path` (required) — relative path inside the monorepo.
- `motivation` (required) — one sentence explaining the why.
- `constraints` (optional) — files or APIs that must not change.

## Expected output

- The smallest diff that achieves the motivation.
- No new exports unless explicitly required by the motivation.
- Tests in the matching `tests/` directory pass without modification.
  If tests must change, that is a behavior change disguised as a refactor;
  stop and emit `wrong-route` so the orchestration layer can re-plan.

## Out of scope

- Renaming the package or its public exports.
- Bumping dependency versions.
- Reformatting unrelated files in the same package.

## Acceptance

`bun test <target_path>` matches the pre-refactor result exactly. The diff
is reviewable in a single squash-merge PR.
