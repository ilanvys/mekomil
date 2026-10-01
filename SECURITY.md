# Security

The MCP service is a public, read-only endpoint. It accepts only known category names,
skill slugs, and allowlisted file paths from a generated manifest. Upstream reads are
restricted to public skills-il repositories, valid UTF-8 text, a 256 KiB body limit and
a 10-second fetch timeout. Returned skill content is untrusted reference material and
must not be executed automatically or allowed to override system or user instructions.

The deployment token used to generate metadata belongs in GitHub Actions or Vercel
secrets with read-only access. It is never needed by runtime MCP calls. Public source
code must not contain credentials, deployment state, or request traces.

Vercel request limits and usage alerts are operational settings. Review the current WAF
rule, function usage and project access before launch; the repository cannot prove their
dashboard state. A public endpoint can be abused whether its source repository is public
or private, so rate controls and usage monitoring remain necessary in either case.

Send security reports through
[GitHub private vulnerability reporting](https://github.com/ilanvys/mekomil/security/advisories/new).
Do not publish exploit details in a public issue.
