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
    full corridor hierarchy from the template. Segment prefabs are named ``<template_name>_<trial_name>.prefab``
    and are always regenerated on each call so trial-parameter edits never leave stale segment geometry on
    disk. Cue prefabs and materials are keyed by ``Cue_<name>_<length>cm`` and shared across every template
    that declares a matching cue; they are reused when present and only built when missing.

    Before any mutation, ``CreateFromTemplate`` runs a cross-template cue-texture preflight that scans every
    YAML under ``Assets/InfiniteCorridorTask/Configurations/`` and aborts the call when two templates declare
    a cue with the same ``(name, length_cm)`` identity but different textures. The shared-cue keying scheme
    makes such conflicts silently corrupt downstream prefabs, so the preflight failure surfaces as an
    ``error:`` response with the offending template pair(s) listed before any cue or segment is touched.
    Templates outside ``Configurations/`` are not visible to the MCP surface and are rejected by the Editor
    menu as well.

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
            ``Assets/InfiniteCorridorTask/Prefabs/SSO_Merging_ABC.prefab``).

    Returns:
        A response dict with ``prefab_path`` and ``hierarchy`` (recursive GameObject tree with transforms,
        components, and collider geometry).
    """
    return _unity_relay(tool="inspect_prefab", arguments={"prefab_path": prefab_path})


@mcp.tool()
def validate_prefab_against_template_tool(template_name: str) -> dict[str, Any]:
    """Validates that Unity prefabs match the YAML template's cue inventory, segment geometry, and zones.

    For each cue defined in the template, checks whether the cue prefab exists on disk. For each trial
    declared in the template's ``trial_structures``, checks whether the matching segment prefab exists
    (named ``<template_name>_<trial_name>.prefab``), compares the prefab's child cue ordering against the
    trial's ``cue_sequence``, compares the measured Z-axis length against the cue-sum length, and compares
    the StimulusTriggerZone position and size against the trial's expected zone values.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``). Must exist in the
            Unity project's ``Assets/InfiniteCorridorTask/Configurations/`` directory.

    Returns:
        A response dict with ``template_name``, ``cue_prefabs`` (per-cue prefab existence), and ``trials``
        (per-trial validation including segment prefab existence, cue ordering, segment length, and zone
        positions).
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


@mcp.tool()
def read_task_parameters_tool() -> dict[str, Any]:
    """Reads every field exposed by the Task Parameters Unity Editor window.

    Returns a single-scan snapshot of the active scene's current state plus the enumerated options
    available for each settable enum-like field and the visibility of conditionally-rendered controls.
    State, options, and visibility are all derived from the same scene walk so an agent that reads,
    modifies, and writes back values does not race against a separate enumeration pass.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with three top-level keys:

        - ``state``: per-section current values. Keys are ``actor`` (with ``model`` and ``controller``),
          ``mqtt`` (with ``ip`` and ``port``), ``display`` (with ``current_brightness``, ``brightness``,
          and ``height_in_vr``), ``camera_mapping`` (a list of per-monitor dicts containing ``monitor``,
          ``left``, ``top``, and ``camera``), and ``task`` (with ``require_lick``, ``require_wait``,
          ``track_length``, and ``track_seed``).
        - ``options``: enumerated alternatives for fields with a finite valid set. ``actor.model`` and
          ``actor.controller`` list every Resources actor prefab and scene ControllerOutput respectively
          (plus the literal ``"None"``); ``camera_mapping.camera`` lists every scene Camera not tagged
          MainCamera or named ``Main Camera`` (also plus ``"None"``).
        - ``visibility``: per-control flags indicating whether the matching control is currently rendered
          in the Parameters window. ``task.require_lick`` is ``true`` only when the scene contains a
          ``GuidanceZone``; ``task.require_wait`` is ``true`` only when the scene contains an
          ``OccupancyZone``. Writes against fields whose visibility is ``false`` are rejected by
          :func:`write_task_parameters_tool`.
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
    ``task.require_lick`` / ``task.require_wait`` when the corresponding zone is absent from the scene
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
        task: Optional dict with ``require_lick`` (bool), ``require_wait`` (bool), ``track_length``
            (float), and/or ``track_seed`` (int). ``require_lick`` is rejected when the scene has no
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
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        return error_response(
            message=(
                f"Unity Editor is not reachable. Ensure the Editor is open with the McpBridge plugin loaded "
                f"and listening on {_UNITY_BRIDGE_URL}."
            ),
        )
    except json.JSONDecodeError:
        return error_response(message="Unity bridge returned invalid JSON.")

    # The bridge contract guarantees a JSON object, but verify the shape so the typed return holds.
    if not isinstance(parsed, dict):
        return error_response(message="Unity bridge returned a non-object JSON payload.")
    return parsed
