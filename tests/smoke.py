#!/usr/bin/env python3
"""Server-level smoke tests for mekomil-mcp.

This checks what the *service* does, not what a model chooses to do with it.
Routing, ranking and disclosure are model behaviour and cannot be tested from
here -- those are cases.tsv, run by hand on each surface. See tests/README.md.

    python3 tests/smoke.py                 # all checks
    python3 tests/smoke.py S05 S07 S08     # only these
    MEKOMIL_MCP_URL=... python3 tests/smoke.py
"""
import json, os, re, sys, urllib.request, urllib.error

URL = os.environ.get("MEKOMIL_MCP_URL", "https://mekomil-mcp.vercel.app/api/mcp")
TIMEOUT = 30
# A skill that has both a references/ file and a scripts/ file, so the two
# lazily-loaded classes are covered by a real fetch rather than a listing.
SLUG, REF, SCRIPT = ("israeli-urban-renewal-owner-guide",
                     "references/tracks-and-majorities.md",
                     "scripts/majority_threshold.py")
# Long enough in Hebrew to exceed one response. 27,314 characters that escape to
# 120,378 -- the file whose live truncation at 32% is what the splitter exists for.
LONG, LONG_FILE = "israeli-pension-advisor", "SKILL_HE.md"
# The only measured survival: a real client cut a result that had delivered this many
# JSON-escaped characters. Every part must land under it, with room to spare.
CLIFF = 36_815
_id = [0]


def rpc(method, params=None):
    _id[0] += 1
    body = json.dumps({"jsonrpc": "2.0", "id": _id[0],
                       "method": method, "params": params or {}}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read().decode()
    # Streamable HTTP answers as SSE; the JSON sits on the data: line.
    for line in raw.splitlines():
        if line.startswith("data: "):
            return json.loads(line[6:])
    return json.loads(raw)


def tool_result(tool, args):
    """Return the MCP tool result envelope, including application-error metadata."""
    d = rpc("tools/call", {"name": tool, "arguments": args})
    if "error" in d:
        raise AssertionError("JSON-RPC error: " + json.dumps(d["error"]))
    return d["result"]


def call(tool, args):
    """Return the text body of a successful tool result."""
    result = tool_result(tool, args)
    assert not result.get("isError"), result
    return result["content"][0]["text"]


def app_error(tool, args, code):
    """Assert a failure is an explicit MCP application error with a stable code."""
    result = tool_result(tool, args)
    assert result.get("isError") is True, result
    payload = result.get("structuredContent")
    assert payload and payload.get("ok") is False, result
    assert payload.get("error", {}).get("code") == code, payload
    assert json.loads(result["content"][0]["text"]) == payload, result
    return payload["error"]


CHECKS = []


def check(fn):
    CHECKS.append(fn)
    return fn


@check
def S01_initialize():
    """initialize reports the expected server name and version"""
    d = rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "smoke", "version": "0"}})
    info = d["result"]["serverInfo"]
    assert info["name"] == "mekomil-mcp", f"serverInfo.name = {info['name']!r}"
    assert info["version"] == "0.2.0", f"serverInfo.version = {info['version']!r}"


@check
def S02_tools_listed():
    """all tools and the optional integer part parameter are advertised"""
    tools = {t["name"]: t for t in rpc("tools/list")["result"]["tools"]}
    assert set(tools) == {"get_catalog", "list_skill_files", "get_skill"}, set(tools)
    schema = tools["get_skill"]["inputSchema"]
    assert schema["properties"]["part"]["type"] == "integer", schema
    assert "part" not in schema.get("required", []), schema


@check
def S03_catalog_index():
    """get_catalog with no argument returns the category index"""
    t = call("get_catalog", {})
    assert "tax-and-finance" in t and "government-services" in t, t[:200]


@check
def S04_catalog_bad_category():
    """an unknown category is a typed error with the list of real ones"""
    e = app_error("get_catalog", {"category": "not-a-category"}, "UNKNOWN_CATEGORY")
    assert "tax-and-finance" in e["recovery"]["knownCategories"], e


@check
def S05_skill_default():
    """get_skill defaults to SKILL.md without exposing an upstream URL"""
    t = call("get_skill", {"slug": SLUG})
    head = t.split("\n---\n\n", 1)[0]
    assert t.startswith(f"skill: {SLUG}"), t[:200]
    assert t.splitlines()[1] == "file: SKILL.md", t[:200]
    assert "license: MIT, Copyright (c) 2026 Skills IL (Yootech)" in t, "license line missing"
    assert "https://" not in head and "raw.githubusercontent.com" not in head, head


