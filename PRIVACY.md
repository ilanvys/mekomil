# Privacy

mekomIL routes a user's question in the client conversation. The MCP calls contain a
category name, skill slug, file path and optional part number. The service does not need
the question text, an account, or a user profile to serve those calls.

The service code does not log tool arguments or retain user questions. It stores generated
public catalog metadata in its deployment and caches up to 64 public upstream file bodies
per warm function instance for at most one hour after each fetch. That cache contains no
user-supplied text. Requests pass through Vercel and GitHub infrastructure, which may
process request metadata under their own policies; this project does not control those
platform logs.

The service fetches skill content from public skills-il repositories. Installed clients
receive the selected content in their conversation context, subject to that client's own
data handling. Do not put secrets in a question or in an upstream skill file.
