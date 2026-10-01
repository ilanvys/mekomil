import assert from "node:assert/strict";
import test from "node:test";

import { escapedLen, splitParts, withProvenance } from "../lib/upstream";

const SLUG = "example-skill";
const FILE = "scripts/example.py";
const RESPONSE_BUDGET = 30_000;

function split(body: string): string[] {
  const overhead = escapedLen(withProvenance(SLUG, FILE, "", 9, 99));
  return splitParts(body, overhead);
}

function assertLosslessAndBounded(body: string): void {
  const parts = split(body);
  assert.equal(parts.join(""), body, "parts must concatenate to the original bytes");
  for (const [index, part] of parts.entries()) {
    const response = withProvenance(SLUG, FILE, part, index + 1, parts.length);
    assert.ok(
      escapedLen(response) <= RESPONSE_BUDGET,
      `part ${index + 1} is ${escapedLen(response)} escaped characters`,
    );
  }
}

test("keeps a retained heading section within the response budget", () => {
  const body = `${"p".repeat(1_000)}\n## Large section\n${"a".repeat(18_000)}\n${"b".repeat(18_000)}`;
  assertLosslessAndBounded(body);
});

test("preserves long script lines and Unicode exactly", () => {
  const body = `value = "${"א".repeat(12_000)}"\nprint(value)\n`;
  assertLosslessAndBounded(body);
});
