#!/usr/bin/env node
// Build data/manifest.json: repository default branches plus slug -> { repo, files }.
//
// Metadata only. No skill content is stored here or anywhere else in this service --
// content is fetched live per request. See lib/upstream.ts.
//
// Why the API and not raw.githubusercontent: raw serves file *bodies* and has no directory
// listing at all. Enumerating `references/` and `scripts/` -- whose names we cannot guess --
// needs a tree, and the tree only exists on api.github.com. Raw is the read path; the API is
// the discovery path, once per daily metadata refresh.
//
// 15 requests (1 org + 14 trees). Unauthenticated GitHub allows 60/hr *per IP*. The scheduled
// GitHub Action supplies its read-only GITHUB_TOKEN; set one for manual refreshes too. A partial
// manifest is worse than no update: every check below exits non-zero rather than writing a file
// that drops skills.
import { writeFileSync, mkdirSync, renameSync, rmSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ORG = "skills-il";
const MAX_FILE_BYTES = 256 * 1024;
// Repos in the org that hold no skills (CLI, MCP servers, bundles, CI).
const NOT_SKILL_REPOS = new Set([
  "skills-il-cli", "release-workflow", ".github", "mcps", "bundles",
  "shufersal-mcp", "rami-levy-mcp", "design-systems",
]);

// A token is optional and read-only -- it raises the rate limit, nothing else.
const TOKEN = process.env.GITHUB_TOKEN || process.env.GH_TOKEN;
const UA = {
  "User-Agent": "mekomil-mcp-manifest",
  Accept: "application/vnd.github+json",
  ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
};

// Empty discovery is always invalid. Larger unexpected losses are rejected later by
// tools/check_refresh_delta.py against the last committed manifest.
const MIN_REPOS = 1;
const MIN_SKILLS = 1;

function die(msg) {
  console.error(`manifest build failed: ${msg}`);
  console.error(TOKEN ? "(a token was in use)" : "(no GITHUB_TOKEN -- 60/hr per IP)");
  process.exit(1);
}

const SCRIPT_EXTENSIONS = new Set([
  ".py", ".js", ".mjs", ".cjs", ".ts", ".sh", ".sql", ".json", ".md", ".yaml", ".yml",
  ".txt", ".csv",
]);

function allowedFile(file) {
  const parts = file.split("/");
  if (parts.some((part) => !part || part === ".." || part.startsWith("."))) return false;
  if (file === "SKILL.md" || file === "SKILL_HE.md") return true;
  if (/^references\/.+\.md$/.test(file)) return true;
  if (!file.startsWith("scripts/")) return false;
  const dot = file.lastIndexOf(".");
  return dot >= 0 && SCRIPT_EXTENSIONS.has(file.slice(dot).toLowerCase());
}

async function gh(url) {
  const r = await fetch(url, { headers: UA });
  if (!r.ok) {
    const remaining = r.headers.get("x-ratelimit-remaining");
    if (r.status === 403 && remaining === "0") {
      const reset = Number(r.headers.get("x-ratelimit-reset") || 0) * 1000;
      throw new Error(`rate limited; resets ${new Date(reset).toISOString()}`);
    }
    throw new Error(`${r.status} ${url}`);
  }
  return r.json();
}

let repoRecords;
try {
  repoRecords = (await gh(`https://api.github.com/orgs/${ORG}/repos?per_page=100`))
    .filter((r) => !NOT_SKILL_REPOS.has(r.name))
    .sort((a, b) => a.name.localeCompare(b.name));
} catch (e) {
  die(`could not list ${ORG}'s repos -- ${e.message}`);
}
if (repoRecords.length < MIN_REPOS) {
  die(`only ${repoRecords.length} skill repos found, expected >= ${MIN_REPOS}`);
}

const repos = repoRecords.map((r) => r.name);
const defaultBranches = {};

const skills = {};
for (const record of repoRecords) {
  const repo = record.name;
  const branch = record.default_branch;
  if (!branch) die(`${repo} has no default_branch in GitHub metadata`);
  defaultBranches[repo] = branch;

  let result;
  try {
    result = await gh(
      `https://api.github.com/repos/${ORG}/${repo}/git/trees/${branch}?recursive=1`,
    );
  } catch (e) {
    // Never skip. A missing repo means every skill in it silently stops existing.
    die(`${repo} tree unavailable -- ${e.message}`);
  }
  if (result.truncated) die(`${repo} tree was truncated by GitHub`);

  const supportedSlugs = new Set(
    result.tree
      .filter((node) => node.type === "blob" && /^[^/.][^/]*\/SKILL\.md$/.test(node.path))
      .map((node) => node.path.split("/", 1)[0])
      .filter((slug) => !slug.startsWith("__")),
  );

  for (const node of result.tree) {
    if (node.type !== "blob") continue;
    const [slug, ...rest] = node.path.split("/");
    if (!rest.length || !supportedSlugs.has(slug)) continue;
    const file = rest.join("/");
    // Only allowlisted text formats a loader may return. Hidden files, binaries, evidence.json,
    // and optimization logs are build residue rather than skill content.
    if (!allowedFile(file)) continue;
    if (skills[slug] && skills[slug].repo !== repo) {
      die(`duplicate skill slug ${slug} in ${skills[slug].repo} and ${repo}`);
    }
    const skill = (skills[slug] ??= { repo, files: [], bytes: {} });
    skill.files.push(file);
    // The tree already carries blob sizes. Keeping every size lets runtime reject an oversized
    // file before spending an upstream request, while list_skill_files can still warn about parts.
    skill.bytes[file] = node.size;
  }
}
for (const s of Object.values(skills)) {
  s.files.sort();
}

const out = {
  generated: new Date().toISOString(),
  org: ORG,
  maxFileBytes: MAX_FILE_BYTES,
  repos,
  defaultBranches,
  skills,
};
const count = Object.keys(skills).length;
if (count < MIN_SKILLS) die(`only ${count} skills found, expected >= ${MIN_SKILLS}`);

const dir = join(dirname(fileURLToPath(import.meta.url)), "..", "data");
mkdirSync(dir, { recursive: true });
const target = join(dir, "manifest.json");
const staged = join(dir, `.manifest.${process.pid}.tmp`);
let previous;
try {
  previous = JSON.parse(readFileSync(target, "utf8"));
} catch (error) {
  if (error.code !== "ENOENT") die(`could not read previous manifest -- ${error.message}`);
}
if (previous) {
  const { generated: _oldTime, ...oldData } = previous;
  const { generated: _newTime, ...newData } = out;
  if (JSON.stringify(oldData) === JSON.stringify(newData)) {
    console.log(`manifest unchanged: ${repos.length} repos, ${count} skills`);
    process.exit(0);
  }
}
try {
  writeFileSync(staged, JSON.stringify(out, null, 1));
  // Same-directory rename is atomic: a failed fetch/build can never truncate the usable manifest.
  renameSync(staged, target);
} catch (error) {
  rmSync(staged, { force: true });
  die(`could not publish manifest -- ${error.message}`);
}

const withHe = Object.values(skills).filter((s) => s.files.includes("SKILL_HE.md")).length;
const withScripts = Object.values(skills).filter((s) => s.files.some((f) => f.startsWith("scripts/"))).length;
console.log(
  `manifest: ${repos.length} repos, ${count} skills, ` +
    `${withHe} with SKILL_HE.md, ${withScripts} with scripts/`,
);
