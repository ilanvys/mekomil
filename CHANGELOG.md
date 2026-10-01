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
- Clarified supported-catalog coverage, the one-hour content cache and best-effort support.

The first tagged release artifact and clean-install host checks remain release gates;
answer-quality scoring is outside the recorded routing benchmark.
