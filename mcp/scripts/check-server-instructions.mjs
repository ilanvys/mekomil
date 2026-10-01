import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const routeSource = readFileSync(
  new URL("../app/api/mcp/route.ts", import.meta.url),
  "utf8",
);
const upstreamSource = readFileSync(
  new URL("../lib/upstream.ts", import.meta.url),
  "utf8",
);

assert.doesNotMatch(routeSource, /Load at most one skill per turn/);
assert.match(routeSource, /Load at most two skills per turn/);
assert.match(routeSource, /explicitly asks for two distinct workstreams/);
assert.match(routeSource, /Never load a second skill speculatively/);
assert.match(routeSource, /serverInfo: \{ name: "mekomil-mcp", version: "0\.2\.0" \}/);
assert.doesNotMatch(routeSource, /\bmatim(?:-mcp)?\b/i);
assert.doesNotMatch(upstreamSource, /\bmatim(?:-mcp)?\b/i);

console.log("server identity and skill-loading policy are consistent");
