# Tests

The repository keeps two independent test layers:

| Layer | Files | What it checks |
|---|---|---|
| MCP service | `smoke.py`, `test_build_catalog.py` | Catalog and skill files can be listed, fetched, split and validated safely. |
| Skill routing | `cases.tsv`, `EVAL_PROMPT.md`, `results/` | Claude decides whether to load a skill, chooses a fitting skill and discloses the load honestly. |

Answer-quality evaluation is intentionally out of scope. The upstream
skills-il project owns the specialist content; this benchmark checks whether
mekomIL reaches the right material. Obvious factual issues may be retained as
notes in the result JSON, but they do not create a second scoring system here.

## Automated browser evaluation

The completed Claude.ai benchmark was automated with Claude's Chrome browser
extension. The operator opened the extension and supplied the browser procedure
captured in [`EVAL_PROMPT.md`](EVAL_PROMPT.md). The cases were dispatched in
several batches; that file retains the targeted rerun batch. In each batch,
Claude:

1. opened a fresh claude.ai chat for every scenario;
2. submitted the scenario and waited for the response to finish;
3. inspected tool activity, the loaded skill and the disclosure line; and
4. acted as the LLM judge, returning a routing verdict and findings.

This is an LLM-as-judge evaluation, not a deterministic unit test. The model,
effort level, date and observed outcomes are recorded in
[`results/claude-browser-2026-09-30.json`](results/claude-browser-2026-09-30.json).
That JSON consolidates the latest result for all 53 cases and is the single
authoritative result file. Full answers and chat transcripts are not retained.

Claude.ai currently allows about three responses to run concurrently. If a
fourth submission reports `Too many responses running at once`, wait for one
response to finish and retry that scenario.

## `cases.tsv`

`cases.tsv` is the canonical machine-readable scenario list. There is no Excel
copy. Its six columns define each fixture:

```text
id query expected class audience needs
```

In `expected`, `+` means both named skills are expected, `|` means either route
is accepted, and `NONE` means the router should stay silent. At most two skills
may load, and two are appropriate only when the prompt explicitly asks for two
distinct workstreams that no single skill covers.

## Service checks

Run the local unit tests:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Run the MCP smoke suite against the deployed service or a local endpoint:

```bash
python3 tests/smoke.py
MEKOMIL_MCP_URL=http://localhost:3000/api/mcp python3 tests/smoke.py
```

The smoke suite proves that retrieval works. It cannot prove that a model will
decide to retrieve a skill; that is what the browser evaluation measures.
