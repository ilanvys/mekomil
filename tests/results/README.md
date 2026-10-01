# Automated browser benchmark result

[`claude-browser-2026-09-30.json`](claude-browser-2026-09-30.json) is the
authoritative normalized result of the completed Claude.ai benchmark. It contains
one normalized record for each fixture in `../cases.tsv`.

The operator opened Claude's Chrome browser extension and gave it the browser
procedure captured in [`../EVAL_PROMPT.md`](../EVAL_PROMPT.md). The cases ran in
several batches. Claude opened a fresh claude.ai chat for each scenario, waited
for completion, inspected tool activity and the reply, and acted as the LLM
judge for the routing verdict. The chats used Sonnet 5.5 at High effort. Cases
were rerun with the updated skill on 2026-10-01; the JSON keeps the latest
result for each case.

The current normalized total is 53/53 passing. In the 40 positive cases, at
least one skill loaded in 38 (95%). The JSON records observed loading and the
final routing verdict; raw chat transcripts and full answers were deliberately
not retained because answer-quality scoring is outside this eval.

For parallel browser runs, keep at most three Claude responses active at once.
The fourth concurrent submission can fail with `Too many responses running at
once`; retry that case after one of the active responses completes.

`failure_stage` identifies where a routing case failed. A `null` value means the
case passed.

Some latest LLM-judge decisions deliberately differ from the older strict
fixtures. In particular, M07 routed to the shelter guide rather than the
protocol skill; C01 and C06 passed without a skill; and X01/X02 passed with one
skill even though their fixtures still require two. These fixtures were not
silently changed and need a separate benchmark-design decision.

The [post-migration verification](post-migration-2026-10-01.md) records the production service
smoke suite and a clean public Claude Code install with C03 and N01 routing traces. Other hosts
remain explicitly unverified there.

The M07 shelter answer also exposed a content issue independent of routing:
official material still presents ten minutes as the general rule, while some
specific operational events require waiting for an explicit release notice.
The skill should not describe either instruction as universally applicable.
