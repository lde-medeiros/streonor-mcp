# Everyday workflows

You can make these requests in plain language. The agent should identify the scene and control, preview the change, and verify the saved result. A scene is a layout of device controls. A flow is one button that performs several steps.

## Create: set up a work layout

> “Create a Work scene with email, calendar and GitHub buttons. Use the volume knob from my Daily scene.”

The agent reads Daily to find those existing controls. It previews and creates Work with the requested `include_coordinates`. Their settings and PNG icons are copied. The original scene stays intact.

> “Add a Calculator shortcut to Work.”

The agent finds Calculator in `list_available_actions`, then previews `create_by_name` with `action_name="Calculator"` at an empty position. It applies the preview hash and reads back the new action. It does not need an existing Calculator button to copy.

If a name is ambiguous, the agent should use `plugin/name` or the exact UUID. Actions restricted to flows cannot be placed directly on a key. Actions that require a secondary screen are not suitable for every device.

## Read: understand an existing setup

> “What do my Work buttons and knobs currently do?”

The agent uses `list_profiles` and `read_profile`. It describes the saved actions, destinations and flows. It should not change anything. Listing an installed Toolbox item only establishes that its plugin metadata is present.

## Update: point a button at your project

> “Change GitHub to open my repository's issues page. Keep its black icon.”

The agent locates the existing Website action, previews its `path` setting and applies the returned hash. It uses `auto_icon=false` to preserve the explicitly requested icon. Ordinary destination changes refresh the associated icon by default.

> “Use this image for the Calendar button.”

The agent previews and applies `set_icon`. PNG, JPEG, BMP, GIF, WebP and self-contained SVG icons are supported. Images become 1254 x 1254 PNGs. Originals are retained.

## Create: start a coding session

> “Make Start Coding open VS Code, wait half a second, then open Terminal.”

The agent can build a `set_flow` from existing OpenApps settings and the installation's own app list. It must look up the current app IDs instead of reusing IDs from another computer. Flows support existing `source_coordinate` templates and installed `action_name` entries. The latter accept user-supplied `settings` when a plugin needs them.

Use a `flow_title` such as Start Coding and ordered `flow_steps` with `delay_ms`. Each launch is requested in sequence. The flow cannot guarantee an app has finished loading before the next step starts.

## Create: run several keyboard shortcuts

> “Copy the selected text, switch to the previous app, then paste it.”

The agent creates a `set_flow` using these steps:

```json
{
  "operation": "set_flow",
  "flow_title": "Copy to previous app",
  "flow_steps": [
    {"action_name": "com.hotspot.streamdock.system.hotkey", "hotkey": "Ctrl+C"},
    {"action_name": "com.hotspot.streamdock.system.hotkey", "hotkey": "Alt+Tab", "delay_ms": 300},
    {"action_name": "com.hotspot.streamdock.system.hotkey", "hotkey": "Ctrl+V", "delay_ms": 300}
  ]
}
```

The agent supplies the actual profile and coordinate, previews this flow and applies it with the returned hash. Modifiers belong to each step. Ctrl+C is a chord, while the flow is the sequence. These shortcuts act on the focused applications. Verify focus before testing. Saved format and order are automated-test covered, but arbitrary hotkey execution is not universally hardware-verified.

## Icons: get a useful image automatically

> “Add a GitHub shortcut.”

An associated icon is assumed. The server prefers an explicit image, then a matching installed app or icon-pack image. Existing custom template icons are preserved unless a new icon query or destination requests a replacement. If there is no suitable local match, it creates a black label icon. A label is not an official brand logo.

`resolve_icon(query)` also returns a prepared path, origin and hash for explicit icon requests. It makes no network requests. Agents may obtain external logos using their other authorized tools, then pass those local files to MCP.

> “Give GitHub a black background.”

The agent uses `prepare_icon` with `background_color="#000000"` and, for a connected opaque background, `replace_edge_background=true`. It then applies the resulting file to the selected action. Check the preview because edge-connected artwork sharing the background color can also be recolored.

> “Create this button without an icon.”

The agent disables automatic icon selection and uses `clear_icon` if the selected template already has one.

## Update: change a knob or an action flow

> “Copy the zoom knob into Work, then remove the old test binding.”

The agent can copy selected source controls into a new scene or clone a same-page action into an empty position. Existing knob settings are edited with the setting preview/apply tools. It should preserve controls you did not request to change.

> “Add a longer pause before Terminal opens.”

The agent reads the current flow, changes the relevant step's delay and previews `set_flow` again. It applies the revised flow in one guarded write.

## Delete: clean up a layout

> “Remove Start Coding and the test knob. Keep my volume control.”

The agent identifies the exact coordinates, previews `remove` for each, applies the hashes, and verifies their absence. This removes device assignments. It does not uninstall applications.

> “Rename Temp to Weekend. Later, delete Weekend.”

The agent uses `preview_scene_change` and `apply_scene_change` for rename or delete. Deletion unregisters the scene and archives its entire folder under `.streonor-deleted-scenes`. Its catalog is backed up too. Deleting the last registered scene is refused. No automatic restore tool is available yet.

## When an action still needs setup

Some Toolbox items need OBS, an account, a file, a device feature or plugin-specific settings. `create_by_name` creates their native slot using installed metadata. It reports `execution_verified=false`. `configure_action` can supply a complete settings object, but the plugin remains responsible for runtime validation when no settings schema is published. The agent should disclose missing configuration rather than promise the action works.
