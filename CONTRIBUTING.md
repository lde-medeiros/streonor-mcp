# Contributing

Install Python 3.12+, create a virtual environment, then run `python -m pip install -e .`.
Run `python -m unittest discover -s tests` and `git diff --check` before submitting a change.
CI covers Windows, macOS and Linux; simulated tests do not establish hardware compatibility.

Add devices in `streonor_mcp/devices.py`. Only mark a device supported after documenting observed results.
Keep shared profile and image operations independent of device models. Platform paths belong in
`paths.py`; app lifecycle code belongs in `app.py`. Do not add undocumented USB write commands.

Include a regression test for safety checks or nontrivial behavior. Describe what was tested on
real hardware and what was simulated. Never submit personal profiles, tokens, app logs or captures
containing private data. Keep pull requests focused and preserve existing user configurations.
