# Changelog

## Unreleased — mekomIL 0.2.0

- Moved client catalog discovery to MCP; the distributed skill and plugin no longer
  bundle category shards.
- Combined the client, service, plugin, website and documentation in the `mekomil` repository,
  with the `mekomil-mcp` service identity and endpoint.
- Added a daily validated catalog/manifest refresh proposal for this repository.
- Pinned a patched PostCSS dependency and aligned client/service version metadata.
- Deployed `mekomil-mcp.vercel.app`, verified all 21 service smoke checks against it, and enabled
  a fixed-window per-IP rate limit on the MCP route.

- Recorded the [53-case Claude.ai routing benchmark](tests/results/README.md): 53 LLM-judge
  passes and 38/40 positive skill loads, with five strict-fixture disagreements retained.
- Recorded the [post-migration production and Claude Code checks](tests/results/post-migration-2026-10-01.md),
  including the C03 positive trace and silent N01 route.
- Clarified supported-catalog coverage, the one-hour content cache and best-effort support.

The `v0.2.0` release candidate ZIP is deterministic and contains one uploadable skill folder;
answer-quality scoring is outside the recorded routing benchmark. The first GitHub release remains pending.
