"""Provides MCP tools for interacting with the Unity Editor via the McpBridge HTTP relay.

All tools in this module delegate to the Unity Editor's McpBridge plugin and require the Editor to be running with the
plugin active. On success each tool returns the McpBridge response payload verbatim. When the bridge is unreachable,
leaves the request unanswered within the timeout, or returns a payload that is not a JSON object, the tool returns a
``{"success": False, "error": <message>}`` dict instead. A bridge-side tool rejection is forwarded verbatim as the
bridge's own ``{"success": False, "error": ...}`` payload.
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

_UNITY_BRIDGE_TIMEOUT: int = 30
"""Number of seconds the relay waits for the Unity Editor to answer a request before it gives up."""


@mcp.tool()
def create_task_tool(template_name: str, unsaved_changes: Literal["save", "discard"] | None = None) -> dict[str, Any]:
    """Creates a Unity task end-to-end from a YAML task template.

    Generates the task prefab and the matching scene in one call. Mirrors the ``CreateTask/New Task`` Editor menu so the
    agentic and manual paths produce byte-equivalent assets. The prefab is built at
    ``Assets/InfiniteCorridorTask/Tasks/<template_name>.prefab`` and the scene at
    ``Assets/Scenes/<template_name>.unity``. Both paths are auto-resolved from the template basename so every task
    artifact shares one name end to end. Refuses to overwrite an existing scene at the resolved path. Regeneration is
    therefore always an explicit two-step action: call ``delete_task_tool`` first to remove the existing task bundle
    (scene, prefab, segments), then call ``create_task_tool`` again to rebuild from scratch. The prefab itself is always
    regenerated because the template is authoritative.

    Before any mutation, the Unity-side ``CreateFromTemplate`` runs a cross-template cue-texture preflight that scans
    every YAML under ``Assets/InfiniteCorridorTask/Configurations/`` and aborts the call when two templates declare a
    cue with the same ``(name, length_cm)`` identity but different textures. The shared-cue keying scheme makes such
    conflicts silently corrupt downstream prefabs, so the preflight failure surfaces as an ``error:`` response with the
    offending template pair(s) listed before any cue or segment is touched. Templates outside ``Configurations/`` are
    not visible to the MCP surface and are rejected by the Editor menu as well.

    Scene generation opens the new scene, which discards unsaved edits in the active one. When the active scene has
    unsaved edits and ``unsaved_changes`` is omitted, the bridge returns an error before any asset is written, matching
    the policy :func:`open_scene_tool` applies.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``). Must exist in the Unity
            project's ``Assets/InfiniteCorridorTask/Configurations/`` directory.
        unsaved_changes: The policy applied when the active scene has unsaved edits. ``save`` persists every open scene
            first, ``discard`` abandons the edits, and ``None`` returns an error so the caller can prompt the user.

    Returns:
        A response dict with ``template_name``, ``prefab_path``, ``scene_path``, ``simulated_controller_added``, and
        ``message`` on success.
    """
    relay_arguments: dict[str, Any] = {"template_name": template_name}
    if unsaved_changes is not None:
        relay_arguments["unsaved_changes"] = unsaved_changes
    return _unity_relay(tool="create_task", arguments=relay_arguments)


@mcp.tool()
def delete_task_tool(template_name: str) -> dict[str, Any]:
    """Removes every Unity artifact that ``create_task_tool`` produces for a given template in a single call.

    Removes the scene plus its ``savedFullScreenViews`` companion, the task prefab, and every segment prefab the
    template owns. A segment is named ``TemplateName-TrialName`` and neither half may contain a hyphen, so the prefix
    resolves to exactly one owning template even where one template basename nests another. A template name matching a
    protected hand-authored asset, such as the base scene template, is refused before anything is deleted. Mirrors
    ``create_task_tool``. The two tools cover the full lifecycle of a task's generated artifacts. Cue prefabs and cue
    materials are intentionally not removed because they are shared across every template that declares a matching
    ``(name, length_cm)`` identity. Deleting them would corrupt sibling tasks. Use ``delete_asset_tool`` for individual
    cue cleanup. The template YAML is also preserved as the source of truth. To remove the template itself, edit the
    file system directly or use a templates-side tool.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        template_name: The template filename without extension (e.g., ``SSO_Merging``). The same name used with
            ``create_task_tool``.

    Returns:
        A response dict with ``template_name``, ``deleted_paths`` (the scene, the task prefab, and every segment prefab
        removed. The per-scene companion is reported separately), ``deleted`` (boolean), and ``message`` on success.
        When a per-scene companion asset existed, the response also carries ``companion_deleted`` with the
        project-relative path of the removed companion. A cascade that located the companion but could not remove it
        reports ``companion_delete_failed`` instead, with a message naming the orphaned asset. The call returns an error
        when no artifacts existed for the template.
    """
    return _unity_relay(tool="delete_task", arguments={"template_name": template_name})


@mcp.tool()
def inspect_prefab_tool(prefab_path: str) -> dict[str, Any]:
    """Returns the full hierarchy, components, transforms, and collider details of a Unity prefab.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        prefab_path: The project-relative path to the prefab (e.g.,
            ``Assets/InfiniteCorridorTask/Prefabs/SSO_Merging-ABC.prefab``).

    Returns:
        A response dict with ``prefab_path`` and ``hierarchy``, a recursive GameObject tree. Each node carries
        ``name``, ``active_self``, its transforms, a ``components`` list of type names, and a ``component_states``
        list pairing each type with its ``enabled`` flag, which is null for a type that cannot be disabled. A node
        holding a BoxCollider also carries ``collider_center``, ``collider_size``, and ``collider_is_trigger``.
    """
    return _unity_relay(tool="inspect_prefab", arguments={"prefab_path": prefab_path})


@mcp.tool()
def clone_zone_prefab_tool(
    source_prefab: str,
    destination_prefab: str,
    root_script: str | None = None,
    regions: list[dict[str, Any]] | None = None,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Clones a canonical base zone prefab into a new trigger-zone prefab.

    Performs the prefab-authoring step of adding a new trigger zone through Unity's serialization layer, so fileIDs,
    script references, and parent-child wiring are assigned by Unity and stay consistent. The clone copies one of the
    two protected base zone prefabs, optionally swaps the root and named region modifier scripts for new compiled
    ``MonoBehaviour`` types, and applies serialized field overrides. Every requested script name is resolved before any
    asset is written, so a missing, ambiguous, or abstract script name fails with the destination left untouched. A
    failure during the later edit phase deletes the destination instead. That phase covers an unmatched or ambiguous
    region name, a wrong modifier count, and a root script that does not derive from ``StimulusTriggerZone``. It also
    covers a ``fields`` key that is unknown, of an unsupported type, or carrying a value that will not convert. With
    ``overwrite`` set, the existing asset is deleted before the copy, so such a failure leaves the path empty and the
    replaced prefab recoverable only from version control. Unity names the new prefab's root after the destination
    filename.

    This tool only produces the prefab. Wiring it into the runtime (the ``ConfigLoader`` trigger_type literal, the
    ``CreateTask`` placement branch, the ``McpBridge`` protected-path set, and the Python ``TriggerType`` registry)
    remains the documented zone-extension recipe. A new region behavior should follow the zone-modifier architecture:
    subclass an existing zone, or add a standalone ``IResettable`` registered in ``Task.FindResettableZones``, on a root
    that subclasses ``StimulusTriggerZone`` and publishes the standard ``Stimulus`` event.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        source_prefab: The project-relative path to a canonical base zone prefab, either
            ``Assets/InfiniteCorridorTask/Prefabs/StimulusTriggerZone.prefab`` or
            ``Assets/InfiniteCorridorTask/Prefabs/OccupancyTriggerZone.prefab``.
        destination_prefab: The project-relative path for the new prefab under ``Assets/InfiniteCorridorTask/Prefabs/``.
            Must end with ``.prefab`` and must not name a protected base prefab.
        root_script: Optional name of a compiled ``MonoBehaviour`` deriving from ``StimulusTriggerZone`` to replace the
            root modifier script. When omitted, the root script is kept.
        regions: Optional list of per-region edits. Each entry requires ``match``, the name of the region to modify.
            An entry may also carry ``rename``, ``script`` naming a compiled ``MonoBehaviour`` that replaces the
            region's modifier, and ``fields``, a name-to-value map of serialized field overrides applied to that
            modifier.
        overwrite: Determines whether to replace an existing prefab at ``destination_prefab``. Defaults to false, which
            makes an existing destination an error.

    Returns:
        A response dict with ``destination_prefab``, ``hierarchy`` (the new prefab's recursive GameObject tree, in the
        same shape as :func:`inspect_prefab_tool`), and a ``warning`` listing the remaining recipe steps on success.
    """
    relay_arguments: dict[str, Any] = {
        "source_prefab": source_prefab,
        "destination_prefab": destination_prefab,
        "overwrite": overwrite,
    }
    if root_script is not None:
        relay_arguments["root_script"] = root_script
    if regions is not None:
        relay_arguments["regions"] = regions
    return _unity_relay(tool="clone_zone_prefab", arguments=relay_arguments)


