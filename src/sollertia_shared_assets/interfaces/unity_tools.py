"""Provides MCP tools for interacting with the Unity Editor via the McpBridge HTTP relay.

All tools in this module delegate to the Unity Editor's McpBridge plugin and require the Editor to be
running with the plugin active.
"""

from __future__ import annotations

import json
from typing import Any, Literal
import urllib.error
import urllib.request

from .mcp_instance import (
    mcp,
    error_response,
)

_UNITY_BRIDGE_URL: str = "http://localhost:8090/"
"""URL of the McpBridge HTTP listener running inside the Unity Editor."""


@mcp.tool()
def generate_task_prefab_tool(template_name: str, save_path: str | None = None) -> dict[str, Any]:
    """Generates a Task prefab in Unity from a YAML task template.

    Delegates to the Unity Editor's CreateTask pipeline, which builds cue prefabs, segment prefabs, and the
    full corridor hierarchy from the template. Existing cue and segment prefabs are reused as-is — to force
    regeneration after editing the YAML, delete the affected prefabs via ``delete_unity_asset_tool`` first.
    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``). Must exist in the
            Unity project's ``Assets/InfiniteCorridorTask/Configurations/`` directory.
        save_path: The project-relative path where the task prefab will be saved. When omitted, defaults to
            ``Assets/InfiniteCorridorTask/Tasks/<template_name>.prefab``.

    Returns:
        A response dict with ``prefab_path``, ``template_name``, and ``message`` on success.
    """
    relay_arguments: dict[str, Any] = {"template_name": template_name}
    if save_path is not None:
        relay_arguments["save_path"] = save_path
    return _unity_relay(tool="generate_task_prefab", arguments=relay_arguments)


@mcp.tool()
def inspect_prefab_tool(prefab_path: str) -> dict[str, Any]:
    """Returns the full hierarchy, components, transforms, and collider details of a Unity prefab.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        prefab_path: The project-relative path to the prefab (e.g.,
            ``Assets/InfiniteCorridorTask/Prefabs/Segment_abc_40cm.prefab``).

    Returns:
        A response dict with ``prefab_path`` and ``hierarchy`` (recursive GameObject tree with transforms,
        components, and collider geometry).
    """
    return _unity_relay(tool="inspect_prefab", arguments={"prefab_path": prefab_path})


@mcp.tool()
def validate_prefab_against_template_tool(template_name: str) -> dict[str, Any]:
    """Validates that Unity prefabs match the YAML template's cue inventory, segment geometry, and zones.

    For each cue defined in the template, checks whether the cue prefab exists on disk. For each segment
    referenced by the template, checks whether the segment prefab exists. Compares the prefab's child
    cue ordering against the template's ``cue_sequence``. Compares the prefab's measured z-axis length
    against the cue-sum length. When the segment has a trial structure, also compares the
    StimulusTriggerZone position and size against the trial's expected values.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``). Must exist in the
            Unity project's ``Assets/InfiniteCorridorTask/Configurations/`` directory.

    Returns:
        A response dict with ``template_name``, ``cue_prefabs`` (per-cue prefab existence), and
        ``segments`` (per-segment validation including cue ordering, segment length, and zone positions).
    """
    return _unity_relay(tool="validate_prefab_against_template", arguments={"template_name": template_name})


@mcp.tool()
def delete_unity_asset_tool(asset_path: str) -> dict[str, Any]:
    """Deletes a Unity asset and refreshes the AssetDatabase.

    Used to force regeneration of a stale cue, segment, or task prefab on the next
    ``generate_task_prefab_tool`` call. The bridge rejects deletion of hand-authored protected assets and
    paths outside the allowed directories with a descriptive error. Requires the Unity Editor to be
    running with the McpBridge plugin active.

    Args:
        asset_path: The project-relative path to the asset to delete (e.g.,
            ``Assets/InfiniteCorridorTask/Cues/Cue_A.prefab``).

    Returns:
        A response dict with ``asset_path``, ``deleted``, and ``message`` on success.
    """
    return _unity_relay(tool="delete_unity_asset", arguments={"asset_path": asset_path})


@mcp.tool()
def list_unity_assets_tool(
    asset_type: str = "Prefab", search_path: str = "Assets/InfiniteCorridorTask"
) -> dict[str, Any]:
    """Lists Unity assets of a given type within a search path.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        asset_type: The Unity asset type filter (e.g., ``Prefab``, ``Scene``, ``Material``, ``Texture2D``).
            Defaults to ``Prefab``.
        search_path: The project-relative directory to search. Defaults to ``Assets/InfiniteCorridorTask``.

    Returns:
        A response dict with ``asset_type``, ``search_path``, ``assets`` (list of project-relative paths),
        and ``count``.
    """
    response = _unity_relay(tool="list_unity_assets", arguments={"type": asset_type, "path": search_path})
    # Renames the Unity-side ``type`` key to ``asset_type`` so callers see a single uniform name.
    if "type" in response:
        response["asset_type"] = response.pop("type")
    return response


@mcp.tool()
def list_scenes_tool() -> dict[str, Any]:
    """Lists all Unity scene assets in the project and identifies the currently active scene.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``scenes`` (list of project-relative scene paths), ``active_scene``, and
        ``count``.
    """
    return _unity_relay(tool="list_scenes")


