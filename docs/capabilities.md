# Capability coverage

Every registered MCP tool is invoked by `tests/test_mcp.py`. The test compares the invoked
names with actual tool discovery and fails if an exposed tool is missing coverage.

| Capability | Implementation | Verification |
| --- | --- | --- |
| Device registry | Known model metadata. S6 supported | Protocol test and prior S6 Windows observations |
| Installed action discovery | Vendor plugin manifests | Protocol fixture |
| Profile/page inspection | Read existing manifests and hashes | Protocol fixture. actual Development read |
| Existing key/knob settings | Preview, matching JSON types, guarded apply | Protocol fixture preserving knob settings. prior Windows knob observations |
| Clone/create-from-template/remove | Existing same-page single actions | Unit and protocol fixtures |
| Ordered action flows | Replace target with native sequential Multi Action | Order/copy/validation tests and protocol write/read-back |
| Icon set/reuse/clear | Normalized PNG copies | Unit and protocol fixtures. prior S6 Windows icon observations |
| Icon preparation | 1254 x 1254 PNG. padding and no-overwrite | Unit and protocol fixtures |
| Boot artwork preparation | Registry dimensions. PNG output | Unit and protocol fixtures |
| Scene creation from selected controls | New profile, optional copied actions/icons and SQLite catalog row | Protocol fixture, empty-actions check, registration and duplicate rejection |
| Scene rename/delete | Hash-checked name changes and catalog removal with folder archival | Protocol CRUD tests |
| Name-based Toolbox slots | Installed metadata, controller checks and explicit configuration status | Protocol and catalog construction checks |
| Multi-step hotkeys | Per-step chords and delays | Modifier, slot, order and protocol tests |
| Automatic icons | Local app/pack matching with a generated label fallback | SVG contrast, fallback, opt-out and protocol tests |
| Solid icon backgrounds | Optional RGB fill and edge-connected background replacement | Pixel/color regression test |
| App close/reopen | Windows only, explicit forced exit option | Unit failure cases and prior Windows integration checks |
| Backups/stale-write prevention | Manifest/catalog snapshots and hashes | Unit and protocol fixtures |
| Concurrent cooperating MCP editors | Advisory profile-root lock | Cross-process test |
| HTTP authentication | Loopback, Bearer token, duplicate-header rejection | ASGI authentication tests |
| Stdio transport | MCP SDK | Real subprocess protocol tests |

## Unsupported or unverified

Direct USB control, firmware writes, boot-logo uploads, live device event streaming, arbitrary
Toolbox invocation, page creation/reordering/deletion, and hot profile
updates without restarting the vendor app are not exposed by this release. Scene creation
requires the observed vendor catalog schema. unknown schemas fail closed. macOS/Linux hardware
and automatic app lifecycle are not verified. A sequence requests actions in order but cannot
guarantee that an app has finished loading before the next action starts.

Installed actions can be constructed from their name or UUID using native metadata. Unknown plugin settings are not invented. Actions without a published settings schema still require native-app verification. Existing source templates remain supported. Whole-app execution parity is not claimed.
