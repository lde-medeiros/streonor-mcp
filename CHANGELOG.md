# Changelog

## 0.7.0

- Preview and reorder existing pages while preserving the current selection.
- Preview and restore controls from a backup scoped to the original scene and page.
- Prepare boot artwork with a choice of crop or black padding for the Devices menu.
- Route Create Folder to the native app so generic action creation cannot leave a broken folder button.
- Add readable titles for all 20 MCP tools and direct creation of single-key hotkey shortcuts.
- Keep valid Toolbox actions discoverable when installed plugin manifests contain malformed entries.
- Refresh the README, device-photo links, contributor links, and tool reference. Add a gallery of MCP output.
- License the independent project under MIT.
- Add issue templates for bugs and device support.

## 0.6.0

- Default icons for new actions and flows, plus destination changes.
- Local icon resolution with a generated label fallback and safe SVG support.
- Name-based installed Toolbox slots with explicit runtime configuration limits.
- Native multi-step hotkey chords with separate modifiers and delays.
- Everyday create, read, update and delete examples.

## 0.5.0

- Scene rename/delete with catalog checks and full-folder archival.
- Create scenes from selected existing buttons, knobs and flows. copy PNG assets.
- Optional solid icon backgrounds and connected edge-background replacement.
- Simple README with official device-photo links and support table. task-based examples.
- Protocol coverage for all 15 tools and scene/flow CRUD.

## 0.4.0

- Native ordered Multi Action flows built from same-page action templates.
- Blank scene preview and creation with vendor catalog registration and backup.
- Protocol coverage for all 13 tools, scene creation, duplicate rejection and ordered flows.

## 0.3.0

- Release-pinned uvx setup for Claude, Codex and JSON clients.
- Cross-process edit locks and preflight validation before closing the vendor app.
- Bounded input reads, image pixel limits and strict JSON numbers.
- Atomic, non-overwriting image output. uncommitted icon cleanup.
- Fail-closed token validation and duplicate Authorization header rejection.
- Protocol tests covering all tools plus HTTP and concurrent-editor regression tests.

## 0.2.0

- Standard Python package and `streonor-mcp` command for local stdio clients.
- Portable profile/image operations, configurable paths, Unix process checks.
- MCP tool risk annotations and server instructions.
- Windows opt-in app close/reopen around guarded edits.
- 1254 x 1254 PNG icon normalization and standalone icon preparation.
- Claude and Codex setup examples, contribution guidance and three-platform CI.

Hardware validation remains limited to the S6 Mini on Windows. Native macOS/Linux vendor
app integration and direct USB control are not verified.
