# Examples

Ask your agent in plain language. It should identify the correct scene and control before changing anything. Coordinates below are illustrative. read the target profile to get the actual positions. Paths refer to the machine running the MCP server.

## Create a scene with buttons and knobs

> “Create Work using Daily's GitHub button and volume knob.”

1. `list_profiles` finds Daily. `read_profile` identifies the requested controls.
2. `preview_scene_creation` uses Daily as `source_profile`, `name="Work"`, and the requested `include_coordinates`.
3. `create_scene` receives the same source/name/coordinates, `expected_source_sha256` and `expected_registry_sha256` from the preview. Use `manage_app=true` on Windows if the app is open.
4. `read_profile` verifies Work's controls. Copied actions receive fresh IDs. referenced PNG icons are copied into the new scene. App associations are cleared.

Omit `include_coordinates` to create a blank scene. To change a copied knob, preview/apply its existing setting through the setting tools. Unknown action types require an existing template. the agent cannot invent a plugin's settings schema.

## Create or update a flow

> “Replace the cron test button with a flow that opens VS Code, then Windows Terminal.”

Read the profile and locate an existing OpenApps template with its installed application list. Preview a `set_flow` action:

```json
{
  "profile": "PROFILE-ID.sdProfile",
  "coordinate": "5,2",
  "operation": "set_flow",
  "flow_title": "Code + Terminal",
  "flow_steps": [
    {"source_coordinate": "5,0", "settings": {"appId": 129}, "delay_ms": 0},
    {"source_coordinate": "5,0", "settings": {"appId": 121}, "delay_ms": 500}
  ]
}
```

The numbers are examples from one installation. Resolve each `appId` from that template's own application list. do not reuse these numbers blindly.

Apply with the same arguments and `expected_sha256` from the preview. Repeat `set_flow` with revised steps to update the flow. The sequence requests launches in order. it does not wait for an app to finish loading.

## Delete a flow, button or knob assignment

> “Delete the Code + Terminal flow.”

> “Remove the test knob function.”

Read the profile, preview `operation="remove"` at the requested coordinate, then apply using its hash. Read back and confirm that coordinate is absent. This removes only the assignment, not the applications it used. Clone a known same-page knob template into an empty coordinate to create a knob assignment. update its existing settings with the setting tools.

## Add logos and change backgrounds

> “Put these local app logos on the six website buttons.”

1. `find_icons` searches imported packs, or use image paths supplied by the user.
2. `prepare_icon` can create square PNGs without changing a profile.
3. Preview/apply `set_icon` with the prepared path on each requested button, checking each new hash.

> “Make the GitHub icon background black.”

Read the GitHub action's current PNG path. Call `prepare_icon` with `background_color="#000000"` and, for an opaque background connected to the top-left corner, `replace_edge_background=true`. This fills that connected area with tolerance 24. Save to a new output path, then preview/apply `set_icon` using the result. The original image remains intact. Inspect the result: edge-connected artwork can also be recolored if it shares the background color. SVG application is not supported.

The server can apply local/imported raster files. It does not have a logo-download or logo-generation tool. the agent must obtain any missing assets using its other authorized tools first.

## Rename or delete a scene

> “Rename Temp to Testing.”

Preview `preview_scene_change(profile, operation="rename", new_name="Testing")`. Apply the same operation/name through `apply_scene_change` with both returned hashes, then read the scene back.

> “Delete Testing.”

Preview `operation="delete"`, then apply using the scene and catalog hashes. The scene is unregistered and its entire folder moved into `.streonor-deleted-scenes` under the profile root. The catalog is also backed up. Verify that `list_profiles` no longer lists it. Deleting the last registered scene is refused. Backups are not automatically pruned. no one-click restore tool is provided yet.

## Check what changed

> “Show me the saved flow and confirm the other keys are unchanged.”

Read the affected profile and compare it with the pre-edit snapshot. A saved configuration is not proof of physical execution: press the device control to verify the native app's behavior.
