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
def create_task_tool(template_name: str) -> dict[str, Any]:
    """Creates a Unity task end-to-end from a YAML task template.

    Generates the task prefab and the matching scene in one call. Mirrors the ``CreateTask/New Task`` Editor
    menu so the agentic and manual paths produce
    byte-equivalent assets. The prefab is built at
    ``Assets/InfiniteCorridorTask/Tasks/<template_name>.prefab`` and the scene at
    ``Assets/Scenes/<template_name>.unity``; both paths are auto-resolved from the template basename so
    every task artifact shares one name end to end. Refuses to overwrite an existing scene at the
    resolved path. Regeneration is therefore always an explicit two-step action: call
    ``delete_task_tool`` first to remove the existing task bundle (scene, prefab, segments), then call
    ``create_task_tool`` again to rebuild from scratch. The prefab itself is always regenerated because
    the template is authoritative.

    Before any mutation, the Unity-side ``CreateFromTemplate`` runs a cross-template cue-texture
    preflight that scans every YAML under ``Assets/InfiniteCorridorTask/Configurations/`` and aborts the
    call when two templates declare a cue with the same ``(name, length_cm)`` identity but different
    textures. The shared-cue keying scheme makes such conflicts silently corrupt downstream prefabs, so
    the preflight failure surfaces as an ``error:`` response with the offending template pair(s) listed
    before any cue or segment is touched. Templates outside ``Configurations/`` are not visible to the
    MCP surface and are rejected by the Editor menu as well.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``). Must exist in the
            Unity project's ``Assets/InfiniteCorridorTask/Configurations/`` directory.

    Returns:
        A response dict with ``template_name``, ``prefab_path``, ``scene_path``,
        ``simulated_controller_added``, and ``message`` on success.
    """
    return _unity_relay(tool="create_task", arguments={"template_name": template_name})


@mcp.tool()
def delete_task_tool(template_name: str) -> dict[str, Any]:
    """Removes every Unity artifact that ``create_task_tool`` produces for a given template in a single call.

    Removes the scene plus its ``savedFullScreenViews`` companion, the task prefab, and every segment prefab
    whose filename begins with the template basename. Mirrors ``create_task_tool`` — the two tools cover the
    full lifecycle of a task's generated artifacts. Cue prefabs and cue materials are intentionally not removed
    because they are shared
    across every template that declares a matching ``(name, length_cm)`` identity; deleting them
    would corrupt sibling tasks. Use ``delete_asset_tool`` for individual cue cleanup. The
    template YAML is also preserved as the source of truth — to remove the template itself, edit the
    file system directly or use a templates-side tool.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``). The same name
            used with ``create_task_tool``.

    Returns:
        A response dict with ``template_name``, ``deleted_paths`` (list of every removed asset path),
        ``deleted`` (boolean), and ``message`` on success. When a per-scene companion asset existed,
        the response also carries ``companion_deleted`` with the project-relative path of the removed
        companion. The call returns an error when no artifacts existed for the template.
    """
    return _unity_relay(tool="delete_task", arguments={"template_name": template_name})


@mcp.tool()
def inspect_prefab_tool(prefab_path: str) -> dict[str, Any]:
    """Returns the full hierarchy, components, transforms, and collider details of a Unity prefab.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        prefab_path: The project-relative path to the prefab (e.g.,
            ``Assets/InfiniteCorridorTask/Prefabs/SSO_Merging_ABC.prefab``).

    Returns:
        A response dict with ``prefab_path`` and ``hierarchy`` (recursive GameObject tree with transforms,
        components, and collider geometry).
    """
    return _unity_relay(tool="inspect_prefab", arguments={"prefab_path": prefab_path})


