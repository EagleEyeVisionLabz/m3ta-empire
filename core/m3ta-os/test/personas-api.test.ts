// core/m3ta-os/test/personas-api.test.ts
//
// Bun:test smoke test for personas-api. Exercises the HTTP shape end-to-end
// against the live persona-registry loader.
//
// Run with:
//   cd core/m3ta-os && bun test

import { beforeAll, describe, expect, it } from "bun:test";
import { handlePersonas } from "../src/personas-api";

beforeAll(() => {
  // Stub the Lyzr pointer so backend="lyzr" personas pass validation under
  // test. Tests should not depend on a real Lyzr Studio agent id.
  if (!process.env.LYZR_AGENT_COACH_ID) {
    process.env.LYZR_AGENT_COACH_ID = "test-stub-agt-id";
  }
});

describe("personas-api", () => {
  it("GET /personas returns an array of personas", async () => {
    const res = handlePersonas(new Request("http://x/personas"));
    expect(res.status).toBe(200);
    const body = (await res.json()) as { personas: Array<{ id: string; backend: string }> };
    expect(Array.isArray(body.personas)).toBe(true);
    expect(body.personas.length).toBeGreaterThan(0);

    // We expect at least the three demo personas shipped in feat/personas.
    const ids = body.personas.map((p) => p.id);
    expect(ids).toContain("m3ta-scout");
    expect(ids).toContain("m3ta-strategist");
    expect(ids).toContain("m3ta-coach");
  });

  it("personas list is sorted by ui.order", async () => {
    const res = handlePersonas(new Request("http://x/personas"));
    const body = (await res.json()) as {
      personas: Array<{ id: string; ui?: { order?: number } }>;
    };
    const orders = body.personas.map((p) => p.ui?.order ?? 999);
    const sorted = [...orders].sort((a, b) => a - b);
    expect(orders).toEqual(sorted);
  });

  it("GET /personas/m3ta-strategist returns the kernel persona", async () => {
    const res = handlePersonas(new Request("http://x/personas/m3ta-strategist"));
    expect(res.status).toBe(200);
    const body = (await res.json()) as { id: string; backend: string; model_route: string };
    expect(body.id).toBe("m3ta-strategist");
    expect(body.backend).toBe("kernel");
    expect(body.model_route).toBe("m3ta-reasoning");
  });

  it("GET /personas/m3ta-coach returns the lyzr-backed pointer with resolved env", async () => {
    const res = handlePersonas(new Request("http://x/personas/m3ta-coach"));
    expect(res.status).toBe(200);
    const body = (await res.json()) as {
      id: string;
      backend: string;
      lyzr: { agent_id: string };
    };
    expect(body.id).toBe("m3ta-coach");
    expect(body.backend).toBe("lyzr");
    expect(body.lyzr.agent_id).toBe("test-stub-agt-id");
  });

  it("GET /personas/nope returns 404", async () => {
    const res = handlePersonas(new Request("http://x/personas/nope"));
    expect(res.status).toBe(404);
  });

  it("GET /personas/INVALID returns 400", async () => {
    const res = handlePersonas(new Request("http://x/personas/INVALID"));
    expect(res.status).toBe(400);
  });

  it("non-GET to /personas returns 404", async () => {
    const res = handlePersonas(new Request("http://x/personas", { method: "POST" }));
    expect(res.status).toBe(404);
  });

  it("GET / returns 404 (unknown path)", async () => {
    const res = handlePersonas(new Request("http://x/"));
    expect(res.status).toBe(404);
  });
});