@mcp.tool()
def delete_asset_tool(asset_path: str) -> dict[str, Any]:
    """Deletes a non-scene Unity asset and refreshes the AssetDatabase.

    The bridge rejects deletion of hand-authored protected assets and paths outside the allowed directories with a
    descriptive error. Scene paths under ``Assets/Scenes/`` are also rejected. Use ``delete_task_tool`` for end-to-end
    scene+prefab+segment cleanup. Requires the Unity Editor to be running with the McpBridge plugin active.

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
        asset_type: The Unity asset type filter (e.g., ``Prefab``, ``Scene``, ``Material``, ``Texture2D``). Defaults to
            ``Prefab``.
        search_path: The project-relative directory to search. Defaults to ``Assets/InfiniteCorridorTask``.

    Returns:
        A response dict with ``asset_type``, ``search_path``, and ``assets`` (list of project-relative paths).
    """
    return _unity_relay(
        tool="list_assets",
        arguments={"asset_type": asset_type, "search_path": search_path},
    )


@mcp.tool()
def refresh_assets_tool() -> dict[str, Any]:
    """Imports pending asset changes into the Unity Editor and reports whether a compilation followed.

    The agentic counterpart of the Editor's automatic refresh on focus. A running Editor that nobody focuses, such
    as one left open on an unattended rig, never receives that event, so a C# file written from outside stays
    unimported and the type it declares stays unresolvable until this runs. Call it after authoring a script and
    before any tool that references the new type, such as :func:`clone_zone_prefab_tool`.

    A true ``is_compiling`` means a domain reload is in flight, while a false one does not prove the import produced
    no compilation, because the Editor may not have started one by the time the handler reads the flag. Poll
    :func:`get_play_state_tool` until it reports a state other than ``compiling`` before issuing further calls.
    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``message``, ``is_compiling``, and ``is_updating`` on success.
    """
    return _unity_relay(tool="refresh_assets")