@mcp.tool()
def delete_asset_tool(asset_path: str) -> dict[str, Any]:
    """Deletes a non-scene Unity asset and refreshes the AssetDatabase.

    The bridge rejects deletion of hand-authored protected assets and paths outside the allowed
    directories with a descriptive error. Scene paths under ``Assets/Scenes/`` are also rejected —
    use ``delete_task_tool`` for end-to-end scene+prefab+segment cleanup. Requires the Unity Editor
    to be running with the McpBridge plugin active.

    Args:
        asset_path: The project-relative path to the asset to delete (e.g.,
            ``Assets/InfiniteCorridorTask/Cues/Cue_A_30cm.prefab``).

    Returns:
        A response dict with ``asset_path``, ``deleted``, and ``message`` on success.
    """
    return _unity_relay(tool="delete_asset", arguments={"asset_path": asset_path})


@mcp.tool()
def list_assets_tool(asset_type: str = "Prefab", search_path: str = "Assets/InfiniteCorridorTask") -> dict[str, Any]:
    """Lists Unity assets of a given type within a search path.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        asset_type: The Unity asset type filter (e.g., ``Prefab``, ``Scene``, ``Material``, ``Texture2D``).
            Defaults to ``Prefab``.
        search_path: The project-relative directory to search. Defaults to ``Assets/InfiniteCorridorTask``.

    Returns:
        A response dict with ``asset_type``, ``search_path``, and ``assets`` (list of project-relative
        paths).
    """
    return _unity_relay(
        tool="list_assets",
        arguments={"asset_type": asset_type, "search_path": search_path},
    )


@mcp.tool()
def list_scenes_tool() -> dict[str, Any]:
    """Lists all Unity scene assets in the project and identifies the currently active scene.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``scenes`` (list of project-relative scene paths) and ``active_scene``.
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
def inspect_scene_tool() -> dict[str, Any]:
    """Returns the active scene's metadata and the recursive hierarchy of every root GameObject.

    Used for pre-flight verification of agent-prepared scenes — confirms that expected components such as
    ``ActorObject``, ``MQTTClient``, ``Display`` rigs, and the Task prefab are present before entering Play
    Mode. The returned ``is_dirty`` flag also exposes whether the scene has unsaved changes that would
    affect a subsequent ``open_scene_tool`` call. Requires the Unity Editor to be running with the
    McpBridge plugin active.

    Returns:
        A response dict with ``scene_path``, ``scene_name``, ``is_dirty``, and ``root_objects``
        (list of recursive GameObject hierarchies with transforms, components, and collider geometry).
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


@mcp.tool()
def read_task_parameters_tool() -> dict[str, Any]:
    """Reads every field exposed by the Task Parameters Unity Editor window.

    Returns a single-scan snapshot of the active scene's current state plus the enumerated options
    available for each settable enum-like field and the visibility of conditionally-rendered controls.
    State, options, and visibility are all derived from the same scene walk so an agent that reads,
    modifies, and writes back values does not race against a separate enumeration pass.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with three top-level keys: ``state``, ``options``, and ``visibility``.
        The ``state`` key holds per-section current values. ``actor`` carries ``model`` and
        ``controller``. ``mqtt`` carries ``ip`` and ``port``. ``display`` carries
        ``current_brightness``, ``brightness``, and ``height_in_vr``. ``camera_mapping`` carries
        a list of per-monitor dicts with ``monitor``, ``left``, ``top``, and ``camera``. ``task``
        carries ``require_interaction``, ``require_wait``, ``track_length``, and ``track_seed``.
        The ``options`` key lists enumerated alternatives for fields with a finite valid set.
        ``actor.model`` lists every Resources actor prefab plus the literal ``"None"``.
        ``actor.controller`` lists every scene ControllerOutput plus the literal ``"None"``.
        ``camera_mapping.camera`` lists every scene Camera not tagged MainCamera or named
        ``Main Camera``, also plus ``"None"``.
        The ``visibility`` key holds per-control flags indicating whether the matching control is
        currently rendered in the Parameters window. ``task.require_interaction`` is true only when the
        scene contains a ``GuidanceZone``. ``task.require_wait`` is true only when the scene
        contains an ``OccupancyZone``. Writes against fields whose visibility is false are
        rejected by :func:`write_task_parameters_tool`.
    """
    return _unity_relay(tool="read_task_parameters")


