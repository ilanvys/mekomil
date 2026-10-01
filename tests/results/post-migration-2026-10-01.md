# Post-migration verification — 2026-10-01

This record covers the public `ilanvys/mekomil` repository and the production endpoint at
`https://mekomil-mcp.vercel.app/api/mcp`. The candidate version is `0.2.0`; the release tag was
still pending when these checks ran. The deployed service came from commit `c073ead`, and the
public Claude Code install came from `main` at commit `d5a7b84`.

## Service

- Vercel production build: passed on Node.js 22.
- Anonymous endpoint access: passed after disabling Vercel Authentication for the project.
- `tests/smoke.py`: 21/21 passed against the production endpoint.
- Fixed-window WAF rule: a normal 21-check multipart session passed; a bounded test then received
  `429 Too Many Requests` after the limit was reached. The threshold is intentionally not recorded
  in this public file.

## Claude Code clean install and lifecycle

- Host: Claude Code `2.1.284` on Linux.
- Public install source: `ilanvys/mekomil`.
- Installed plugin: `mekomil@mekomil` version `0.2.0`.
- Installed components: one skill and one HTTP MCP server pointing to the production endpoint.
- Removal: plugin uninstall and marketplace removal both passed, leaving the pre-existing plugin
  list unchanged.

The install was first repeated in an isolated temporary Claude configuration. The routing checks
used the clean-installed artifact from the normal authenticated profile, passed explicitly with
`--plugin-dir` because Claude Code restricted mode ignores user-level plugin declarations. All
built-in tools were disabled; only the three read-only mekomIL MCP tools were allowed.

### C03 positive route

- Model: `claude-sonnet-5-5`.
- Effort: high.
- Prompt: `3 בעלי דירות מתוך 12 מסרבים לתמא. יש רוב לפרויקט?`
- Result: passed the post-migration routing gate.
- Observed tool sequence:
  1. `get_catalog(category="housing-and-urban-renewal")` returned an unknown-category recovery.
  2. `get_catalog()`.
  3. `get_catalog(category="legal-tech")`.
  4. `get_skill(slug="israeli-urban-renewal-owner-guide", file="SKILL_HE.md")`.
  5. `get_skill(..., file="SKILL_HE.md", part=2)`.
  6. `get_skill(..., file="SKILL_HE.md", part=3)`.
  7. `get_skill(..., file="references/tracks-and-majorities.md")`.
- The answer named `israeli-urban-renewal-owner-guide`, credited skills-il through mekomIL, and
  included a legal-advice boundary. The specialist answer itself was not independently scored.

### N01 negative route

- Model: `claude-sonnet-5-5`.
- Effort: high.
- Prompt: `תסכם לי את המייל הזה`
- Result: passed. No tool was called; Claude asked the user to paste the missing email text.

## Still unverified

Clean install, routing, upgrade, rollback and removal remain unverified on claude.ai, Cowork and
ChatGPT. No release tag or GitHub release should be published from this record alone.