@mcp.tool()
def list_scenes_tool() -> dict[str, Any]:
    """Lists all Unity scene assets in the project and identifies the currently active scene.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``scenes`` (list of project-relative scene paths) and ``active_scene`` (the
        project-relative path of the currently active scene, not its name).
    """
    return _unity_relay(tool="list_scenes")


@mcp.tool()
def open_scene_tool(scene_path: str, unsaved_changes: Literal["save", "discard"] | None = None) -> dict[str, Any]:
    """Opens a Unity scene in the Editor after applying the unsaved-changes policy.

    When the active scene has unsaved edits and ``unsaved_changes`` is omitted, the bridge returns an error instead of
    switching scenes. Agentic callers should ask the user whether to save or discard the edits, then retry with the
    chosen value. ``save`` persists every open scene before switching. ``discard`` abandons the edits silently. When the
    active scene is clean, the value is ignored. Requires the Unity Editor to be running with the McpBridge plugin
    active.

    Args:
        scene_path: The project-relative path to the scene (e.g., ``Assets/Scenes/SSO_Merging.unity``).
        unsaved_changes: The policy applied when the active scene has unsaved edits. ``save`` persists every open scene
            first, ``discard`` abandons the edits, and ``None`` returns an error so the caller can prompt the user.

    Returns:
        A response dict with ``scene_path`` and ``message`` on success.
    """
    relay_arguments: dict[str, Any] = {"scene_path": scene_path}
    if unsaved_changes is not None:
        relay_arguments["unsaved_changes"] = unsaved_changes
    return _unity_relay(tool="open_scene", arguments=relay_arguments)


