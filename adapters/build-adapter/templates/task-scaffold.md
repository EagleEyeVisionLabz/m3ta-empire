# scaffold a new package under core/

## Intent

Create a new package under `core/<package-name>/` with the standard
Bun/TypeScript layout used elsewhere in the monorepo.

## Inputs

- `package_name` (required) — kebab-case, no leading `m3ta-` prefix.
- `description` (required) — one sentence; ends up in the package README.
- `language` (optional) — `ts` (default) or `py`.

## Expected output

- `core/<package-name>/package.json` with the canonical scripts block.
- `core/<package-name>/src/index.ts` exporting a single named symbol.
- `core/<package-name>/README.md` with the description and a usage stub.
- `core/<package-name>/tests/index.test.ts` with a passing smoke test.

## Out of scope

- Wiring into `core/m3ta-os/` (covered by a separate integrate task).
- Adding to CI workflows (covered by `ci-add-package`).

## Acceptance

`bun test core/<package-name>` is green; the package builds clean from a
fresh install.
