// core/m3ta-os/src/persona-registry.ts
//
// Persona registry: merges three storage backends into one read-only registry
// the qu3bii-dashboard reads at boot via the kernel HTTP surface.
//
//   local   apps/qu3bii-dashboard/src/personas/*.json
//   kernel  core/m3ta-os/personas/*.yaml
//   lyzr    integrations/lyzr/personas/*.json
//
// Validation rules (fatal on first violation):
//   - declared `backend` field must match the directory the file lives in
//   - `id` must be globally unique across all backends
//   - `backend === "lyzr"` requires non-empty `lyzr.agent_id` after env resolution
//   - `backend !== "lyzr"` requires non-empty `system_prompt`
//
// Env-var refs of the form ${VAR_NAME} inside string fields are resolved
// against process.env at load time. Missing vars resolve to "" and will
// trip the lyzr validation above.

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { parse as parseYaml } from "yaml";

export type PersonaBackend = "local" | "kernel" | "lyzr";

export interface Persona {
  id: string;
  name: string;
  role: string;
  backend: PersonaBackend;
  model_route: string;
  system_prompt?: string;
  tools?: string[];
  tags?: string[];
  ui?: { icon?: string; color?: string; order?: number };
  lyzr?: {
    agent_id: string;
    env_key?: string;
    bridge_url?: string;
    studio_url?: string;
  };
}

// Repo root resolves three levels up from src/persona-registry.ts when this
// file lives at core/m3ta-os/src/. Adjust if the build output moves.
const REPO_ROOT = join(__dirname, "..", "..", "..");

const SOURCES: Array<{ backend: PersonaBackend; dir: string; ext: "json" | "yaml" }> = [
  { backend: "local",  dir: "apps/qu3bii-dashboard/src/personas", ext: "json" },
  { backend: "kernel", dir: "core/m3ta-os/personas",              ext: "yaml" },
  { backend: "lyzr",   dir: "integrations/lyzr/personas",         ext: "json" },
];

function resolveEnvRefs<T>(value: T): T {
  if (typeof value === "string") {
    return value.replace(/\$\{([A-Z0-9_]+)\}/g, (_, k) => process.env[k] ?? "") as unknown as T;
  }
  if (Array.isArray(value)) {
    return value.map(resolveEnvRefs) as unknown as T;
  }
  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value)) {
      out[k] = resolveEnvRefs(v);
    }
    return out as T;
  }
  return value;
}

function validate(p: Persona, source: PersonaBackend, path: string): void {
  if (!p.id) {
    throw new Error(`persona-registry: missing id (${path})`);
  }
  if (p.backend !== source) {
    throw new Error(
      `persona-registry: ${p.id} declares backend="${p.backend}" but lives in ${source} storage (${path})`,
    );
  }
  if (p.backend === "lyzr") {
    if (!p.lyzr?.agent_id) {
      throw new Error(
        `persona-registry: lyzr persona ${p.id} has empty lyzr.agent_id after env resolution (${path}); check ${p.lyzr?.env_key ?? "LYZR_AGENT_*"} in core/m3ta-os/.env`,
      );
    }
  } else {
    if (!p.system_prompt || !p.system_prompt.trim()) {
      throw new Error(`persona-registry: ${p.backend} persona ${p.id} missing system_prompt (${path})`);
    }
  }
}

export function loadPersonas(): Map<string, Persona> {
  const registry = new Map<string, Persona>();

  for (const { backend, dir, ext } of SOURCES) {
    const abs = join(REPO_ROOT, dir);
    let files: string[];
    try {
      files = readdirSync(abs).filter((f) => f.endsWith(`.${ext}`));
    } catch {
      // Backend directory doesn't exist yet — skip silently. New backends are
      // additive; a fresh checkout shouldn't fail because one dir is empty.
      continue;
    }

    for (const file of files) {
      const path = join(abs, file);
      const raw = readFileSync(path, "utf8");
      const parsed = ext === "json" ? JSON.parse(raw) : parseYaml(raw);
      const persona = resolveEnvRefs(parsed) as Persona;

      validate(persona, backend, path);

      const existing = registry.get(persona.id);
      if (existing) {
        throw new Error(
          `persona-registry: id collision: ${persona.id} in ${backend} (${file}) conflicts with ${existing.backend}`,
        );
      }
      registry.set(persona.id, persona);
    }
  }

  return registry;
}

export function listPersonas(): Persona[] {
  return Array.from(loadPersonas().values()).sort(
    (a, b) => (a.ui?.order ?? 999) - (b.ui?.order ?? 999),
  );
}
