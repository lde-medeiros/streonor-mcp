# Security

This local server can read profiles and edit their actions. Connect only trusted clients.
Stdio needs no HTTP token. HTTP binds to loopback and requires its generated Bearer token.
Do not expose the endpoint publicly or commit `token.txt`, client secrets or personal profiles.

Preview hashes prevent stale writes, backups preserve the preceding manifest, and paths are
validated inside the configured profile root. These are safeguards, not a sandbox for an
untrusted agent. A client can still request harmful configurations or force-close the vendor app.

Cooperating MCP instances serialize edits with an advisory lock in the profile root. The
vendor app and unrelated editors do not honor that lock, so process and hash checks remain
necessary. Do not use a shared profile while its vendor app runs on another computer or OS.
Input limits are 32 MiB per manifest and 16 MiB / 16 million pixels per icon. Standalone image
outputs are published without replacing an existing file. Failed profile edits remove their
uncommitted icon files. backups are retained. No backup pruning occurs automatically.

Report vulnerabilities privately using GitHub's private vulnerability reporting when available.
If unavailable on this private repository, contact the repository owner privately rather than
posting credentials or exploit details in a public issue.