@check
def S06_skill_hebrew():
    """SKILL_HE.md resolves and is actually Hebrew"""
    t = call("get_skill", {"slug": SLUG, "file": "SKILL_HE.md"})
    assert t.startswith(f"skill: {SLUG}"), t[:120]
    body = t.split("\n---\n\n", 1)[1]
    assert any("֐" <= c <= "ת" for c in body[:2000]), "no Hebrew in SKILL_HE.md"


@check
def S07_reference_file():
    """a references/ file is fetchable by path"""
    t = call("get_skill", {"slug": SLUG, "file": REF})
    assert t.startswith(f"skill: {SLUG}"), t[:200]
    assert REF in t.splitlines()[1], "file: line does not name the reference"
    assert len(t) > 400, f"reference suspiciously short ({len(t)} chars)"


@check
def S08_script_file():
    """a scripts/ file is fetchable, and comes back as real source"""
    t = call("get_skill", {"slug": SLUG, "file": SCRIPT})
    assert t.startswith(f"skill: {SLUG}"), t[:200]
    body = t.split("\n---\n\n", 1)[1]
    assert "def " in body or "import " in body, "does not look like Python source"


@check
def S09_unknown_slug():
    """an unknown slug is a typed error with one recovery action"""
    e = app_error("get_skill", {"slug": "no-such-skill-at-all"}, "UNKNOWN_SKILL")
    assert "Copy the slug" in e["recovery"]["action"], e


@check
def S10_unknown_file():
    """a wrong path is a typed error listing the real files"""
    e = app_error("get_skill", {"slug": SLUG, "file": "references/nope.md"}, "UNKNOWN_FILE")
    assert "SKILL.md" in e["recovery"]["availableFiles"], e


@check
def S11_list_files():
    """list_skill_files exposes both classes and returns a typed unknown-slug error"""
    t = call("list_skill_files", {"slug": SLUG})
    assert "references/" in t and "scripts/" in t, t[:300]
    app_error("list_skill_files", {"slug": "no-such-skill-at-all"}, "UNKNOWN_SKILL")


@check
def S12_no_folder_fetch():
    """a folder is not a file -- it must be refused, not silently concatenated"""
    app_error("get_skill", {"slug": SLUG, "file": "references/"}, "UNKNOWN_FILE")


@check
def S13_malicious_paths_are_not_resolved():
    """category and file traversal attempts remain inside their allowlists"""
    app_error("get_catalog", {"category": "../manifest"}, "UNKNOWN_CATEGORY")
    app_error("get_skill", {"slug": SLUG, "file": "../manifest.json"}, "UNKNOWN_FILE")


@check
def S14_invalid_parts_are_rejected():
    """zero and out-of-range parts return bounds instead of clamping"""
    for part in (0, 999):
        e = app_error("get_skill", {"slug": LONG, "file": LONG_FILE, "part": part},
                      "INVALID_PART")
        bounds = e["recovery"]["validParts"]
        assert bounds[0] == 1 and bounds[1] == e["recovery"]["totalParts"], e


def escaped_len(t):
    """The unit the client meters: JSON escaped to pure ASCII, where each Hebrew
    letter widens to a six-character \\uXXXX escape."""
    return len(json.dumps(t)) - 2


def parts_of(slug, file):
    """Walk a file part by part the way a model is told to, and hand back the
    raw results plus the bodies below each provenance block."""
    out, n = [], 1
    while True:
        t = call("get_skill", {"slug": slug, "file": file, "part": n})
        out.append(t)
        head = t.split("\n---\n\n", 1)[0]
        line = next((l for l in head.splitlines() if l.startswith("part:")), "")
        if not line or "final part" in line:
            break
        n += 1
        assert n <= 20, "runaway paging -- no part ever declared itself final"
    return out


@check
def S15_long_file_is_split_under_the_budget():
    """a long Hebrew file is split, and every part lands under the measured cliff"""
    got = parts_of(LONG, LONG_FILE)
    assert len(got) > 1, f"{LONG_FILE} came back as one part; the splitter did not engage"
    for i, t in enumerate(got, 1):
        n = escaped_len(t)
        assert n < CLIFF, f"part {i} is {n:,} escaped chars, at or over the {CLIFF:,} cliff"


