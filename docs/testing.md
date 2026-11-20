# Validation

The 0.3.0 test suite exercises all 11 exposed tools through a real stdio MCP session
against disposable profiles and image fixtures. Personal device configurations are not used.

Coverage includes device/action/profile discovery, icon search and preparation, boot artwork,
setting preview/apply, action cloning/removal, icon changes, stale-hash rejection and preservation
of unrelated knob settings. Unit tests also cover app exit/relaunch failures, forced close,
cross-process edit locking, output overwrite protection, orphan cleanup, bounded input,
invalid JSON numbers, invalid tokens and duplicate/missing/incorrect HTTP authorization headers.

All 24 tests passed locally on Windows Python 3.12 and Linux Python 3.12 under WSL.
Hosted Windows/macOS/Linux results are recorded in GitHub Actions, including Python 3.13.
The dependency audit found no known advisories in the audited installed dependencies after
upgrading the development environment's old pip. The unpublished project itself is not in
the advisory database and is covered by source review and tests instead.

Source installation through `uvx --python 3.12 --from . streonor-mcp --version` was verified.
Release installation uses the same runner with a pinned Git tag. GitHub access is required
while the repository remains private. No Python environment or dependencies need manual setup.

This does not establish hardware support on macOS/Linux, eliminate races with noncooperating
file writers, or guarantee recovery from disk failure. The S6 Windows key/icon checks were
observed in the preceding development session. lifecycle failure cases in CI are simulated.
