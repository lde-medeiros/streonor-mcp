# Contributing

Install Python 3.12+, create a virtual environment, then run `python -m pip install -e .`.
Run `python -m unittest discover -s tests` and `git diff --check` before submitting a change.
CI covers Windows, macOS and Linux. simulated tests do not establish hardware compatibility.

Add devices in `streonor_mcp/devices.py`. Only mark a device supported after documenting observed results.
Keep shared profile and image operations independent of device models. Platform paths belong in
`paths.py`. app lifecycle code belongs in `app.py`. Do not add undocumented USB write commands.

Include a regression test for safety checks or nontrivial behavior. Describe what was tested on
real hardware and what was simulated. Never submit personal profiles, tokens, app logs or captures
containing private data. Keep pull requests focused and preserve existing user configurations.

## Make a release

1. Squash merge the release PR into `main`. Set the new version in `pyproject.toml`, the CLI, `server.json`, and the pinned install examples. Add the matching version heading and notes to `CHANGELOG.md`.
2. After **Checks** passes on the merged commit, **Prepare draft release** starts automatically. For a new version, it builds and validates the wheel and source archive and attaches them to a draft targeting that exact commit. For a retry, run the workflow from `main` in GitHub Actions.
3. Review the draft, then publish it as a stable release. GitHub creates the tag if needed. The publishing workflow checks CI and the attachment digests, uploads to PyPI, and then updates the MCP Registry. Tag pushes and prereleases do not upload packages.

If a publishing job fails, rerun only the failed jobs from the Actions run. If PyPI already has the version after a partial upload, inspect its files before retrying.
