# mekomil-mcp

The fetch service for mekomIL. The client obtains the category index and shards through
`get_catalog`.

**Why it exists:** claude.ai web chat only fetches URLs that came from the user's message or
from a prior search/fetch result. A URL read out of a bundled catalog is neither, so the web
surface cannot load a skill by fetching. An MCP tool result is not a fetch, so the rule never
engages.

## What it stores

`data/manifest.json` — repository → default branch, plus slug → repo and file list. Metadata only,
216 skills from the supported organization repositories; it is not a promise to mirror every entry
in the wider public registry.
Rebuild with `npm run manifest` (1 org + 14 tree requests against api.github.com).

**Set `GITHUB_TOKEN`** (any read-only token) in the Vercel project. The API allows 60/hr per
IP unauthenticated and build IPs are shared, so an untokened build can be rate limited by
someone else's traffic. The script exits non-zero rather than writing a truncated manifest,
so that shows up as a failed deploy, not as skills quietly disappearing.

The API is used because **raw.githubusercontent has no directory listing** — it serves file
bodies only. Enumerating each skill's `references/` and `scripts/`, whose names we can't
guess, needs a git tree. Discovery is the API, once per deploy; reading is raw, per request.

**No skill content is persisted.** `get_skill` fetches from raw.githubusercontent.com live on
each cold request; the in-memory map in `lib/upstream.ts` is a per-instance latency cache
that dies with the instance and holds at most 64 public file bodies for up to one hour.

## What it must never do

- Log or persist tool arguments or user questions; use arguments only to select public catalog/files.
- Serve a file that is not in the manifest.
- Present an upstream fetch failure as successfully retrieved content. A valid cached public body
  can still be served within its one-hour lifetime.
- Execute a downloaded script. Scripts are returned as untrusted reference text only.

## Tools

| Tool | In | Success |
|---|---|---|
| `get_catalog` | optional category | index, or one category shard, in `content[0].text` |
| `list_skill_files` | slug | file list for that skill, in `content[0].text` |
| `get_skill` | slug, optional file and part | that file part, with internal skill/file metadata and license, in `content[0].text` |

Application failures are MCP tool errors rather than plausible-looking skill content. They set
`isError: true`; `structuredContent` and the JSON in `content[0].text` carry the same payload:

```json
{
  "ok": false,
  "error": {
    "code": "UNKNOWN_FILE",
    "message": "…",
    "recovery": { "availableFiles": ["SKILL.md", "SKILL_HE.md"] }
  }
}
```

Stable codes are `UNKNOWN_CATEGORY`, `CATALOG_UNAVAILABLE`, `UNKNOWN_SKILL`, `UNKNOWN_FILE`,
`INVALID_PART`, `UPSTREAM_UNAVAILABLE`, `FILE_TOO_LARGE`, and `INVALID_UPSTREAM_CONTENT`.
`recovery` is omitted when there is nothing useful the caller can do.

## Runtime boundary

- A request can select only a slug and path already present in the generated manifest. Category
  names are restricted to lowercase letters, digits, and hyphens; arbitrary URLs and filesystem
  paths are never accepted.
- Only `SKILL.md`, `SKILL_HE.md`, Markdown references, and an explicit set of text-based script
  extensions enter the manifest. Hidden files and binary/build artifacts do not.
- Upstream reads time out after 10 seconds and stop at 256 KiB, even when the server omits or lies
  about `Content-Length`.
- A warm function instance keeps at most 64 public file bodies for one hour. The cache is an
  optimization, not durable storage or a correctness dependency.
- Returned upstream text is labelled untrusted. It cannot change system/user authority, request
  secrets, broaden permissions, or trigger writes, network calls, or script execution by itself.

Rate limiting belongs at the Vercel edge. Do not add an in-memory counter: serverless instances do
not share it, so it would be both bypassable and capable of rejecting a burst inconsistently. Use
one [WAF fixed-window rule](https://vercel.com/docs/vercel-firewall/vercel-waf/rate-limiting) for
`/api/mcp`; begin in Log mode around 100 requests/minute per IP, then switch it to Deny/429 after
checking that real connector traffic—including clients behind shared egress—is comfortably below
it. This is a deployment setting, not repository state.

## Deploy

Vercel. Endpoint is `/api/mcp` (Streamable HTTP). `npm run build` regenerates the manifest before
building the service, so an occasional build/deploy also refreshes file discovery. This
intentional live discovery can differ from the manifest reviewed in a metadata PR; use the
agreement check and smoke suite when releasing a deployment. Build when a repository,
skill, file list, default branch, or catalog description changes; edits to the body of an
already-listed file are fetched live and need no rebuild. No runtime env vars; `GITHUB_TOKEN` is
build-time only.

The catalog in `data/catalog/` and the manifest are generated in this repository. They can still
manifest drift independently: a skill in the manifest but not the catalog is merely unroutable,
which is safe. **A row in the catalog with no manifest entry is the unsafe direction** — the
client would offer a skill `get_skill` cannot resolve. Check both directions after a rebuild.
The complete refresh, diff-review, consistency, and local-check sequence lives in
[`docs/refresh.md`](../docs/refresh.md).

The scheduled workflow in `.github/workflows/catalog-refresh.yml` checks the public
client generator once per day, validates catalog/manifest agreement, and proposes changes
in a pull request. It does not merge or deploy automatically. Unchanged metadata preserves
the existing manifest timestamp, so routine runs produce no PR.

### First deploy

1. `GITHUB_TOKEN` in the Vercel project (build-time only, read-only, no scopes needed).
2. From the repository root, run `python3 mcp/scripts/build_catalog.py --refresh --verify`, then
   run `npm run build` from `mcp/`. The build regenerates the manifest and must print
   `manifest: 14 repos, 216 skills, …`; a non-zero exit means rate limited or upstream changed,
   and the existing metadata stays intact.
3. Check both directions of catalog/manifest drift before deploying.
4. Deploy. Endpoint: `https://<project>.vercel.app/api/mcp`.
5. Smoke it before connecting anything — `initialize` must answer with
   `serverInfo.name: "mekomil-mcp"` and version `0.2.0`; `get_skill {"slug":"green-invoice"}` must
   come back starting with `skill:`, and `get_skill {"slug":"nope"}` must be an `isError: true`
   result with code `UNKNOWN_SKILL`.
6. Add it as a custom connector on claude.ai, and run one real Hebrew question end to end.

There are no runtime env vars. If the deploy needs one later, it is a change to the privacy
contract and should be reviewed as a privacy change before it belongs in code.
