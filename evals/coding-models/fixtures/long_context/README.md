# long-context fixtures

The shipped `corpus.md` is intentionally small — large enough to exercise the harness mechanics, far too small to actually stress a 200K-token context window. Before running with a real backend, swap in a real haystack (open-source book, large transcript dump, etc.).

Needles are described in `needles.json`:

```json
{
  "needles": [
    { "id": "alpha", "position": 0.1, "value": "the-secret-word-is-OPAL" },
    { "id": "delta", "position": 0.9, "value": "checkpoint-7421" }
  ]
}
```

`position` is a fraction in [0, 1] indicating where in the corpus the needle is inserted. The harness inserts `NEEDLE-<id>: <value>` lines at those positions before sending the prompt.
