# Validation

The 0.6.0 test suite exercises all 16 exposed tools through a real stdio MCP session
against disposable profiles and image fixtures. Personal device configurations are not used.

Coverage includes device/action/profile discovery, icon search and preparation, boot artwork,
setting preview/apply, action cloning/removal, icon changes, stale-hash rejection and preservation
of unrelated knob settings. Unit tests also cover app exit/relaunch failures, forced close,
cross-process edit locking, output overwrite protection, orphan cleanup, bounded input,
invalid JSON numbers, invalid tokens and duplicate/missing/incorrect HTTP authorization headers.

All 34 tests passed locally on Windows Python 3.12 and Linux Python 3.12 under WSL.
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

## Observed 0.5.0 Windows CRUD check

The Development test flow was read, updated and removed through MCP. A temporary knob assignment
was cloned, read, updated and removed. Existing volume and zoom assignments were preserved.
The Temp scene was read, renamed and deleted through MCP, retaining its full-folder archive and
SQLite catalog backup. Daily's GitHub icon was prepared with a black background and applied
through the guarded icon tools. These observations verify saved configurations and app relaunch.
Physical deletion/display behavior still needs the user's device check.

## 0.6.0 checks

Automatic-icon tests cover local SVG selection, contrast on a black background, preserved aspect
ratio, fallback generation, opt-out and source preservation. Hotkey tests cover modifier isolation,
unused native slots, invalid chords and step order. Name-based action creation and configuration
are exercised over MCP. A read-only construction check produced native definitions for all 156
installed Toolbox entries using each entry's declared controller and flow-only restrictions.
That check did not execute those actions or establish hardware support for their controllers.