@mcp.tool()
def save_scene_tool() -> dict[str, Any]:
    """Saves the active Unity scene to its existing asset path.

    Clears the dirty flag that any :func:`write_task_parameters_tool` call actually writing a value sets, which the Play
    Mode preflight requires. A scene that has never been saved has no asset path to write to, and the bridge returns an
    error rather than opening a save dialog, because it answers a caller that cannot dismiss one. Saving while the
    Editor sits in Play Mode is likewise refused, since the Editor discards scene edits on exit. Requires the Unity
    Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``message``, ``scene_path``, and ``is_dirty`` on success.
    """
    return _unity_relay(tool="save_scene")


@mcp.tool()
def inspect_scene_tool() -> dict[str, Any]:
    """Returns the active scene's metadata and the recursive hierarchy of every root GameObject.

    Used for pre-flight verification of agent-prepared scenes. Confirms that expected components such as
    ``ActorObject``, ``MQTTClient``, ``Display`` rigs, and the Task prefab are present before entering Play Mode. The
    returned ``is_dirty`` flag also exposes whether the scene has unsaved changes that would affect a subsequent
    ``open_scene_tool`` call. Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``scene_path``, ``scene_name``, ``is_dirty``, and ``root_objects``, a list of recursive
        GameObject hierarchies. Each node carries ``name``, ``active_self``, its transforms, a ``components`` list of
        type names, and a ``component_states`` list pairing each type with its ``enabled`` flag, which is null for a
        type that cannot be disabled. A node holding a BoxCollider also carries the three collider keys.
    """
    return _unity_relay(tool="inspect_scene")


@mcp.tool()
def enter_play_mode_tool() -> dict[str, Any]:
    """Enters Play Mode in the Unity Editor.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``state`` (``playing`` when already in Play Mode, ``entering_play_mode`` while the
        transition is in progress) and ``message``.
    """
    return _unity_relay(tool="enter_play_mode")


