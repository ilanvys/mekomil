import assert from "node:assert/strict";
import test from "node:test";

import { GET, POST } from "../app/api/mcp/route";

const headers = {
  "content-type": "application/json",
  accept: "application/json, text/event-stream",
};
const initialize = JSON.stringify({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2025-03-26",
    capabilities: {},
    clientInfo: { name: "security-tests", version: "1.0.0" },
  },
});

function post(body: string, extraHeaders: Record<string, string> = {}) {
  return POST(new Request("http://localhost/api/mcp", {
    method: "POST", headers: { ...headers, ...extraHeaders }, body,
  }));
}

async function rpc(response: Response) {
  const body = await response.text();
  if (response.headers.get("content-type")?.includes("text/event-stream")) {
    const data = body.split("\n").find((line) => line.startsWith("data: "));
    assert.ok(data, "MCP stream must contain a JSON-RPC response");
    return JSON.parse(data.slice(6));
  }
  return JSON.parse(body);
}

test("legacy clients can initialize with the existing server identity", async () => {
  const response = await post(initialize);
  assert.equal(response.status, 200);
  const message = await rpc(response);
  assert.deepEqual(message.result.serverInfo, { name: "mekomil-mcp", version: "0.2.0" });
});

test("tool discovery retains the three public tools", async () => {
  const response = await post(JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }));
  assert.equal(response.status, 200);
  const message = await rpc(response);
  assert.deepEqual(message.result.tools.map((tool: { name: string }) => tool.name).sort(),
    ["get_catalog", "get_skill", "list_skill_files"]);
});

test("a request at the 64 KiB byte boundary still initializes", async () => {
  const body = initialize + " ".repeat(65_536 - Buffer.byteLength(initialize));
  const response = await post(body);
  assert.equal(response.status, 200);
  assert.equal((await rpc(response)).result.serverInfo.name, "mekomil-mcp");
});

test("rejects a body over 64 KiB without Content-Length", async () => {
  const response = await post(initialize + " ".repeat(65_537 - Buffer.byteLength(initialize)));
  assert.equal(response.status, 413);
  await response.body?.cancel();
});

test("an underreported Content-Length cannot bypass the body limit", async () => {
  const response = await post(initialize + " ".repeat(65_537 - Buffer.byteLength(initialize)),
    { "content-length": "1" });
  assert.equal(response.status, 413);
  await response.body?.cancel();
});

test("chunked Hebrew input is limited by UTF-8 bytes rather than characters", async () => {
  const payload = JSON.parse(initialize);
  payload.params.clientInfo.name = "א".repeat(32_768);
  const bytes = new TextEncoder().encode(JSON.stringify(payload));
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(bytes.subarray(0, 255));
      controller.enqueue(bytes.subarray(255, 511));
      controller.enqueue(bytes.subarray(511));
      controller.close();
    },
  });
  const init: RequestInit & { duplex: "half" } = { method: "POST", headers, body, duplex: "half" };
  const response = await POST(new Request("http://localhost/api/mcp", init));
  assert.equal(response.status, 413);
  await response.body?.cancel();
});

test("tool input collections are rejected before the tool handler runs", async () => {
  const response = await post(JSON.stringify({
    jsonrpc: "2.0", id: 3, method: "tools/call",
    params: { name: "list_skill_files", arguments: { slug: "nope", unused: Array(300).fill(0) } },
  }));
  const message = await rpc(response);
  assert.equal(message.result.isError, true);
  assert.match(message.result.content[0].text, /more than the maximum of 256 elements/);
  assert.notEqual(message.result.structuredContent?.error?.code, "UNKNOWN_SKILL");
});

test("nested tool input collections count toward the element limit", async () => {
  const nested = Array.from({ length: 20 }, () => ({ a: Array(12).fill(0) }));
  const response = await post(JSON.stringify({
    jsonrpc: "2.0", id: 5, method: "tools/call",
    params: { name: "list_skill_files", arguments: { slug: "nope", unused: nested } },
  }));
  const message = await rpc(response);
  assert.equal(message.result.isError, true);
  assert.match(message.result.content[0].text, /more than the maximum of 256 elements/);
});

test("tool input exactly at the element limit reaches the tool", async () => {
  // slug + unused + 254 array elements = 256.
  const response = await post(JSON.stringify({
    jsonrpc: "2.0", id: 6, method: "tools/call",
    params: { name: "list_skill_files", arguments: { slug: "nope", unused: Array(254).fill(0) } },
  }));
  const message = await rpc(response);
  assert.equal(message.result.structuredContent.error.code, "UNKNOWN_SKILL");
});

const modern = "2026-07-28";
const modernMeta = {
  "io.modelcontextprotocol/protocolVersion": modern,
  "io.modelcontextprotocol/clientInfo": { name: "security-tests", version: "1.0.0" },
  "io.modelcontextprotocol/clientCapabilities": {},
};
const modernCall = (id: number, args: unknown) => post(JSON.stringify({
  jsonrpc: "2.0", id, method: "tools/call",
  params: { name: "list_skill_files", arguments: args, _meta: modernMeta },
}), { "mcp-protocol-version": modern, "mcp-method": "tools/call", "mcp-name": "list_skill_files" });

test("modern-protocol tool calls keep the structured error contract", async () => {
  const message = await rpc(await modernCall(7, { slug: "nope" }));
  assert.equal(message.result.structuredContent.error.code, "UNKNOWN_SKILL");
});

test("modern-protocol tool calls enforce the element limit", async () => {
  const message = await rpc(await modernCall(8, { slug: "nope", unused: Array(300).fill(0) }));
  assert.equal(message.result.isError, true);
  assert.match(message.result.content[0].text, /more than the maximum of 256 elements/);
});

test("modern-protocol requests over 64 KiB are rejected", async () => {
  const response = await modernCall(9, { slug: "nope", pad: "x".repeat(65_536) });
  assert.equal(response.status, 413);
  await response.body?.cancel();
});

test("ordinary tool errors retain their structured recovery contract", async () => {
  const response = await post(JSON.stringify({
    jsonrpc: "2.0", id: 4, method: "tools/call",
    params: { name: "list_skill_files", arguments: { slug: "nope" } },
  }));
  const message = await rpc(response);
  assert.equal(message.result.isError, true);
  assert.equal(message.result.structuredContent.error.code, "UNKNOWN_SKILL");
  assert.deepEqual(JSON.parse(message.result.content[0].text), message.result.structuredContent);
});

test("malformed JSON remains a client error", async () => {
  const response = await post("{");
  assert.equal(response.status, 400);
  await response.body?.cancel();
});

test("legacy GET remains unsupported rather than opening a persistent session", async () => {
  const response = await GET(new Request("http://localhost/api/mcp", {
    headers: { accept: "text/event-stream", "mcp-protocol-version": "2025-03-26" },
  }));
  assert.equal(response.status, 405);
  await response.body?.cancel();
});
