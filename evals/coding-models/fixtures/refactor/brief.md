## Refactor brief

The `add` function in `src/index.ts` currently only handles numbers. Extend it so it also accepts strings, in which case it should concatenate them (`add("a", "b") === "ab"`). The TypeScript types must be precise — when given two numbers it returns `number`, when given two strings it returns `string`. Update `tests/index.test.ts` only if necessary to keep all existing tests passing.