@mcp.tool()
def exit_play_mode_tool() -> dict[str, Any]:
    """Exits Play Mode in the Unity Editor.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with ``state`` (``edit`` when not in Play Mode, ``exiting_play_mode`` while the transition is in
        progress) and ``message``.
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

    Returns a single-scan snapshot of the active scene's current state plus the enumerated options available for each
    settable enum-like field and the visibility of conditionally-rendered controls. State, options, and visibility are
    all derived from the same scene walk so an agent that reads, modifies, and writes back values does not race against
    a separate enumeration pass.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A response dict with three top-level keys: ``state``, ``options``, and ``visibility``. The ``state`` key holds
        per-section current values. ``actor`` carries ``model`` and ``controller``. ``mqtt`` carries ``ip`` and
        ``port``. ``display`` carries ``current_brightness``, ``brightness``, and ``height_in_vr``. ``camera_mapping``
        carries a list of per-monitor dicts with ``monitor``, ``left``, ``top``, and ``camera``. ``task`` carries
        ``require_interaction``, ``require_wait``, ``track_length``, ``track_seed``, ``actor`` (the assigned actor's
        GameObject name, or null when the reference is unassigned), and ``config_path``. Neither of the last two is
        writable, because the Parameters window exposes no control for either, though the window assigns ``actor``
        itself whenever it draws the Task section against a scene that has one. A section is null when the scene holds
        no matching component. The ``options`` key lists enumerated alternatives for fields with a finite valid set.
        ``actor.model`` lists every Resources actor prefab plus the literal ``"None"``. ``actor.controller`` lists every
        scene ControllerOutput plus the literal ``"None"``. ``camera_mapping.camera`` lists every scene Camera not
        tagged MainCamera or named ``Main Camera``, also plus ``"None"``. The ``visibility`` key holds per-control flags
        indicating whether the matching control is currently rendered in the Parameters window.
        ``task.require_interaction`` is true only when the scene contains a ``GuidanceZone``. ``task.require_wait`` is
        true only when the scene contains an ``OccupancyZone``. Writes against fields whose visibility is false are
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

    Each top-level argument corresponds to one section of the Task Parameters window. Passing ``None`` (the default)
    leaves the section untouched. Fields within a supplied section are also individually optional, but a field is
    omitted by leaving its key out of the dict rather than by setting it to ``None``. An explicit ``None`` reaching
    ``mqtt.port``, any ``display`` field, or ``task.require_interaction``, ``require_wait``, or ``track_seed`` converts
    to ``0`` or ``false`` and is written, and the call still reports success. Writes flow through the same code paths
    the GUI uses, so the scene is marked dirty and modified asset files (``DisplaySettings``, ``savedFullScreenViews``)
    are flagged for save.

    Validation rejects values that fall outside the enumeration reported by :func:`read_task_parameters_tool`,
    mismatched monitor indices, and writes targeting ``task.require_interaction`` / ``task.require_wait`` when the
    corresponding zone is absent from the scene (mirroring the GUI's conditional rendering). The tightened
    require-toggle contract guarantees that a successful write means the flag will actually take effect at runtime.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        actor: Optional dict with ``model`` (str matching ``options.actor.model``) and/or ``controller`` (str matching
            ``options.actor.controller``).
        mqtt: Optional dict with ``ip`` (str) and/or ``port`` (int).
        display: Optional dict with ``current_brightness`` (0-100 float), ``brightness`` (0-100 float), and/or
            ``height_in_vr`` (float, Unity units).
        camera_mapping: Optional list of per-monitor dicts. Each entry requires ``monitor`` (1-based index, matching the
            GUI row index), and an entry that omits it is rejected along with the whole write. ``camera`` (str matching
            ``options.camera_mapping.camera``) is optional, and an entry that omits it, carries a non-string value, or
            is not an object at all is skipped rather than rejected. Omitted monitors keep their current assignment.
            The whole write is refused when the host detected no monitors, because assigning against an empty list
            would clear the saved mapping.
        task: Optional dict with ``require_interaction`` (bool), ``require_wait`` (bool), ``track_length`` (float),
            and/or ``track_seed`` (int). ``require_interaction`` is rejected when the scene has no ``GuidanceZone``.
            ``require_wait`` is rejected when the scene has no ``OccupancyZone``. ``track_length`` must be a positive,
            finite number of Unity units long enough to fill one corridor.

    Returns:
        A post-write snapshot in the same shape as :func:`read_task_parameters_tool`, so callers get immediate
        confirmation of the new state without a separate read.
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


@mcp.tool()
def refresh_monitors_tool() -> dict[str, Any]:
    """Re-detects the system monitors attached to the Unity Editor host and returns a fresh snapshot.

    The agentic counterpart of the Camera Mapping section's Refresh Monitor Positions button, sharing the same
    Unity-side code path so both re-detect identically. Existing camera assignments carry across by monitor index, so
    removing a monitor from the middle of the arrangement shifts every later assignment up by one slot. The refreshed
    list is not persisted to the scene's companion asset until a camera assignment is written via
    :func:`write_task_parameters_tool`.

    The bridge builds its monitor enumeration once per scene and reuses it across requests, so call this after
    physically changing the monitor arrangement. A snapshot that already matches the hardware needs no refresh.

    Requires the Unity Editor to be running with the McpBridge plugin active.

    Returns:
        A post-refresh snapshot in the same shape as :func:`read_task_parameters_tool`, whose ``state.camera_mapping``
        list reflects the re-detected monitor geometry.
    """
    return _unity_relay(tool="refresh_monitors")


@mcp.tool()
def read_console_tool(
    level: Literal["all", "log", "warning", "error"] = "all",
    limit: int = 100,
    since_sequence: int | None = None,
) -> dict[str, Any]:
    """Returns the Unity Console entries the Editor has logged since it loaded the project.

    The bridge keeps the last 500 entries in memory, so this reports what the current Editor session logged rather than
    what the Console window currently displays, and a domain reload resets it. Each entry carries a monotonic
    ``sequence``, its ``type``, its ``message``, and its ``stack_trace``.

    Supplying ``since_sequence`` selects polling behavior, which returns the oldest unread matching entries and reports
    a ``next_sequence`` to pass back on the following call, so a backlog larger than ``limit`` arrives across successive
    calls rather than being skipped. Omitting it selects one-shot behavior, which returns the newest matching entries,
    which is what a diagnosis after a failure needs. Entries go missing through two channels. A ``dropped`` count that
    grew since the previous call means the 500-entry bound evicted entries, which this caller lost only if its own
    polling fell behind. A ``matched`` above ``count`` means ``limit`` truncated that many further matching entries out
    of this response. Requires the Unity Editor to be running with the McpBridge plugin active.

    Args:
        level: The severity group to return. ``error`` covers Unity's Error, Exception, and Assert types together.
        limit: The maximum number of entries to return. Must be at least 1. Defaults to 100.
        since_sequence: The sequence number to resume after, which must be non-negative, selecting polling behavior.
            Omit it for one-shot behavior.

    Returns:
        A response dict with ``entries``, ``count``, ``matched``, ``next_sequence``, ``dropped``, and ``capacity`` on
        success.
    """
    relay_arguments: dict[str, Any] = {"level": level, "limit": limit}
    if since_sequence is not None:
        relay_arguments["since_sequence"] = since_sequence
    return _unity_relay(tool="read_console", arguments=relay_arguments)


def _unity_relay(tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Relays a tool call to the Unity Editor's McpBridge HTTP listener.

    Args:
        tool: The tool name to invoke on the Unity side.
        arguments: The tool arguments dictionary. Defaults to an empty dict when omitted.

    Returns:
        The parsed JSON response from the Unity bridge, or an error dict if the bridge is unreachable, leaves the
        request unanswered within the timeout, or replies with a payload that is not a JSON object.
    """
    relay_arguments = arguments if arguments is not None else {}
    payload = json.dumps({"tool": tool, "args": relay_arguments}).encode("utf-8")
    request = urllib.request.Request(
        url=_UNITY_BRIDGE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(  # noqa: S310 - same localhost URL.
            url=request, timeout=_UNITY_BRIDGE_TIMEOUT
        ) as response:
            parsed = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError:
        message = (
            f"Unable to reach the Unity Editor at {_UNITY_BRIDGE_URL}. Ensure the Editor is open with the "
            f"McpBridge plugin loaded and listening on this address."
        )
        return error_response(message=message)
    # URLError wraps the failures of the request-sending half alone, so the connection-level failures of the
    # response-reading half arrive as its OSError siblings and are handled below it.
    except OSError:
        message = (
            f"Unable to complete the request to the Unity Editor at {_UNITY_BRIDGE_URL}. The Editor accepted the "
            f"connection but did not answer within {_UNITY_BRIDGE_TIMEOUT} seconds or dropped it mid-response, which "
            f"happens while its main thread is busy with a long operation such as a domain reload or an asset import. "
            f"Wait for the Editor to become responsive and retry."
        )
        return error_response(message=message)
    except json.JSONDecodeError, UnicodeDecodeError:
        message = "Unable to parse the Unity bridge response: the payload is not valid UTF-8 encoded JSON."
        return error_response(message=message)

    # The bridge contract guarantees a JSON object, but verify the shape so the typed return holds.
    if not isinstance(parsed, dict):
        message = "Unable to parse the Unity bridge response: the payload is a valid JSON value but not an object."
        return error_response(message=message)
    return parsed