@mcp.tool()
def write_task_parameters_tool(
    actor: dict[str, Any] | None = None,
    mqtt: dict[str, Any] | None = None,
    display: dict[str, Any] | None = None,
    camera_mapping: list[dict[str, Any]] | None = None,
    task: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Writes a subset of the Task Parameters fields in a single atomic relay call.

    Each top-level argument corresponds to one section of the Task Parameters window. Passing ``None``
    (the default) leaves the section untouched; fields within a supplied section are also individually
    optional so callers can update one value at a time. Writes flow through the same code paths the
    GUI uses, so the scene is marked dirty and modified asset files (``DisplaySettings``,
    ``savedFullScreenViews``) are flagged for save.

    Validation rejects values that fall outside the enumeration reported by
    :func:`read_task_parameters_tool`, mismatched monitor indices, and writes targeting
    ``task.require_interaction`` / ``task.require_wait`` when the corresponding zone is absent from the scene
    (mirroring the GUI's conditional rendering). The tightened require-toggle contract guarantees that
    a successful write means the flag will actually take effect at runtime.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        actor: Optional dict with ``model`` (str matching ``options.actor.model``) and/or
            ``controller`` (str matching ``options.actor.controller``).
        mqtt: Optional dict with ``ip`` (str) and/or ``port`` (int).
        display: Optional dict with ``current_brightness`` (0-100 float), ``brightness``
            (0-100 float), and/or ``height_in_vr`` (float, Unity units).
        camera_mapping: Optional list of per-monitor dicts. Each entry requires ``monitor`` (1-based
            index, matching the GUI row index) and ``camera`` (str matching
            ``options.camera_mapping.camera``). Omitted monitors keep their current assignment.
        task: Optional dict with ``require_interaction`` (bool), ``require_wait`` (bool), ``track_length``
            (float), and/or ``track_seed`` (int). ``require_interaction`` is rejected when the scene has no
            ``GuidanceZone``; ``require_wait`` is rejected when the scene has no ``OccupancyZone``.

    Returns:
        A post-write snapshot in the same shape as :func:`read_task_parameters_tool`, so callers get
        immediate confirmation of the new state without a separate read.
    """
    relay_arguments: dict[str, Any] = {}
    if actor is not None:
        relay_arguments["actor"] = actor
    if mqtt is not None:
        relay_arguments["mqtt"] = mqtt
    if display is not None:
        relay_arguments["display"] = display
    if camera_mapping is not None:
        relay_arguments["camera_mapping"] = camera_mapping
    if task is not None:
        relay_arguments["task"] = task
    return _unity_relay(tool="write_task_parameters", arguments=relay_arguments)


def _unity_relay(tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Relays a tool call to the Unity Editor's McpBridge HTTP listener.

    Args:
        tool: The tool name to invoke on the Unity side.
        arguments: The tool arguments dictionary. Defaults to an empty dict when omitted.

    Returns:
        The parsed JSON response from the Unity bridge, or an error dict if the bridge is unreachable.
    """
    relay_arguments = arguments if arguments is not None else {}
    payload = json.dumps({"tool": tool, "args": relay_arguments}).encode("utf-8")
    request = urllib.request.Request(  # noqa: S310 - hardcoded localhost URL for the Unity Editor bridge.
        url=_UNITY_BRIDGE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(url=request, timeout=30) as response:  # noqa: S310 - same localhost URL.
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        message = (
            f"Unable to reach the Unity Editor at {_UNITY_BRIDGE_URL}. Ensure the Editor is open with the "
            f"McpBridge plugin loaded and listening on this address."
        )
        return error_response(message=message)
    except json.JSONDecodeError:
        message = "Unable to parse the Unity bridge response: the payload is not valid JSON."
        return error_response(message=message)

    # The bridge contract guarantees a JSON object, but verify the shape so the typed return holds.
    if not isinstance(parsed, dict):
        message = "Unable to parse the Unity bridge response: the payload is a valid JSON value but not an object."
        return error_response(message=message)
    return parsed
