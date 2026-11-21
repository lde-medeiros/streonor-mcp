# Security

This local server can read profiles and edit their actions. Connect only trusted clients.
Stdio needs no HTTP token. HTTP binds to loopback and requires its generated Bearer token.
Do not expose the endpoint publicly or commit `token.txt`, client secrets or personal profiles.

Preview hashes prevent stale writes, backups preserve the preceding manifest, and paths are
validated inside the configured profile root. These are safeguards, not a sandbox for an
untrusted agent. A client can still request harmful configurations or force-close the vendor app.

Report vulnerabilities privately using GitHub's private vulnerability reporting when available.
If unavailable on this private repository, contact the repository owner privately rather than
posting credentials or exploit details in a public issue.
