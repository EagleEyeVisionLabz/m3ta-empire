# Brain Persona Schema (canonical)

A persona is a routed, named-and-shaped agent the qu3bii-dashboard surfaces in
the 🧠 Brain Personas view. Personas can live in three storage backends; the
`persona-registry` (`core/m3ta-os/src/persona-registry.ts`) merges them at
boot into a single read-only map keyed by persona id.

## Storage backends

| Backend  | Path glob                                          | Format       | Use when                                                |
|----------|----------------------------------------------------|--------------|---------------------------------------------------------|
| `local`  | `apps/qu3bii-dashboard/src/personas/*.json`        | JSON         | Fast UX iteration, no kernel reload                     |
| `kernel` | `core/m3ta-os/personas/*.yaml`                     | YAML         | Production personas the kernel hot-reloads              |
| `lyzr`   | `integrations/lyzr/personas/*.json`                | JSON pointer | Persona body lives in Lyzr Studio; only the id is here  |

The loader resolves env-var refs of the form `${VAR_NAME}` against `process.env`
at load time, so `lyzr.agent_id` can be `${LYZR_AGENT_COACH_ID}` and the actual
id stays in `core/m3ta-os/.env`.

## Common fields (all backends)

| Field           | Type                                | Required        | Notes                                                                                                  |
|-----------------|-------------------------------------|-----------------|--------------------------------------------------------------------------------------------------------|
| `id`            | string (kebab-case)                 | yes             | Globally unique across all backends                                                                    |
| `name`          | string                              | yes             | Display name in the dashboard card                                                                     |
| `role`          | string                              | yes             | One-line subtitle, e.g. `"Deep reasoning / planning"`                                                  |
| `backend`       | `"local" \| "kernel" \| "lyzr"`     | yes             | Must match the storage location the file actually lives in                                             |
| `model_route`   | string                              | yes             | LiteLLM proxy route slug (`m3ta-default`, `m3ta-code`, `m3ta-reasoning`, `m3ta-fast`, `m3ta-heavy`, `m3ta-oss`, `m3ta-embed`) — or `"lyzr-managed"` when backend is `"lyzr"` |
| `system_prompt` | string                              | conditional     | Required for `local` + `kernel`; omitted for `lyzr` (body in Studio)                                   |
| `tools`         | string[]                            | no              | Tool slugs the persona may invoke                                                                      |
| `tags`          | string[]                            | no              | Free-form, used for dashboard filtering                                                                |
| `ui`            | `{ icon, color, order }`            | no              | Card rendering: emoji or icon name, hex color, sort order                                              |
| `lyzr`          | `{ agent_id, env_key?, bridge_url?, studio_url? }` | conditional | Required only when `backend === "lyzr"`                                                                |

## Validation contract

The registry rejects any persona where:

1. **Backend mismatch** — file lives in `local` storage but declares `backend: "kernel"`, etc.
2. **Id collision** — two personas (in any backend) share the same `id`.
3. **Lyzr without pointer** — `backend: "lyzr"` but `lyzr.agent_id` missing or empty after env resolution.
4. **Non-Lyzr without prompt** — `backend: "local" | "kernel"` but `system_prompt` missing or empty.

A failed load is fatal: the kernel refuses to start with an invalid persona
rather than silently dropping it from the registry.

## Adding a new persona

1. Pick the backend by ownership:
   - **local** — owned by the dashboard team, ships in the UI bundle.
   - **kernel** — owned by the runtime, hot-reloaded, can call kernel-only tools.
   - **lyzr** — owned in Studio, body editable without a deploy.
2. Drop the file in the matching directory.
3. Add a `LYZR_AGENT_<UPPER>=agt_...` line to `core/m3ta-os/.env` if Lyzr-backed.
4. Restart T1 (kernel) or just save (dashboard hot-reload picks up `local`).
