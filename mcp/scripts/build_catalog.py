#!/usr/bin/env python3
"""Build mekomIL's catalog from the live skills-il org.

Emits mcp/data/catalog/_index.md (category router) plus one shard per category.
Descriptions are copied whole and never truncated -- the "Do NOT use for ..."
clause they end with is the highest-value content in the index.

Requires PyYAML so upstream frontmatter follows YAML semantics instead of a partial handwritten
parser.

  python3 mcp/scripts/build_catalog.py            # build
  python3 mcp/scripts/build_catalog.py --verify   # build, then check every row resolves
  python3 mcp/scripts/build_catalog.py --refresh  # ignore the cache and refetch
"""
import argparse, json, os, re, shutil, sys, tempfile, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

try:
    import yaml
except ImportError:
    raise SystemExit("PyYAML is required: python3 -m pip install -r mcp/scripts/requirements.txt")

ORG = "skills-il"
# The shards copy each skill's description verbatim, so they carry the upstream MIT notice.
NOTICE = "Descriptions: Copyright (c) 2026 Skills IL (Yootech), MIT License. See THIRD_PARTY_NOTICES.md."
API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, ".cache")
OUT = os.path.join(ROOT, "data", "catalog")
HE_TERMS = os.path.join(ROOT, "scripts", "hebrew_terms.tsv")
INTENTS  = os.path.join(ROOT, "scripts", "category_intents.tsv")
UA = {"User-Agent": "mekomil-catalog-builder", "Accept": "application/vnd.github+json"}
# Optional and read-only. api.github.com allows 60 requests/hour per IP unauthenticated,
# which a --refresh run can exhaust; a token raises that to 5000. Raw file reads below
# do not consume that REST quota. raw.githubusercontent is CDN-backed, but GitHub may still
# throttle excessive automated traffic under its general bandwidth/abuse policies.
if os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"):
    UA["Authorization"] = "Bearer " + (os.environ.get("GITHUB_TOKEN") or os.environ["GH_TOKEN"])

# Repos in the org that hold no skills (CLI, MCP servers, bundles, CI).
NOT_SKILL_REPOS = {"skills-il-cli", "release-workflow", ".github", "mcps",
                   "bundles", "shufersal-mcp", "rami-levy-mcp", "design-systems"}

# Ordering for _index.md: general-audience categories first.
CATEGORY_ORDER = ["tax-and-finance", "government-services", "legal-tech", "accounting",
                  "health-services", "education", "travel", "food-and-dining",
                  "localization", "communication", "marketing-growth",
                  "security-compliance", "developer-tools", "courses"]

NET   = re.compile(r"requests\.|urllib|httpx|aiohttp|http\.client|socket\.", re.I)
# Route C markers: the call needs credentials, or it writes. Neither survives a browser sandbox.
AUTH  = re.compile(r"api[_-]?key|apikey|bearer|authorization|os\.environ|getenv|client_secret|oauth|password", re.I)
WRITE = re.compile(r"requests\.(post|put|patch|delete)|\.post\(|\.put\(|[\"']POST[\"']|[\"']PUT[\"']", re.I)


def get(url, raw=False):
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]} if raw else UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def cached(key, fn):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, key)
    if os.path.exists(path) and not ARGS.refresh:
        return json.load(open(path, encoding="utf-8"))
    val = fn()
    # A killed refresh must not leave a truncated cache file that breaks the next run.
    fd, staged = tempfile.mkstemp(prefix=f".{key}.", suffix=".tmp", dir=CACHE, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(val, f)
        os.replace(staged, path)
    except BaseException:
        try:
            os.unlink(staged)
        except FileNotFoundError:
            pass
        raise
    return val


def discover():
    """-> {repo: {branch, skills: [{slug, path, py: [...]}]}}"""
    repos = json.loads(cached("org.json", lambda: get(f"{API}/orgs/{ORG}/repos?per_page=100")))
    out = {}
    for r in repos:
        name = r["name"]
        if name in NOT_SKILL_REPOS:
            continue
        tree = json.loads(cached(f"tree-{name}.json",
                                 lambda n=name, b=r["default_branch"]:
                                 get(f"{API}/repos/{ORG}/{n}/git/trees/{b}?recursive=1")))
        if tree.get("truncated"):
            print(f"  !! {name}: tree truncated, rows will be incomplete", file=sys.stderr)
        blobs = [e["path"] for e in tree.get("tree", []) if e["type"] == "blob"]
        skills = []
        for p in blobs:
            # A skill lives at <slug>/SKILL.md. Anything nested under a private directory
            # (__fixtures/, .github/) is test scaffolding: it would produce a routable row
            # that mekomIL MCP cannot resolve, because the manifest keys on the first segment.
            if any(seg.startswith(("__", ".")) for seg in p.split("/")[:-1]):
                continue
            if p.endswith("SKILL.md"):
                d = p[: -len("SKILL.md")]
                skills.append({"slug": d.rstrip("/").split("/")[-1], "path": p,
                               "py": [b for b in blobs if b.startswith(d) and b.endswith(".py")]})
        if skills:
            out[name] = {"branch": r["default_branch"], "skills": sorted(skills, key=lambda s: s["slug"])}
    return out


FRONTMATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<yaml>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL
)
PLACEHOLDER_DESCRIPTIONS = {"|", "|-", "|+", ">", ">-", ">+", "(no description)", "todo", "tbd"}