@check
def S16_parts_reassemble_losslessly():
    """the parts rejoin into the whole file, including sections past the old cut"""
    bodies = []
    for t in parts_of(LONG, LONG_FILE):
        assert "\n---\n\n" in t, "no provenance separator -- cannot tell header from body"
        bodies.append(t.split("\n---\n\n", 1)[1])
    whole = "\n".join(bodies)
    # Step 6 sat just past where a real client truncated this file; step 9 is the last
    # section. Both present means nothing was dropped in the middle or off the end.
    assert "### שלב 6" in whole, "step 6 missing -- the old truncation is not fixed"
    assert "### שלב 9" in whole, "step 9 missing -- the tail is being dropped"
    assert "## מלכודות נפוצות" in whole, "the gotchas section is missing"


@check
def S17_every_result_carries_the_attribution_duty():
    """each result requires attribution without exposing an upstream URL"""
    for t in parts_of(LONG, LONG_FILE) + [call("get_skill", {"slug": SLUG, "file": SCRIPT})]:
        head = t.split("\n---\n\n", 1)[0]
        assert "[mekomIL]" in head, "no attribution directive in the provenance block"
        assert "skills-il" in head, "skills-il is not credited"
        assert "mekomIL" in head, "mekomIL is not named"
        assert head.startswith("skill:"), "skill identity is missing"
        assert "https://" not in head and "raw.githubusercontent.com" not in head, head


@check
def S18_a_non_final_part_says_so():
    """a part that is not the last one is labelled incomplete and names the next"""
    first = call("get_skill", {"slug": LONG, "file": LONG_FILE, "part": 1})
    head = first.split("\n---\n\n", 1)[0]
    line = next((l for l in head.splitlines() if l.startswith("part:")), "")
    assert line, "no part: line on a file that needs several"
    assert "INCOMPLETE" in line, f"part 1 does not declare itself incomplete: {line}"
    assert "part=2" in line, f"part 1 does not say how to get the rest: {line}"


def whole(slug, file):
    """The file itself, every part joined, with the provenance blocks stripped."""
    return "\n".join(t.split("\n---\n\n", 1)[1] for t in parts_of(slug, file))


CITED = re.compile(r"(?:scripts|references)/[A-Za-z0-9._-]+")


def files_of(slug):
    """The paths list_skill_files says exist, as a set."""
    return set(re.findall(r"^- (\S+)", call("list_skill_files", {"slug": slug}), re.M))


# --- the ladder's preconditions --------------------------------------------------------
# Whether the model *decides* to fetch a script or a reference is cases.tsv (C01-C06,
# R01-R04) and cannot be observed from here. What can be observed is whether that decision
# could possibly succeed: the skill has to name the file, the file has to exist, and what
# comes back has to be runnable. Each of those breaks silently -- a dangling citation hands
# the model "does not exist for", and a truncated script still looks like source -- and each
# one turns a compute case into a guessed number with no error anywhere.


@check
def S19_a_fetched_script_actually_runs():
    """a scripts/ file comes back as complete, compilable Python -- not a truncated blob"""
    src = whole(SLUG, SCRIPT)
    # "looks like Python" (S08) passes on a file cut in half. Compiling does not.
    compile(src, SCRIPT, "exec")
    assert "def main(" in src or "__main__" in src, "no entry point -- nothing to run"


@check
def S20_the_skill_names_its_own_script_and_references():
    """the Hebrew skill text cites the script and reference paths, so there is a rung to take"""
    body = whole(SLUG, "SKILL_HE.md")
    assert SCRIPT in body, f"SKILL_HE.md never mentions {SCRIPT} -- nothing sends a model to it"
    assert REF in body, f"SKILL_HE.md never mentions {REF}"


@check
def S21_every_cited_path_exists():
    """no skill step cites a scripts/ or references/ file that is not actually there"""
    have = files_of(SLUG)
    for f in ("SKILL.md", "SKILL_HE.md"):
        cited = set(CITED.findall(whole(SLUG, f)))
        missing = sorted(cited - have)
        assert not missing, f"{f} cites paths that do not exist: {missing}"


def main():
    only = {a.upper() for a in sys.argv[1:]}
    todo = [c for c in CHECKS if not only or c.__name__.split("_")[0] in only]
    if not todo:
        print("no checks matched", file=sys.stderr)
        return 2
    print(f"mekomil-mcp smoke  ->  {URL}\n")
    bad = 0
    for c in todo:
        cid = c.__name__.split("_")[0]
        try:
            c()
            print(f"  PASS  {cid}  {c.__doc__}")
        except AssertionError as e:
            bad += 1
            print(f"  FAIL  {cid}  {c.__doc__}\n          {e}")
        except Exception as e:
            bad += 1
            print(f"  ERROR {cid}  {c.__doc__}\n          {type(e).__name__}: {e}")
    print(f"\n{len(todo) - bad}/{len(todo)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
