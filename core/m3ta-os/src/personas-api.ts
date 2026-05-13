// core/m3ta-os/src/personas-api.ts
//
// Read-only HTTP surface for the persona registry. The qu3bii-dashboard
// fetches `/personas` at boot to populate the 🧠 Brain Personas view.
//
// Routes:
//   GET /personas        -> { personas: Persona[] }  (sorted by ui.order)
//   GET /personas/:id    -> Persona | 404
//
// To run standalone for local testing or CI smoke:
//   bun run core/m3ta-os/src/personas-api.ts
//   curl http://localhost:4101/personas | jq
//
// To mount inside the existing kernel server, import `handlePersonas` and
// delegate any URL matching `/personas` or `/personas/:id` to it. The handler
// is request-shape-pure — no global state, no side effects beyond reading
// the persona files at request time.

import { listPersonas, loadPersonas, type Persona } from "./persona-registry";

const ID_RE = /^[a-z0-9-]+$/;

export function handlePersonas(req: Request): Response {
  const url = new URL(req.url);

  // GET /personas
  if (url.pathname === "/personas" && req.method === "GET") {
    try {
      const personas: Persona[] = listPersonas();
      return Response.json({ personas });
    } catch (e) {
      return Response.json({ error: String(e) }, { status: 500 });
    }
  }

  // GET /personas/:id
  const m = url.pathname.match(/^\/personas\/([^/]+)$/);
  if (m && req.method === "GET") {
    const id = m[1];
    if (!ID_RE.test(id)) {
      return Response.json({ error: "invalid id" }, { status: 400 });
    }
    try {
      const persona = loadPersonas().get(id);
      if (!persona) {
        return Response.json({ error: `not found: ${id}` }, { status: 404 });
      }
      return Response.json(persona);
    } catch (e) {
      return Response.json({ error: String(e) }, { status: 500 });
    }
  }

  return Response.json({ error: "not found" }, { status: 404 });
}

// Standalone server entrypoint. Only fires when this file is executed
// directly via `bun run`, not when imported by the kernel.
if (import.meta.main) {
  const port = Number(process.env.PERSONAS_API_PORT ?? 4101);
  Bun.serve({ port, fetch: handlePersonas });
  console.log(`personas-api listening on http://localhost:${port}`);
}
