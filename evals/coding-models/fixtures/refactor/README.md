# refactor fixtures

Layout:
- `sample/` — small TypeScript project the backend receives in its prompt
- `brief.md` — the refactor instruction
- `expected.json` — pass/fail thresholds

The harness gathers every file under `sample/` into the prompt, asks the backend to return a JSON `{ "files": { "<relpath>": "<new contents>" } }` object, applies those updates to a copy of the project, and (optionally) runs `npm test`.

In CI we run with `run_tests: false` because the runner image doesn't have Node. To enable test execution locally:

```yaml
tasks:
  - kind: refactor
    fixtures: fixtures/refactor
    params:
      run_tests: true
```
