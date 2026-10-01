# Catalog refresh and release checks

The daily workflow builds a complete catalog and manifest candidate and opens or updates a pull
request when metadata changes. It never merges or deploys automatically. Vercel intentionally
regenerates the manifest during a production build, so the deployed file list can be newer than
the reviewed metadata commit. Check catalog/manifest agreement and run the smoke suite after each
release deployment. Existing skill-body edits are fetched live and do not need a metadata refresh.

## 1. Build a complete candidate

Use a read-only `GITHUB_TOKEN` when available. Both generators validate their complete result
before replacing the previous output.

```bash
python3 -m pip install -r mcp/scripts/requirements.txt
python3 mcp/scripts/build_catalog.py --refresh --verify
npm --prefix mcp ci
npm --prefix mcp run manifest
npm --prefix mcp test
npm --prefix mcp run typecheck
python3 tools/check_refresh.py
git diff -- mcp/data/catalog/ mcp/data/manifest.json
```

Review removed skills, changed descriptions, category moves, file-list changes and surprising flag
changes. Do not continue if a catalog row is absent from the manifest or if a repository, skill or
file disappeared unexpectedly. An unchanged refresh preserves the manifest timestamp.

Regenerate the client artifacts and confirm they are deterministic:

```bash
python3 tools/build_bundles.py
sha256sum dist/mekomil.zip
python3 tools/build_bundles.py
sha256sum dist/mekomil.zip
git diff --exit-code -- plugin/ .claude-plugin/
```

`tools/check_refresh.py` requires exact agreement between the catalog and manifest skill sets,
checks each manifest entry, and confirms the generated plugin skill matches `skill/SKILL.md`.

## 2. Run local service checks

Build and start the production service:

```bash
npm --prefix mcp run build
npm --prefix mcp run start
```

In another terminal:

```bash
MEKOMIL_MCP_URL=http://localhost:3000/api/mcp python3 tests/smoke.py
```

All 21 checks must pass. They cover the advertised schema, typed errors, traversal rejection, file
loading, part bounds and lossless reassembly, attribution, script completeness, and cited-file
existence.

## 3. Model-facing checks

The smoke suite cannot test whether a model selects the right category or skill. The 53-case
LLM-judged routing run is recorded in `tests/results/`; five verdicts differ from strict fixtures.
Use `tests/EVAL_PROMPT.md` for targeted reruns if routing behavior changes. It is routing evidence,
not an answer-quality benchmark.

For a release, also run one Hebrew flow all the way through. `C03` is the standard high-risk flow:

```text
3 בעלי דירות מתוך 12 מסרבים לתמא. יש רוב לפרויקט?
```

The trace must show the index and relevant category lookup, selection of
`israeli-urban-renewal-owner-guide`, all parts of `SKILL_HE.md`, any cited reference or script,
and disclosure crediting skills-il through mekomIL. Record failures without silently rerunning the
case in the same conversation.

## 4. Commit boundary

Review `git status`, `git diff --check`, the generated metadata, and bundle checksums. After a
deployment, repeat the 21 service checks and clean-install positive/negative routing checks against
the new endpoint before tagging a release.