def parse_frontmatter(body, source="skill"):
    """Parse and validate one skill's YAML frontmatter.

    Catalog routing depends on the complete description, so missing delimiters, malformed YAML,
    non-mapping frontmatter, and blank/non-string descriptions are build errors rather than rows
    that silently become unroutable.
    """
    match = FRONTMATTER.match(body)
    if not match:
        raise ValueError(f"{source}: missing or unterminated YAML frontmatter")
    try:
        fm = yaml.safe_load(match.group("yaml"))
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
        raise ValueError(f"{source}: malformed YAML frontmatter ({problem})") from exc
    if not isinstance(fm, dict):
        raise ValueError(f"{source}: YAML frontmatter must be a mapping")
    description = fm.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"{source}: description must be a non-empty string")
    description = description.strip()
    if description.lower() in PLACEHOLDER_DESCRIPTIONS:
        raise ValueError(f"{source}: description is a placeholder ({description!r})")
    fm["description"] = description
    return fm


def classify(py_sources):
    """Route the skill by what its scripts do.

      -   no scripts        -> instructions only
      Sc  pure computation  -> route A, port the logic. Needs no network.
      Si  plain GET         -> route B, extract the contract and make the real call.
      Sx  auth and/or write -> route C, out of reach in a browser. Honest handoff.

    Caveat this cannot fix: the flag describes the SCRIPTS, not the skill's data
    needs. A skill with no scripts may still depend on rates that go stale.
    """
    if not py_sources:
        return "-"
    blob = "\n".join(py_sources)
    if not NET.search(blob):
        return "Sc"
    return "Sx" if (AUTH.search(blob) or WRITE.search(blob)) else "Si"


def tsv(path):
    if not os.path.exists(path):
        return {}
    out = {}
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if not line or line.startswith("#") or "\t" not in line:
            continue
        k, v = line.split("\t", 1)
        out[k.strip()] = v.strip()
    return out


def build():
    repos = discover()
    jobs = [(r, d["branch"], s) for r, d in repos.items() for s in d["skills"]]
    print(f"{len(repos)} repos, {len(jobs)} skills")

    def fetch(job):
        repo, branch, s = job
        url = f"{RAW}/{ORG}/{repo}/{branch}/{s['path']}"
        body = json.loads(cached(f"skill-{repo}-{s['slug']}.json", lambda: json.dumps(get(url, raw=True))))
        py = [json.loads(cached(f"py-{repo}-{os.path.basename(p)}.json",
                                lambda p=p: json.dumps(get(f"{RAW}/{ORG}/{repo}/{branch}/{p}", raw=True))))
              for p in s["py"][:3]]
        source = f"{repo}/{s['path']}"
        return {"repo": repo, "slug": s["slug"], "url": url,
                "fm": parse_frontmatter(body, source),
                "flag": classify(py), "n_py": len(s["py"])}

    with ThreadPoolExecutor(max_workers=12) as ex:
        rows = list(ex.map(fetch, jobs))

    he = tsv(HE_TERMS)
    intents = tsv(INTENTS)
    missing_he = [r["slug"] for r in rows if r["slug"] not in he]
    by_repo = {}
    for r in rows:
        by_repo.setdefault(r["repo"], []).append(r)
    order = [c for c in CATEGORY_ORDER if c in by_repo] + sorted(set(by_repo) - set(CATEGORY_ORDER))

    rendered = {}

    # shards
    for repo in order:
        rs = sorted(by_repo[repo], key=lambda r: r["slug"])
        L = [f"# {repo}", "",
             f"{len(rs)} skills. Load a selected skill with `get_skill` before applying it.",
             "Descriptions are the authors' own, unedited -- including the \"Do NOT use for\" clauses,",
             "which are load-bearing: they are how you tell near-misses apart.",
             NOTICE, ""]
        for r in rs:
            L.append(f"## {r['slug']}  `{r['flag']}`")
            if r["slug"] in he:
                L.append(f"**he:** {he[r['slug']]}")
            L.append(f"{r['fm'].get('description','(no description)')}")
            L.append("")
        rendered[f"{repo}.md"] = "\n".join(L)

    # router
    L = ["# Category index", "",
         "Pick 1-2 categories by what the user is ASKING ABOUT, not by the category's name.",
         "The names describe a technical domain; the lines below describe the questions.",
         "Then read only those files. Never read them all.", ""]
    for repo in order:
        rs = by_repo[repo]
        # Route on what people ask, not on the category's name.
        hint = intents.get(repo) or ", ".join(sorted(r["slug"] for r in rs)[:6])
        L.append(f"- **{repo}** ({len(rs)}) — {hint}")
    L += ["", "Flags: `-` instructions only · `Sc` port the logic and compute · "
          "`Si` extract the contract, make the real call · `Sx` needs auth or writes, out of reach here.",
          f"Generated from github.com/{ORG} — {len(rows)} skills.",
          NOTICE]
    rendered["_index.md"] = "\n".join(L)

    return rows, missing_he, rendered


