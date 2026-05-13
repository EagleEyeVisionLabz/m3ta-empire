import { describe, expect, it } from "vitest";
import { add } from "../src/index.js";

describe("add", () => {
  it("adds two numbers", () => {
    expect(add(2, 3)).toBe(5);
  });

  it("concatenates two strings", () => {
    // Will fail until the refactor adds string support.
    expect(add("a" as any, "b" as any)).toBe("ab");
  });
});
