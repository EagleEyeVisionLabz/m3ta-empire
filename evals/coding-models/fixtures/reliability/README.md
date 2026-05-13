# reliability fixtures

`tasks.json` lists long-generation prompts that historically destabilized stealth coding models (cf. Goldie's Code Supernova review: app builds with infinite-loading bugs, hallucinated APIs in large multi-file synthesis).

Each entry shape:

```json
{
  "id": "movie-tracker",
  "prompt": "...",
  "max_tokens": 8192
}
```

The harness optionally repeats each task `runs_per_task` times (default 1) and reports per-run failure modes: timeout, error, hallucinated_api, infinite_loading. Pass threshold is `min_success_rate` (default 0.7).
