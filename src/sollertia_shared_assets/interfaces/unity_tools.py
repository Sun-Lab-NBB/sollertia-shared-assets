"""Provides MCP tools for interacting with the Unity Editor via the McpBridge HTTP relay.

All tools in this module delegate to the Unity Editor's McpBridge plugin and require the Editor to be
running. Tools register on the shared ``mcp`` instance from ``mcp_instance``.
"""

from __future__ import annotations

import json
from typing import Any
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
    full corridor hierarchy from the template. Requires the Unity Editor to be running with the McpBridge
    plugin active.

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
    """Validates that Unity segment prefab zone positions match the YAML template's configured values.

    For each segment referenced by the template's trial structures, checks whether the prefab exists and
    whether its StimulusTriggerZone position and size match the expected values derived from the template's
    zone start/end centimeters and cm_per_unity_unit conversion.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``).

    Returns:
        A response dict with ``template_name`` and ``segments`` (list of per-segment validation results
        including expected vs. actual zone positions and match flags).
    """
    return _unity_relay(tool="validate_prefab_against_template", arguments={"template_name": template_name})


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
        A response dict with ``type``, ``search_path``, ``assets`` (list of project-relative paths), and ``count``.
    """
    return _unity_relay(tool="list_unity_assets", arguments={"type": asset_type, "path": search_path})


@mcp.tool()
def list_scenes_tool() -> dict[str, Any]:
    """Lists all Unity scene assets in the project and identifies the currently active scene.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``scenes`` (list of project-relative scene paths), ``active_scene``, and ``count``.
    """
    return _unity_relay(tool="list_scenes")


@mcp.tool()
def open_scene_tool(scene_path: str) -> dict[str, Any]:
    """Opens a Unity scene in the Editor.

    Saves the current scene if modified before switching. Requires the Unity Editor to be running with the
    McpBridge plugin active.

    Args:
        scene_path: The project-relative path to the scene (e.g., ``Assets/Scenes/SSO_Merging.unity``).

    Returns:
        A response dict with ``scene_path`` and ``message``.
    """
    return _unity_relay(tool="open_scene", arguments={"scene_path": scene_path})


@mcp.tool()
def create_scene_tool(scene_name: str, task_prefab_path: str | None = None) -> dict[str, Any]:
    """Creates a new Unity scene by copying ExperimentTemplate.unity and optionally adding a task prefab.

    The new scene is saved to ``Assets/Scenes/<scene_name>.unity``. If a task prefab path is provided, the
    prefab is instantiated in the scene. Requires the Unity Editor to be running with the McpBridge plugin
    active.

    Args:
        scene_name: The name for the new scene (without ``.unity`` extension).
        task_prefab_path: The project-relative path to a task prefab to instantiate in the scene. When
            omitted, creates an empty scene from the template.

    Returns:
        A response dict with ``scene_path`` and ``message``.
    """
    relay_arguments: dict[str, Any] = {"scene_name": scene_name}
    if task_prefab_path is not None:
        relay_arguments["task_prefab_path"] = task_prefab_path
    return _unity_relay(tool="create_scene", arguments=relay_arguments)


@mcp.tool()
def enter_play_mode_tool() -> dict[str, Any]:
    """Enters Play Mode in the Unity Editor.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``state`` and ``message``.
    """
    return _unity_relay(tool="enter_play_mode")


@mcp.tool()
def exit_play_mode_tool() -> dict[str, Any]:
    """Exits Play Mode in the Unity Editor.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``state`` and ``message``.
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
    payload = json.dumps({"tool": tool, "args": arguments or {}}).encode("utf-8")
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