@mcp.tool()
def open_scene_tool(scene_path: str, unsaved_changes: Literal["save", "discard"] | None = None) -> dict[str, Any]:
    """Opens a Unity scene in the Editor after applying the unsaved-changes policy.

    When the active scene has unsaved edits and ``unsaved_changes`` is omitted, the bridge returns an error
    instead of switching scenes. Agentic callers should ask the user whether to save or discard the edits,
    then retry with the chosen value. ``save`` persists the active scene before switching; ``discard``
    abandons the edits silently. When the active scene is clean, the value is ignored.
    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        scene_path: The project-relative path to the scene (e.g., ``Assets/Scenes/SSO_Merging.unity``).
        unsaved_changes: The policy applied when the active scene has unsaved edits. ``save`` persists the
            active scene first, ``discard`` abandons the edits, and ``None`` returns an error so the caller
            can prompt the user.

    Returns:
        A response dict with ``scene_path`` and ``message`` on success.
    """
    relay_arguments: dict[str, Any] = {"scene_path": scene_path}
    if unsaved_changes is not None:
        relay_arguments["unsaved_changes"] = unsaved_changes
    return _unity_relay(tool="open_scene", arguments=relay_arguments)


@mcp.tool()
def create_scene_tool(
    scene_name: str,
    task_prefab_path: str | None = None,
    unsaved_changes: Literal["save", "discard"] | None = None,
) -> dict[str, Any]:
    """Creates a new Unity scene by copying ``Assets/Scenes/ExperimentTemplate.unity``.

    The new scene is saved to ``Assets/Scenes/<scene_name>.unity``. When a task prefab path is provided,
    the prefab is instantiated in the scene. When the previously active scene has unsaved edits and
    ``unsaved_changes`` is omitted, the bridge returns an error before creating the scene. Agentic callers
    should ask the user whether to save or discard the edits, then retry with the chosen value.
    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        scene_name: The name for the new scene (without ``.unity`` extension).
        task_prefab_path: The project-relative path to a task prefab to instantiate in the scene. When
            omitted, creates an empty scene from the template.
        unsaved_changes: The policy applied when the previously active scene has unsaved edits. ``save``
            persists the previously active scene first, ``discard`` abandons the edits, and ``None``
            returns an error so the caller can prompt the user.

    Returns:
        A response dict with ``scene_path`` and ``message`` on success.
    """
    relay_arguments: dict[str, Any] = {"scene_name": scene_name}
    if task_prefab_path is not None:
        relay_arguments["task_prefab_path"] = task_prefab_path
    if unsaved_changes is not None:
        relay_arguments["unsaved_changes"] = unsaved_changes
    return _unity_relay(tool="create_scene", arguments=relay_arguments)


@mcp.tool()
def inspect_scene_tool() -> dict[str, Any]:
    """Returns the active scene's metadata and the recursive hierarchy of every root GameObject.

    Used for pre-flight verification of agent-prepared scenes — confirms that expected components such as
    ``ActorObject``, ``MQTTClient``, ``Display`` rigs, and the Task prefab are present before entering Play
    Mode. The returned ``is_dirty`` flag also exposes whether the scene has unsaved changes that would
    affect a subsequent ``open_scene_tool`` or ``create_scene_tool`` call. Requires the Unity Editor to be
    running with the McpBridge plugin active.

    Returns:
        A response dict with ``scene_path``, ``scene_name``, ``is_dirty``, ``root_count``, and
        ``root_objects`` (list of recursive GameObject hierarchies with transforms, components, and
        collider geometry).
    """
    return _unity_relay(tool="inspect_scene")


@mcp.tool()
def enter_play_mode_tool() -> dict[str, Any]:
    """Enters Play Mode in the Unity Editor.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``state`` (``playing`` when already in Play Mode, ``entering_play_mode`` while
        the transition is in progress) and ``message``.
    """
    return _unity_relay(tool="enter_play_mode")


@mcp.tool()
def exit_play_mode_tool() -> dict[str, Any]:
    """Exits Play Mode in the Unity Editor.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``state`` (``edit`` when not in Play Mode, ``exiting_play_mode`` while the
        transition is in progress) and ``message``.
    """
    return _unity_relay(tool="exit_play_mode")


@mcp.tool()
def get_play_state_tool() -> dict[str, Any]:
    """Returns the current Unity Editor play state and active scene name.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``state`` (``playing``, ``compiling``, or ``edit``) and ``active_scene``.
    """
    return _unity_relay(tool="get_play_state")


def _unity_relay(tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Relays a tool call to the Unity Editor's McpBridge HTTP listener.

    Args:
        tool: The tool name to invoke on the Unity side.
        arguments: The tool arguments dictionary. Defaults to an empty dict when omitted.

    Returns:
        The parsed JSON response from the Unity bridge, or an error dict if the bridge is unreachable.
    """
    # Constructs the JSON-encoded HTTP POST request for the Unity bridge.
    relay_arguments = arguments if arguments is not None else {}
    payload = json.dumps({"tool": tool, "args": relay_arguments}).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310 - hardcoded localhost URL for the Unity Editor bridge.
        url=_UNITY_BRIDGE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # Sends the request and parses the JSON response, handling connectivity and decode errors.
    try:
        with urllib.request.urlopen(url=request, timeout=30) as response:  # noqa: S310 - same localhost URL.
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        return error_response(
            message=(
                f"Unity Editor is not reachable. Ensure the Editor is open with the McpBridge plugin loaded "
                f"and listening on {_UNITY_BRIDGE_URL}."
            ),
        )
    except json.JSONDecodeError:
        return error_response(message="Unity bridge returned invalid JSON.")