def publish(rendered):
    """Replace the generated catalog only after the whole candidate is ready.

    Network, parsing, validation, or staging failures therefore leave the last usable catalog
    untouched. The short directory swap is restored from its backup if the second rename fails.
    """
    staged = tempfile.mkdtemp(prefix=".catalog-candidate-", dir=ROOT)
    backup = tempfile.mkdtemp(prefix=".catalog-previous-", dir=ROOT)
    os.rmdir(backup)  # reserve a unique path for the directory rename below
    moved_old = False
    published = False
    try:
        for name, body in rendered.items():
            with open(os.path.join(staged, name), "w", encoding="utf-8") as f:
                f.write(body)
        if os.path.isdir(OUT):
            os.replace(OUT, backup)
            moved_old = True
        os.replace(staged, OUT)
        staged = None
        published = True
    except BaseException:
        if moved_old and not os.path.exists(OUT):
            os.replace(backup, OUT)
            moved_old = False
        raise
    finally:
        if staged and os.path.isdir(staged):
            shutil.rmtree(staged)
        if published and os.path.isdir(backup):
            shutil.rmtree(backup, ignore_errors=True)


def verify(rows):
    bad = []
    dupes = {}
    for r in rows:
        dupes.setdefault(r["slug"], []).append(r["repo"])
    for slug, repos in dupes.items():
        if len(repos) > 1:
            bad.append(f"duplicate slug {slug!r} in {repos}")
    for r in rows:
        if not r["fm"].get("description"):
            bad.append(f"{r['repo']}/{r['slug']}: no description")

    def head(r):
        try:
            req = urllib.request.Request(r["url"], method="HEAD", headers={"User-Agent": UA["User-Agent"]})
            urllib.request.urlopen(req, timeout=20)
            return None
        except Exception as e:
            return f"{r['repo']}/{r['slug']}: URL failed ({e})"

    with ThreadPoolExecutor(max_workers=12) as ex:
        bad += [b for b in ex.map(head, rows) if b]
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--refresh", action="store_true")
    ARGS = ap.parse_args()

    rows, missing_he, rendered = build()

    if ARGS.verify:
        print("\nverifying...")
        bad = verify(rows)
        if bad:
            print("\n".join("  FAIL " + b for b in bad))
            print("\nkept the previous catalog unchanged", file=sys.stderr)
            sys.exit(1)
        print("  OK")

    publish(rendered)
    sizes = {f: len(body.encode("utf-8")) for f, body in rendered.items()}
    print(f"\nwrote {len(sizes)} files to mcp/data/catalog/")
    for f, n in sorted(sizes.items(), key=lambda kv: -kv[1])[:6]:
        print(f"  {f:<28} {n:>7,} bytes  ~{n//4:>5,} tok")
    print(f"  router (_index.md)         ~{sizes['_index.md']//4:,} tok")
    print(f"\nHebrew terms: {len(rows)-len(missing_he)}/{len(rows)} rows "
          f"({len(missing_he)} missing -> mcp/scripts/hebrew_terms.tsv)")
