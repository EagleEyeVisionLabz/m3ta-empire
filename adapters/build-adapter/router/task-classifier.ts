/**
 * task-classifier.ts
 *
 * Verb-based router for build-adapter. Standalone — does not call the
 * LiteLLM proxy. Emits a `model_route_hint` that the orchestration layer
 * (or the proxy itself, later) can pick up.
 *
 * Inputs: a free-form task description.
 * Outputs: a Classification with a route, scope, confidence, and hint.
 *
 * Keep this file pure: no I/O, no network, no filesystem. The CLI wrappers
 * import the classify() function and handle side effects themselves.
 */

export type Route =
  | "build"
  | "build-with-review"
  | "orchestrate"
  | "memory"
  | "release"
  | "unknown";

export type Scope = "file" | "package" | "monorepo" | "external" | "unknown";

export type ModelRouteHint =
  | "m3ta-default"
  | "m3ta-code"
  | "m3ta-reasoning"
  | "m3ta-fast"
  | "m3ta-heavy"
  | "m3ta-oss"
  | "m3ta-embed"
  | null;

export interface Classification {
  route: Route;
  scope: Scope;
  confidence: number; // 0.0 - 1.0
  reason: string;
  matchedVerbs: string[];
  modelRouteHint: ModelRouteHint;
}

interface VerbRule {
  pattern: RegExp;
  route: Route;
  hint: ModelRouteHint;
  weight: number;
}

// Verb rules are ordered: earlier rules win on ties. Each pattern matches
// the leading verb of a task; suffixes are tolerated.
const VERB_RULES: VerbRule[] = [
  // Build family -> build route, m3ta-code hint.
  { pattern: /^scaffold(\s|$)/i, route: "build", hint: "m3ta-code", weight: 1.0 },
  { pattern: /^generate(\s|$)/i, route: "build", hint: "m3ta-code", weight: 0.9 },
  { pattern: /^build(\s|$)/i, route: "build", hint: "m3ta-code", weight: 0.9 },
  { pattern: /^write\s+(a\s+|the\s+)?(test|tests|file|module|function|class)/i,
    route: "build", hint: "m3ta-code", weight: 0.9 },
  { pattern: /^refactor(\s|$)/i, route: "build", hint: "m3ta-code", weight: 0.9 },
  { pattern: /^port\s+/i, route: "build", hint: "m3ta-code", weight: 0.85 },
  { pattern: /^codemod(\s|$)/i, route: "build", hint: "m3ta-code", weight: 0.85 },
  { pattern: /^lint(\s|$)/i, route: "build", hint: "m3ta-fast", weight: 0.8 },
  { pattern: /^fix\s+(up|the)?\s*/i, route: "build", hint: "m3ta-code", weight: 0.8 },

  // Destructive build family -> build-with-review.
  { pattern: /^delete\s+(file|package|module|dir|directory)/i,
    route: "build-with-review", hint: "m3ta-code", weight: 0.95 },
  { pattern: /^rewrite\s+/i, route: "build-with-review", hint: "m3ta-code", weight: 0.9 },
  { pattern: /^migrate\s+/i, route: "build-with-review", hint: "m3ta-reasoning", weight: 0.9 },

  // Strategy family -> orchestration layer.
  { pattern: /^analy[sz]e(\s|$)/i, route: "orchestrate", hint: "m3ta-reasoning", weight: 0.95 },
  { pattern: /^plan(\s|$)/i, route: "orchestrate", hint: "m3ta-reasoning", weight: 0.95 },
  { pattern: /^strategi[sz]e(\s|$)/i, route: "orchestrate", hint: "m3ta-reasoning", weight: 0.95 },
  { pattern: /^decide(\s|$)/i, route: "orchestrate", hint: "m3ta-reasoning", weight: 0.9 },
  { pattern: /^compare(\s|$)/i, route: "orchestrate", hint: "m3ta-reasoning", weight: 0.9 },
  { pattern: /^design(\s|$)/i, route: "orchestrate", hint: "m3ta-reasoning", weight: 0.85 },

  // Memory family -> memory layer first.
  { pattern: /^recall(\s|$)/i, route: "memory", hint: "m3ta-fast", weight: 0.95 },
  { pattern: /^summari[sz]e(\s|$)/i, route: "memory", hint: "m3ta-fast", weight: 0.9 },
  { pattern: /^look\s+up\s+/i, route: "memory", hint: "m3ta-fast", weight: 0.9 },
  { pattern: /^remember(\s|$)/i, route: "memory", hint: "m3ta-fast", weight: 0.9 },

  // Release family -> release tooling.
  { pattern: /^ship(\s|$)/i, route: "release", hint: null, weight: 0.95 },
  { pattern: /^release(\s|$)/i, route: "release", hint: null, weight: 0.95 },
  { pattern: /^tag(\s|$)/i, route: "release", hint: null, weight: 0.9 },
  { pattern: /^merge(\s|$)/i, route: "release", hint: null, weight: 0.9 },
];

const SCOPE_RULES: { pattern: RegExp; scope: Scope }[] = [
  { pattern: /\b(monorepo|workspace|all\s+packages)\b/i, scope: "monorepo" },
  { pattern: /\b(package|module|app|core)\b/i, scope: "package" },
  { pattern: /\b(file|script|test)\b/i, scope: "file" },
  { pattern: /\b(api|endpoint|service|integration|webhook)\b/i, scope: "external" },
];

function detectScope(task: string): Scope {
  for (const rule of SCOPE_RULES) {
    if (rule.pattern.test(task)) return rule.scope;
  }
  return "unknown";
}

const DEFAULT_THRESHOLD = 0.65;

export function classify(
  task: string,
  threshold: number = DEFAULT_THRESHOLD,
): Classification {
  const trimmed = task.trim();
  if (!trimmed) {
    return {
      route: "unknown",
      scope: "unknown",
      confidence: 0,
      reason: "empty task description",
      matchedVerbs: [],
      modelRouteHint: null,
    };
  }

  const matches: { rule: VerbRule; matched: string }[] = [];
  for (const rule of VERB_RULES) {
    const m = trimmed.match(rule.pattern);
    if (m) matches.push({ rule, matched: m[0].trim() });
  }

  if (matches.length === 0) {
    return {
      route: "unknown",
      scope: detectScope(trimmed),
      confidence: 0,
      reason: "no verb match",
      matchedVerbs: [],
      modelRouteHint: null,
    };
  }

  const top = matches[0]; // earliest in VERB_RULES wins
  const confidence = top.rule.weight;
  const scope = detectScope(trimmed);
  const modelRouteHint = confidence >= threshold ? top.rule.hint : null;

  return {
    route: top.rule.route,
    scope,
    confidence,
    reason: `matched verb rule: ${top.rule.pattern}`,
    matchedVerbs: matches.map((m) => m.matched),
    modelRouteHint,
  };
}

// CLI entry point: read task from argv or stdin, emit classification JSON.
// Exits 0 on success regardless of confidence; the caller decides what to
// do with a low-confidence result.
if (import.meta.main) {
  const args = process.argv.slice(2);
  let task = args.join(" ");
  if (!task) {
    const stdinBuf = await new Response(Bun.stdin.stream()).text();
    task = stdinBuf.trim();
  }
  const result = classify(task);
  console.log(JSON.stringify(result, null, 2));
}
