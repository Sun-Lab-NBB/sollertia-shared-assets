"""Provides MCP tools for managing Sollertia platform configuration assets."""

from __future__ import annotations

import math
import shutil
import struct
from typing import TYPE_CHECKING, Any, Literal
from decimal import ROUND_HALF_UP, Context, Decimal, InvalidOperation
from pathlib import Path
import contextlib

from ..enums import (
    ReadAssets,
    SessionTypes,
    CredentialsTypes,
    AcquisitionSystems,
)
from ..registries import (
    DESCRIPTOR_REGISTRY,
    READ_ASSET_REGISTRY,
    SYSTEM_SESSION_TYPES,
    CREDENTIALS_FILE_REGISTRY,
    EXPERIMENT_CONFIGURATION_REGISTRY,
)
from ..credentials import get_credentials, set_credentials
from .mcp_instance import (
    mcp,
    read_yaml,
    serialize,
    ok_response,
    safe_iterdir,
    error_response,
    describe_dataclass,
    write_yaml_validated,
    resolve_root_directory,
    collect_field_dataclasses,
)
from ..configuration import (
    NAME_COMPONENT_PATTERN,
    CONFIGURATION_DIRECTORY,
    Cue,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
    get_data_root,
    set_data_root,
    get_working_directory,
    set_working_directory,
    get_task_templates_directory,
    set_task_templates_directory,
)
from ..data_hierarchy import ProjectData

if TYPE_CHECKING:
    from collections.abc import Sized

    from ataraxis_data_structures import YamlConfig

_TEMPLATE_SUFFIXES: tuple[str, str] = (".yaml", ".yml")
"""The filename suffixes that make a YAML file a task template. The Unity catalog preflight scans both suffixes and
the Editor's template picker offers both as its file filter, so both name a live catalog member."""

_SINGLE_PRECISION_DIGITS: Context = Context(prec=7, rounding=ROUND_HALF_UP)
"""The decimal context reproducing the seven-significant-digit reduction C# applies to a single-precision float before
it renders the value through a custom numeric format string."""

_LENGTH_LABEL_QUANTUM: Decimal = Decimal("0.01")
"""The quantum of the two-fraction-digit cue length label that Unity embeds in every generated cue asset filename."""


@mcp.tool()
def get_platform_environment_status_tool() -> dict[str, Any]:
    """Returns a health report for the Sollertia platform configuration components owned by this package.

    Combines working directory, data root, templates directory, and per-category credentials status into a single
    report. Only the working directory is required for ``slsa mcp`` to function. The task templates directory is needed
    when authoring task templates or experiment configurations, and by ``SessionData.create()`` when it caches the
    ``vr_configuration.yaml`` snapshot for an experiment session. Credentials are needed only by hosts that integrate
    with the corresponding external service (for example, Google credentials are used to read subject metadata from and
    write water-restriction logs to Google Sheets). ``overall_ok`` reflects the required components only. Optional
    components contribute ``configured`` and ``ok`` per-component but do not gate the aggregate. System configuration
    mount checks live with the acquisition runtime package, sollertia-experiment.

    Returns:
        A response dict with ``overall_ok`` (the aggregate health flag, computed from required components only) and
        ``components`` mapping each environment component name to a dict carrying ``required``, ``configured``, ``ok``,
        and either ``path`` (when configured) or ``error`` (when not).
    """
    report: dict[str, Any] = {}

    try:
        working_directory = get_working_directory()
        report["working_directory"] = {"required": True, "configured": True, "path": str(working_directory), "ok": True}
    except FileNotFoundError as exception:
        report["working_directory"] = {"required": True, "configured": False, "error": str(exception), "ok": False}

    try:
        data_root = get_data_root()
        report["data_root"] = {"required": False, "configured": True, "path": str(data_root), "ok": True}
    except FileNotFoundError as exception:
        report["data_root"] = {"required": False, "configured": False, "error": str(exception), "ok": False}

    try:
        templates_directory = get_task_templates_directory()
        report["task_templates_directory"] = {
            "required": False,
            "configured": True,
            "path": str(templates_directory),
            "ok": True,
        }
    except FileNotFoundError as exception:
        report["task_templates_directory"] = {
            "required": False,
            "configured": False,
            "error": str(exception),
            "ok": False,
        }

    for credentials_type in CredentialsTypes:
        component_name = f"{credentials_type.value}_credentials"
        try:
            credentials_path = get_credentials(credentials=credentials_type)
            report[component_name] = {
                "required": False,
                "configured": True,
                "path": str(credentials_path),
                "ok": True,
            }
        except FileNotFoundError as exception:
            report[component_name] = {
                "required": False,
                "configured": False,
                "error": str(exception),
                "ok": False,
            }

    overall_ok = all(component["ok"] for component in report.values() if component["required"])
    return ok_response(overall_ok=overall_ok, components=report)


@mcp.tool()
def read_working_directory_tool() -> dict[str, Any]:
    """Returns the configured Sollertia platform working directory path.

    Returns:
        A response dict with ``working_directory`` containing the path.
    """
    try:
        path = get_working_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    return ok_response(working_directory=str(path))


@mcp.tool()
def set_working_directory_tool(directory: str) -> dict[str, Any]:
    """Sets the local Sollertia platform working directory.

    Args:
        directory: The absolute path to use as the working directory.

    Returns:
        A response dict with ``working_directory`` containing the configured path.
    """
    try:
        path = Path(directory)
        set_working_directory(path=path)
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(working_directory=str(path))


@mcp.tool()
def read_data_root_tool() -> dict[str, Any]:
    """Returns the configured Sollertia platform data root path.

    Returns:
        A response dict with ``data_root`` containing the path.
    """
    try:
        path = get_data_root()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    return ok_response(data_root=str(path))


@mcp.tool()
def set_data_root_tool(directory: str) -> dict[str, Any]:
    """Sets the local Sollertia platform data root.

    Args:
        directory: The absolute path to use as the data root.

    Returns:
        A response dict with ``data_root`` containing the configured path.
    """
    try:
        path = Path(directory)
        set_data_root(path=path)
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(data_root=str(path))


@mcp.tool()
def create_project_tool(project_name: str, root_directory: str | None = None) -> dict[str, Any]:
    """Creates the on-disk directory structure for a new project under a data root.

    Materializes the project hierarchy so the project becomes visible to directory-based discovery and ready to
    hold experiment configurations. When ``root_directory`` is omitted, the project is created under the
    configured Sollertia platform data root.

    Args:
        project_name: The name of the project to create, used as the project directory name.
        root_directory: The absolute path to the data root under which to create the project. When None, the
            configured platform data root is used.

    Returns:
        A response dict with ``project_name``, ``project_path``, and ``configuration_directory`` containing the
        created project's resolved paths. Returns the error envelope (``success`` false and ``error``) when the
        project directories cannot be created, for example because a plain file already occupies the project path or
        the data root is not writable.
    """
    if root_directory is None:
        try:
            root_directory = str(get_data_root())
        except FileNotFoundError as exception:
            return error_response(message=str(exception))

    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error
    if root is None:
        message = f"Unable to resolve the data root from {root_directory}."
        return error_response(message=message)

    # mkdir(exist_ok=True) still raises when a non-directory occupies the path, and any unwritable root surfaces the
    # same way, so the OSError family is converted into the error envelope every other tool in this module returns.
    try:
        project = ProjectData(root=root, project_name=project_name).create()
    except OSError as exception:
        message = f"Unable to create the project '{project_name}' under {root}: {exception}"
        return error_response(message=message)
    return ok_response(
        project_name=project_name,
        project_path=str(project.path),
        configuration_directory=str(project.configuration_directory),
    )


@mcp.tool()
def delete_project_tool(
    project_name: str,
    root_directory: str | None = None,
    confirm_deletion: Literal["yes", "no"] | None = None,
) -> dict[str, Any]:
    """Irreversibly removes an entire project directory tree together with every asset stored inside it.

    The removal covers the project directory itself, every animal and session directory beneath it, and every
    experiment configuration in the project's configuration directory. When ``root_directory`` is omitted, the
    project is resolved under the configured Sollertia platform data root.

    Important:
        The removal is irreversible and takes every file stored under the project with it. When ``confirm_deletion`` is
        omitted, the tool returns an error instead of deleting anything. Agentic callers should warn the user about the
        consequences and ask whether to proceed, then retry with the chosen value. A ``yes`` value performs the
        deletion. A ``no`` value abandons it.

    Args:
        project_name: The name of the project to delete, used as the project directory name. The name must be a
            single path component containing only ASCII letters, digits, and underscores.
        root_directory: The absolute path to the data root under which the project is stored. When None, the
            configured platform data root is used.
        confirm_deletion: The policy applied to the deletion request. ``yes`` performs the deletion, ``no`` abandons
            it, and ``None`` returns an error so the caller can prompt the user.

    Returns:
        A response dict with ``project_name``, ``project_path``, ``deleted`` set to True, ``animal_count`` (the
        number of animal directories removed), and ``experiment_configuration_count`` (the number of experiment
        configurations removed). An abandoned request instead returns ``project_name`` with ``deleted`` set to False.
        Returns the error envelope (``success`` false and ``error``) when the deletion policy is unspecified, when
        the project name violates the name-component pattern, when the data root cannot be resolved, or when the
        project is missing, resolves outside the data root, or cannot be removed.
    """
    # ProjectData joins the name onto the root verbatim, so a name carrying a path separator would address an animal
    # or session subtree that the containment guard below still accepts, and the response would report the removal as
    # a project deletion with animal counts taken from the wrong directory level.
    if not NAME_COMPONENT_PATTERN.match(project_name):
        message = (
            f"Unable to delete the project '{project_name}'. The project name must be a single path component "
            f"containing only ASCII letters, digits, and underscores, because it is joined onto the data root as the "
            f"project directory name."
        )
        return error_response(message=message)

    if root_directory is None:
        try:
            root_directory = str(get_data_root())
        except FileNotFoundError as exception:
            return error_response(message=str(exception))

    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error
    if root is None:
        message = f"Unable to resolve the data root from {root_directory}."
        return error_response(message=message)

    # Resolves the deletion policy before the project tree is inspected, so an unspecified policy cannot reach the
    # removal through a falsy default.
    if confirm_deletion is None:
        message = (
            f"Unable to delete the project '{project_name}' under {root} without an explicit deletion policy. The "
            f"deletion permanently removes the project directory with every animal, session, and experiment "
            f"configuration stored under it, and it cannot be undone. Specify confirm_deletion='yes' to perform the "
            f"deletion, or confirm_deletion='no' to abandon it. Ask the user which behavior they prefer before "
            f"retrying."
        )
        return error_response(message=message)
    if confirm_deletion == "no":
        return ok_response(project_name=project_name, deleted=False)

    project = ProjectData(root=root, project_name=project_name)
    if not project.exists():
        message = f"Unable to delete the project '{project_name}'. No project directory exists at {project.path}."
        return error_response(message=message)

    # resolve_root_directory validates the root alone, so an empty or '..'-bearing project name would otherwise
    # resolve to the data root itself or to a directory outside it.
    resolved_project_path = project.path.resolve()
    resolved_root = root.resolve()
    if resolved_project_path == resolved_root or not resolved_project_path.is_relative_to(resolved_root):
        message = (
            f"Unable to delete the project '{project_name}'. The project must resolve to a directory nested under "
            f"the data root {resolved_root}, but it resolves to {resolved_project_path}."
        )
        return error_response(message=message)

    # Inventories the tree before it is removed, so the response records what the deletion cost.
    animal_count = len(
        [
            child
            for child in safe_iterdir(directory=project.path)
            if child.is_dir() and child.name != CONFIGURATION_DIRECTORY
        ]
    )
    experiment_configuration_count = len(project.experiment_configs())

    try:
        shutil.rmtree(path=project.path)
    except OSError as exception:
        message = f"Unable to delete the project '{project_name}' at {project.path}: {exception}"
        return error_response(message=message)
    return ok_response(
        project_name=project_name,
        project_path=str(project.path),
        deleted=True,
        animal_count=animal_count,
        experiment_configuration_count=experiment_configuration_count,
    )


@mcp.tool()
def read_credentials_tool(credentials: str) -> dict[str, Any]:
    """Returns the path to the requested credentials file stored in the platform credentials directory.

    Use ``list_supported_credentials_tool`` to enumerate valid ``credentials`` values.

    Args:
        credentials: The ``CredentialsTypes`` value identifying the credentials category to resolve.

    Returns:
        A response dict with ``credentials`` (the echoed credentials category) and ``credentials_path``
        containing the path to the credentials file.
    """
    try:
        path = get_credentials(credentials=credentials)
    except (FileNotFoundError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(credentials=credentials, credentials_path=str(path))


@mcp.tool()
def set_credentials_tool(credentials: str, file_path: str) -> dict[str, Any]:
    """Copies the source credentials file into the platform credentials directory under its canonical name.

    The copy replaces any previously configured credentials file for the same category. Use
    ``list_supported_credentials_tool`` to enumerate valid ``credentials`` values.

    Args:
        credentials: The ``CredentialsTypes`` value identifying the credentials category to configure.
        file_path: The absolute path to the source credentials file to copy.

    Returns:
        A response dict with ``credentials`` (the echoed credentials category) and ``credentials_path``
        containing the path to the configured credentials file.
    """
    try:
        set_credentials(credentials=credentials, path=Path(file_path))
        path = get_credentials(credentials=credentials)
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(credentials=credentials, credentials_path=str(path))


@mcp.tool()
def read_task_templates_directory_tool() -> dict[str, Any]:
    """Returns the configured path to the sollertia-virtual-reality task templates directory.

    Returns:
        A response dict with ``task_templates_directory`` containing the path.
    """
    try:
        path = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    return ok_response(task_templates_directory=str(path))


@mcp.tool()
def set_task_templates_directory_tool(directory: str) -> dict[str, Any]:
    """Sets the path to the sollertia-virtual-reality task templates directory.

    Args:
        directory: The absolute path to the task templates directory.

    Returns:
        A response dict with ``task_templates_directory`` containing the configured path.
    """
    try:
        path = Path(directory)
        set_task_templates_directory(path=path)
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(task_templates_directory=str(path))


@mcp.tool()
def discover_templates_tool() -> dict[str, Any]:
    """Lists all task templates in the configured templates directory.

    Returns:
        A response dict with ``templates`` (a list of per-template summary dicts), ``total_templates``,
        and ``templates_directory`` (the resolved templates directory path). Each summary dict carries
        ``name`` (the template filename stem), ``path`` (the absolute YAML path), and on a successful
        load also ``cue_count``, ``trial_count``, and ``cue_offset_cm``. Templates that fail to load
        instead carry an ``error`` field describing the failure.
    """
    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))

    templates: list[dict[str, Any]] = []
    for template_file in sorted(templates_directory.glob("*.yaml")):
        entry: dict[str, Any] = {
            "name": template_file.stem,
            "path": str(template_file),
        }
        try:
            template = TaskTemplate.from_yaml(file_path=template_file)
        except Exception as exception:
            entry["error"] = f"Failed to load: {exception}"
        else:
            entry["cue_count"] = len(template.cues)
            entry["trial_count"] = len(template.trial_structures)
            entry["cue_offset_cm"] = template.vr_environment.cue_offset_cm
        templates.append(entry)

    return ok_response(
        templates=templates,
        total_templates=len(templates),
        templates_directory=str(templates_directory),
    )


@mcp.tool()
def read_template_tool(file_path: str) -> dict[str, Any]:
    """Loads a TaskTemplate YAML from either the live templates directory or a per-session frozen snapshot.

    Notes:
        TaskTemplates live in three places. The **live** template at ``<templates-directory>/<name>.yaml`` is the
        authoring surface managed via ``write_template_tool`` under the directory configured by
        ``set_task_templates_directory_tool``, and is shared across projects. ``discover_templates_tool`` returns the
        absolute paths of every live template. The per-session **frozen snapshot** at
        ``<session>/raw_data/vr_configuration.yaml`` is the immutable copy cached by ``SessionData.create()`` at
        acquisition time and records the exact template active when the session was acquired. The per-session
        **forged-dataset copy** at ``<dataset_root>/<animal>/<session>/vr_configuration.yaml`` is the same snapshot
        carried into a forged dataset by the sollertia-forgery pipeline, and is located via
        ``inspect_datasets_tool``. This tool reads any of the three. The caller chooses by passing the corresponding
        absolute path.

    Args:
        file_path: Absolute path to the template YAML file. Pass a path under the configured templates directory
            to read a live template, or a per-session ``raw_data/vr_configuration.yaml`` path to read the frozen
            session snapshot.

    Returns:
        A response dict with ``data`` containing the full TaskTemplate payload and the resolved ``file_path``.
    """
    return read_yaml(file_path=Path(file_path), validator_cls=TaskTemplate)


@mcp.tool()
def write_template_tool(
    file_path: str,
    template_payload: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates or replaces a live TaskTemplate YAML in the templates directory.

    The ``template_payload`` must match the TaskTemplate schema (use ``describe_template_schema_tool`` to
    inspect the required structure). The payload is validated against ``TaskTemplate.__post_init__`` before
    being persisted.

    Notes:
        This tool targets the **live** authoring surface, TaskTemplate YAMLs under the configured templates directory.
        Per-session frozen snapshots at ``<session>/raw_data/vr_configuration.yaml`` are immutable records of the
        template active at acquisition time and are produced exclusively by ``SessionData.create()``. Do not point this
        tool at a session's ``vr_configuration.yaml``. If a snapshot is corrupted or out of sync, repair the live
        template and re-acquire, or restore the snapshot from a backup.

        The destination filename stem is checked against ``NAME_COMPONENT_PATTERN`` before anything is written.
        ``ConfigLoader.cs`` applies the same pattern to the stem when Unity loads the template, and the stem also
        becomes the ``TemplateName`` half of every generated ``TemplateName-TrialName`` segment asset. Rejecting it
        here means a template this tool writes cannot be one the Editor later refuses to load.

        A cue identity, which is the cue name paired with its length, must also carry one texture across the whole
        templates catalog. Unity keys the generated cue prefab on that identity and reuses the prefab already on disk,
        so a sibling template declaring the identity with another texture makes both tasks render a texture they do
        not declare. This tool applies the same check the Unity generator applies, and skips it when the host has no
        templates directory configured or the destination lies outside that directory.

    Args:
        file_path: Absolute path to the destination template YAML file under the directory configured via
            ``set_task_templates_directory_tool``. The filename stem must contain only ASCII letters, digits, and
            underscores.
        template_payload: The complete TaskTemplate payload as a JSON-friendly dict.
        overwrite: Determines whether to overwrite an existing template file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated template payload). Returns the error envelope
        (``success`` false and ``error``) when the filename stem violates the name-component pattern. The same
        envelope reports a cue identity that carries a different texture in a sibling template, naming every
        contributing template stem.
    """
    template_path = Path(file_path)
    if not NAME_COMPONENT_PATTERN.match(template_path.stem):
        message = (
            f"Unable to write the task template to {template_path}. The template filename stem "
            f"'{template_path.stem}' must contain only ASCII letters, digits, and underscores, because "
            f"ConfigLoader.cs applies the same pattern when Unity loads the template and the stem is embedded in "
            f"every generated segment asset filename."
        )
        return error_response(message=message)

    # Unity keys every generated cue prefab on the cue identity alone and reuses the prefab already on disk, so a
    # texture that collides with a sibling template corrupts both tasks at generation time. The scan is skipped on a
    # host that has no templates directory configured, and for a destination outside that directory.
    templates_directory = _resolve_templates_catalog(template_path=template_path)
    if templates_directory is not None:
        conflicts = _detect_cue_texture_conflicts(
            templates_directory=templates_directory,
            template_path=template_path,
            candidate_cues=_extract_payload_cues(template_payload=template_payload),
        )
        if conflicts:
            message = (
                f"Unable to write the task template to {template_path}. Each cue identity must declare one texture "
                f"across the templates catalog at {templates_directory}, but the identities below declare more than "
                f"one: {' | '.join(conflicts)}."
            )
            return error_response(message=message)

    return write_yaml_validated(
        file_path=template_path,
        payload=template_payload,
        validator_cls=TaskTemplate,
        overwrite=overwrite,
    )


@mcp.tool()
def validate_template_tool(file_path: str) -> dict[str, Any]:
    """Loads and validates a TaskTemplate against its schema and cross-reference constraints.

    Notes:
        Accepts live templates under the configured templates directory, per-session frozen snapshots at
        ``<session>/raw_data/vr_configuration.yaml``, and the forged-dataset copies at
        ``<dataset_root>/<animal>/<session>/vr_configuration.yaml``. The validation logic is identical in every case.
        The schema and cross-reference constraints belong to ``TaskTemplate``, not to a particular storage location.
        The template filename stem is not part of that schema, so this tool does not apply the name-component pattern
        that ``write_template_tool`` enforces at authoring time.

        A template that lives in the live catalog is additionally checked against its siblings for cue identities
        declaring more than one texture, which is the conflict that aborts Unity task generation. A snapshot and a
        forged-dataset copy sit outside the catalog, so they receive the schema verdict alone.

    Args:
        file_path: Absolute path to the template YAML file (live template or session snapshot).

    Returns:
        A response dict with ``file_path``, ``valid``, and either ``summary`` (carrying ``cue_count``,
        ``trial_count``, and ``cue_offset_cm``) or ``issues`` (a list of validation error messages, carrying either
        the schema failure or one entry per cross-template cue-texture conflict). When the file does not exist, the
        tool instead returns the error envelope (``success`` false and ``error``) rather than a ``valid`` verdict.
    """
    template_path = Path(file_path)
    if not template_path.exists():
        message = f"Unable to validate the task template at {template_path}: the file does not exist."
        return error_response(message=message)
    try:
        template = TaskTemplate.from_yaml(file_path=template_path)
    except Exception as exception:
        return ok_response(valid=False, issues=[str(exception)], file_path=str(template_path))

    # A per-session snapshot and a forged-dataset copy both live outside the live catalog, and their stem is always
    # vr_configuration, so the cross-template scan runs for a catalog member alone.
    templates_directory = _resolve_templates_catalog(template_path=template_path)
    if templates_directory is not None:
        conflicts = _detect_cue_texture_conflicts(
            templates_directory=templates_directory,
            template_path=template_path,
            candidate_cues=[(cue.name, cue.length_cm, cue.texture) for cue in template.cues],
        )
        if conflicts:
            issues = [f"Cross-template cue-texture conflict. {conflict}" for conflict in conflicts]
            return ok_response(valid=False, issues=issues, file_path=str(template_path))

    summary = {
        "cue_count": len(template.cues),
        "trial_count": len(template.trial_structures),
        "cue_offset_cm": template.vr_environment.cue_offset_cm,
    }
    return ok_response(valid=True, file_path=str(template_path), summary=summary)


@mcp.tool()
def delete_template_tool(file_path: str) -> dict[str, Any]:
    """Removes a live TaskTemplate YAML from the configured templates directory.

    Notes:
        The removal takes the live YAML alone. The Unity artifacts generated from the template, which are the scene,
        the task prefab, and the segment prefabs, survive it, so retiring a task end to end means calling
        ``delete_task_tool`` first and this tool second.

        The path is resolved and then required to name a template file nested under the configured templates
        directory, which keeps the per-session frozen snapshot at ``<session>/raw_data/vr_configuration.yaml`` out of
        reach. That snapshot is an immutable record of the template active when the session was acquired, and
        ``read_template_tool`` and ``validate_template_tool`` accept it precisely because they only read it. A
        directory, and a file carrying a suffix other than ``.yaml`` or ``.yml``, are refused as well, so the removal
        reaches catalog members alone.

    Args:
        file_path: Absolute path to the live template YAML file under the directory configured via
            ``set_task_templates_directory_tool``.

    Returns:
        A response dict with ``file_path`` (the resolved path of the removed template) and ``deleted`` set to True.
        Returns the error envelope (``success`` false and ``error``) when the templates directory is unconfigured,
        when the resolved path is the templates directory itself or lies outside it, when the path carries another
        suffix, when no file exists at the path, or when the removal fails.
    """
    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))

    # Path.is_relative_to compares path components without normalizing them, so a caller path bearing '..' would
    # otherwise satisfy the guard while the kernel resolves the unlink onto a file outside the catalog.
    template_path = Path(file_path).resolve()
    resolved_templates_directory = templates_directory.resolve()
    if template_path == resolved_templates_directory or not template_path.is_relative_to(resolved_templates_directory):
        message = (
            f"Unable to delete the task template at {template_path}. The path must name a live template nested under "
            f"the configured templates directory {resolved_templates_directory}, because a per-session "
            f"vr_configuration.yaml snapshot is an immutable acquisition record."
        )
        return error_response(message=message)
    if template_path.suffix not in _TEMPLATE_SUFFIXES:
        message = (
            f"Unable to delete the task template at {template_path}. The path must carry one of the task template "
            f"suffixes {', '.join(_TEMPLATE_SUFFIXES)}, but got '{template_path.suffix}'."
        )
        return error_response(message=message)
    if not template_path.is_file():
        message = f"Unable to delete the task template at {template_path}: no file exists at the path."
        return error_response(message=message)
    try:
        template_path.unlink()
    except OSError as exception:
        message = f"Unable to delete the task template at {template_path}: {exception}"
        return error_response(message=message)
    return ok_response(file_path=str(template_path), deleted=True)


@mcp.tool()
def describe_template_schema_tool() -> dict[str, Any]:
    """Returns the schema for TaskTemplate, including nested Cue, TrialStructure, and VREnvironment.

    Use the returned schema to construct a valid payload for ``write_template_tool``.

    Returns:
        A response dict with ``schema`` containing the TaskTemplate schema. The ``schema`` carries a
        ``nested_classes`` sub-mapping of each nested dataclass name (Cue, TrialStructure, VREnvironment) to its
        individual schema.
    """
    schema = describe_dataclass(dataclass_type=TaskTemplate)
    schema["nested_classes"] = {
        "Cue": describe_dataclass(dataclass_type=Cue),
        "TrialStructure": describe_dataclass(dataclass_type=TrialStructure),
        "VREnvironment": describe_dataclass(dataclass_type=VREnvironment),
    }
    return ok_response(schema=schema)


@mcp.tool()
def discover_experiments_tool(
    root_directory: str,
    project: str | None = None,
) -> dict[str, Any]:
    """Discovers all experiment configuration YAML files under the data root.

    Walks each project's ``configuration`` directory for experiment YAML files and returns a flat list of
    experiment summaries.

    Args:
        root_directory: The absolute path to the root data directory to scan.
        project: When provided, restricts the search to a single project.

    Returns:
        A response dict with ``experiments`` (a list of per-experiment summary dicts) and ``total_experiments``. Each
        summary dict carries ``project`` (the project directory name), ``experiment`` (the experiment configuration
        filename stem), and ``path`` (the absolute YAML path).
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    project_paths: list[Path]
    if project is not None:
        project_path = root.joinpath(project)  # type: ignore[union-attr]
        if not project_path.is_dir():
            message = f"Unable to discover experiments. The project '{project}' was not found at {project_path}."
            return error_response(message=message)
        project_paths = [project_path]
    else:
        project_paths = [child for child in safe_iterdir(directory=root) if child.is_dir()]  # type: ignore[arg-type]

    experiments: list[dict[str, Any]] = []
    for project_path in sorted(project_paths, key=lambda candidate: candidate.name):
        configuration_directory = project_path.joinpath(CONFIGURATION_DIRECTORY)
        if not configuration_directory.is_dir():
            continue
        experiments.extend(
            {
                "project": project_path.name,
                "experiment": configuration_file.stem,
                "path": str(configuration_file),
            }
            for configuration_file in sorted(configuration_directory.glob("*.yaml"))
        )

    return ok_response(experiments=experiments, total_experiments=len(experiments))


@mcp.tool()
def read_experiment_configuration_tool(file_path: str, acquisition_system: str) -> dict[str, Any]:
    """Loads an experiment configuration YAML, parsing it with the dataclass that matches ``acquisition_system``.

    The same experiment configuration schema is used for both the authored per-project source config and the
    frozen per-session snapshot copied at acquisition time. This tool reads both. Pass the per-project path
    (``<root>/<project>/configuration/<experiment>.yaml``) to inspect the authored source. Pass the per-session
    snapshot path (``<session>/raw_data/experiment_configuration.yaml``) to inspect the immutable record of what
    was active when the session was acquired. Use ``list_supported_acquisition_systems_tool`` to enumerate valid
    ``acquisition_system`` values.

    Args:
        file_path: Absolute path to the experiment configuration YAML file. Accepts either the per-project
            source path or the per-session frozen snapshot path.
        acquisition_system: The ``AcquisitionSystems`` value identifying which experiment-configuration dataclass
            to parse the file with.

    Returns:
        On success, a response dict with ``data`` (the full experiment configuration payload), ``acquisition_system``,
        and ``file_path``. On failure, a dict with ``success`` false and ``error`` (the ``acquisition_system`` key is
        present only on success).
    """
    resolved = _resolve_experiment_configuration_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    response = read_yaml(file_path=Path(file_path), validator_cls=resolved)
    if response.get("success"):
        response["acquisition_system"] = acquisition_system
    return response


@mcp.tool()
def write_experiment_configuration_tool(
    file_path: str,
    acquisition_system: str,
    configuration_payload: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates or replaces an experiment configuration YAML, validated against ``acquisition_system``.

    The ``configuration_payload`` must match the experiment-configuration schema for ``acquisition_system``. Use
    ``describe_experiment_configuration_schema_tool`` to inspect the required structure, and
    ``list_supported_acquisition_systems_tool`` to enumerate valid ``acquisition_system`` values.

    Args:
        file_path: Absolute path to the destination experiment configuration YAML file. Canonical per-project
            location is ``<root>/<project>/configuration/<experiment>.yaml``. Any missing parent directories,
            including the project and its ``configuration`` subdirectory, are created as needed. Use
            ``create_project_tool`` to mint a project explicitly.
        acquisition_system: The ``AcquisitionSystems`` value identifying which experiment-configuration dataclass
            to validate against.
        configuration_payload: The complete experiment configuration payload.
        overwrite: Determines whether to overwrite an existing experiment configuration file.

    Returns:
        On success, a response dict with ``file_path``, ``data`` (the validated configuration payload), and
        ``acquisition_system``. On failure (validation error, or an existing file when ``overwrite`` is False), a
        dict with ``success`` false and ``error`` (the ``acquisition_system`` key is present only on success).
    """
    resolved = _resolve_experiment_configuration_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    response = write_yaml_validated(
        file_path=Path(file_path),
        payload=configuration_payload,
        validator_cls=resolved,
        overwrite=overwrite,
    )
    if response.get("success"):
        response["acquisition_system"] = acquisition_system
    return response


@mcp.tool()
def create_experiment_from_vr_template_tool(
    file_path: str,
    acquisition_system: str,
    template_path: str,
    state_count: int = 1,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates an experiment configuration for ``acquisition_system`` from a Unity VR task template.

    Loads the task template at ``template_path`` and builds the experiment configuration through the acquisition
    system's experiment-configuration class, which maps the template's trial structures to runtime trials and seeds
    ``state_count`` default-valued runtime states. Then writes the result to ``file_path``. The embedded Unity scene
    name is inferred from the template filename, mirroring how sollertia-virtual-reality derives the scene name at task
    creation. Use ``list_supported_acquisition_systems_tool`` to enumerate valid ``acquisition_system`` values.

    The generated configuration's trial parameters take the acquisition system's built-in defaults. To author a
    configuration with custom trial parameters, inspect the schema with
    ``describe_experiment_configuration_schema_tool`` and write the full payload with
    ``write_experiment_configuration_tool``.

    Args:
        file_path: Absolute path to the destination experiment configuration YAML file. Canonical per-project
            location is ``<root>/<project>/configuration/<experiment>.yaml``. Any missing parent directories,
            including the project and its ``configuration`` subdirectory, are created as needed. Use
            ``create_project_tool`` to mint a project explicitly.
        acquisition_system: The ``AcquisitionSystems`` value whose experiment configuration is built from the
            template.
        template_path: Absolute path to the Unity VR task template YAML to instantiate. The embedded Unity scene
            name is inferred from this file's stem (the filename without the ``.yaml`` extension).
        state_count: Number of default-valued runtime states to generate.
        overwrite: Determines whether to overwrite an existing experiment configuration file.

    Returns:
        A response dict with ``file_path``, ``acquisition_system``, ``template_path``, and ``data`` (the generated
        experiment configuration payload).
    """
    try:
        acquisition_enum = AcquisitionSystems(acquisition_system)
    except ValueError:
        valid = ", ".join(member.value for member in AcquisitionSystems)
        message = (
            f"Unable to create an experiment configuration. The acquisition_system '{acquisition_system}' is not a "
            f"member of AcquisitionSystems. Valid values: {valid}."
        )
        return error_response(message=message)

    experiment_configuration_class = EXPERIMENT_CONFIGURATION_REGISTRY[acquisition_enum]

    destination = Path(file_path)
    if destination.exists() and not overwrite:
        message = (
            f"Unable to write the experiment configuration to {destination}: a file already exists at this path. "
            f"Pass overwrite=True to replace it."
        )
        return error_response(message=message)

    template_file = Path(template_path)
    if not template_file.exists():
        message = f"Unable to load the task template from {template_file}: the file does not exist."
        return error_response(message=message)

    resolved_scene_name = template_file.stem

    try:
        task_template = TaskTemplate.from_yaml(file_path=template_file)
        # The import-time contract check guarantees every registered configuration provides this builder.
        build_from_template: Any = getattr(experiment_configuration_class, "from_task_template", None)
        experiment_configuration = build_from_template(
            template=task_template,
            unity_scene_name=resolved_scene_name,
            state_count=state_count,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        experiment_configuration.to_yaml(file_path=destination)
    except Exception as exception:
        message = (
            f"Unable to create the experiment configuration for '{acquisition_system}' from the task template at "
            f"{template_file}: {exception}"
        )
        return error_response(message=message)

    return ok_response(
        file_path=str(destination),
        acquisition_system=acquisition_system,
        template_path=str(template_file),
        data=serialize(value=experiment_configuration),
    )


@mcp.tool()
def validate_experiment_configuration_tool(file_path: str, acquisition_system: str) -> dict[str, Any]:
    """Loads and validates an experiment configuration YAML against the ``acquisition_system`` schema.

    Use ``list_supported_acquisition_systems_tool`` to enumerate valid ``acquisition_system`` values.

    Args:
        file_path: Absolute path to the experiment configuration YAML file.
        acquisition_system: The ``AcquisitionSystems`` value identifying which experiment-configuration dataclass
            to validate against.

    Returns:
        A response dict with ``file_path``, ``acquisition_system``, ``valid``, and either ``summary`` (carrying
        ``trial_count``, ``state_count``, and ``unity_scene_name``) or ``issues`` (a list of validation errors).
        When the file does not exist, the tool instead returns the error envelope (``success`` false and ``error``)
        rather than a ``valid`` verdict.
    """
    resolved = _resolve_experiment_configuration_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    configuration_path = Path(file_path)
    if not configuration_path.exists():
        message = f"Unable to validate the experiment configuration at {configuration_path}: the file does not exist."
        return error_response(message=message)
    try:
        experiment_configuration = resolved.from_yaml(file_path=configuration_path)
    except Exception as exception:
        return ok_response(
            valid=False,
            issues=[str(exception)],
            file_path=str(configuration_path),
            acquisition_system=acquisition_system,
        )
    # Every experiment configuration declares these contract fields, so the summary always carries them.
    trial_structures: Sized = getattr(experiment_configuration, "trial_structures", ())
    experiment_states: Sized = getattr(experiment_configuration, "experiment_states", ())
    summary: dict[str, Any] = {
        "trial_count": len(trial_structures),
        "state_count": len(experiment_states),
        "unity_scene_name": getattr(experiment_configuration, "unity_scene_name", ""),
    }
    return ok_response(
        valid=True,
        file_path=str(configuration_path),
        acquisition_system=acquisition_system,
        summary=summary,
    )


@mcp.tool()
def delete_experiment_configuration_tool(file_path: str, root_directory: str | None = None) -> dict[str, Any]:
    """Removes a per-project experiment configuration YAML from a project's configuration directory.

    Notes:
        The removal never parses the document, so it needs no ``acquisition_system`` argument. The path is resolved
        and then required to name a ``.yaml`` file directly inside a project's ``configuration`` directory nested
        under the data root the request targets. That confinement keeps the per-session frozen snapshot at
        ``<session>/raw_data/experiment_configuration.yaml`` out of reach, and it keeps every data root other than
        the one the request names, such as an archival mirror on mounted server storage, out of reach as well. The
        snapshot is an immutable record of the configuration active when the session was acquired, and
        ``read_experiment_configuration_tool`` accepts it precisely because it only reads it.

        Acting on a data root other than the configured platform data root takes an explicit ``root_directory``,
        which mirrors ``delete_project_tool`` and records the targeted root in the response.

    Args:
        file_path: Absolute path to the per-project experiment configuration YAML at
            ``<root>/<project>/configuration/<experiment>.yaml``.
        root_directory: The absolute path to the data root under which the configuration is stored. When None, the
            configured platform data root is used.

    Returns:
        A response dict with ``file_path`` (the resolved path of the removed configuration), ``root_directory`` (the
        resolved data root the removal was confined to), and ``deleted`` set to True. Returns the error envelope
        (``success`` false and ``error``) when the data root cannot be resolved, when the resolved path lies outside
        that root, when the parent directory is not named ``configuration``, when the path carries another suffix,
        when no file exists at the path, or when the removal fails.
    """
    if root_directory is None:
        try:
            root_directory = str(get_data_root())
        except FileNotFoundError as exception:
            return error_response(message=str(exception))

    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error
    if root is None:
        message = f"Unable to resolve the data root from {root_directory}."
        return error_response(message=message)

    # A parent directory named 'configuration' exists on every reachable mount and inside every source checkout, so
    # the name alone identifies no location. Both sides are resolved before the containment test, because
    # Path.is_relative_to compares path components without normalizing the '..' entries away.
    configuration_path = Path(file_path).resolve()
    resolved_root = root.resolve()
    if not configuration_path.is_relative_to(resolved_root):
        message = (
            f"Unable to delete the experiment configuration at {configuration_path}. The path must resolve to a file "
            f"stored under the data root {resolved_root}. Pass the root_directory of the data root that holds the "
            f"configuration to act on another root."
        )
        return error_response(message=message)
    if configuration_path.parent.name != CONFIGURATION_DIRECTORY:
        message = (
            f"Unable to delete the experiment configuration at {configuration_path}. The path must name a file "
            f"directly inside a project's '{CONFIGURATION_DIRECTORY}' directory, but its parent directory is "
            f"'{configuration_path.parent.name}'."
        )
        return error_response(message=message)
    if configuration_path.suffix != ".yaml":
        message = (
            f"Unable to delete the experiment configuration at {configuration_path}. The path must carry the "
            f"'.yaml' suffix, but got '{configuration_path.suffix}'."
        )
        return error_response(message=message)
    if not configuration_path.is_file():
        message = f"Unable to delete the experiment configuration at {configuration_path}: no file exists at the path."
        return error_response(message=message)
    try:
        configuration_path.unlink()
    except OSError as exception:
        message = f"Unable to delete the experiment configuration at {configuration_path}: {exception}"
        return error_response(message=message)
    return ok_response(file_path=str(configuration_path), root_directory=str(resolved_root), deleted=True)


@mcp.tool()
def describe_experiment_configuration_schema_tool(acquisition_system: str) -> dict[str, Any]:
    """Returns the schema for the experiment configuration of a given acquisition system.

    Every experiment configuration shares one contract: the ``experiment_states`` state machine, the
    ``trial_structures`` table, and the ``unity_scene_name`` of the corridor task. The concrete trial classes and any
    fields beyond the contract are system-specific, so the returned ``nested_classes`` are derived from the resolved
    configuration class. Use ``list_supported_acquisition_systems_tool`` to enumerate valid ``acquisition_system``
    values.

    Args:
        acquisition_system: The ``AcquisitionSystems`` value to describe.

    Returns:
        A response dict with ``acquisition_system`` (the resolved acquisition system) and ``schema`` (the experiment
        configuration schema). The ``schema`` carries a ``nested_classes`` sub-mapping of each nested dataclass name
        to its individual schema, derived from the resolved configuration class.
    """
    resolved = _resolve_experiment_configuration_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    schema = describe_dataclass(dataclass_type=resolved)
    schema["nested_classes"] = {
        name: describe_dataclass(dataclass_type=nested_class)
        for name, nested_class in collect_field_dataclasses(dataclass_type=resolved).items()
    }
    return ok_response(acquisition_system=acquisition_system, schema=schema)


@mcp.tool()
def list_supported_session_types_tool(acquisition_system: str | None = None) -> dict[str, Any]:
    """Enumerates the SessionTypes supported by the platform, optionally scoped to one acquisition system.

    When ``acquisition_system`` is provided, only the session types that system can run are returned (per
    ``SYSTEM_SESSION_TYPES``). When omitted, every platform session type is returned. Agents operating within a
    configured acquisition system should pass that system so the result reflects what the local host can actually run.
    Use ``list_supported_acquisition_systems_tool`` to enumerate valid ``acquisition_system`` values, and
    ``list_session_type_support_tool`` to retrieve the full system-to-session-type mapping at once.

    Args:
        acquisition_system: The ``AcquisitionSystems`` value to scope the result to, or None for every session type.

    Returns:
        A response dict with ``acquisition_system`` (the echoed filter, or None) and ``session_types`` (a list of
        dicts containing ``value``, ``name``, and ``descriptor_class`` for each session type). The descriptor
        filename is always ``session_descriptor.yaml`` regardless of session type and is therefore not returned.
    """
    if acquisition_system is not None:
        try:
            system = AcquisitionSystems(acquisition_system)
        except ValueError:
            valid = ", ".join(member.value for member in AcquisitionSystems)
            message = (
                f"Unable to list the supported session types. The acquisition_system '{acquisition_system}' is not a "
                f"member of AcquisitionSystems. Valid values: {valid}."
            )
            return error_response(message=message)
        supported = SYSTEM_SESSION_TYPES[system]
    else:
        supported = frozenset(SessionTypes)
    entries: list[dict[str, Any]] = [
        {
            "value": session_type.value,
            "name": session_type.name,
            "descriptor_class": DESCRIPTOR_REGISTRY[session_type].__name__,
        }
        for session_type in SessionTypes
        if session_type in supported
    ]
    return ok_response(acquisition_system=acquisition_system, session_types=entries)


@mcp.tool()
def list_session_type_support_tool() -> dict[str, Any]:
    """Returns the full mapping of acquisition systems to the session types each one can run.

    Use this to retrieve the entire system-to-session-type landscape in a single call. Use
    ``list_supported_session_types_tool`` with an ``acquisition_system`` argument when only one system's session types
    are needed.

    Returns:
        A response dict with ``session_type_support`` (a dict mapping each acquisition system value to the list of
        session type values it supports).
    """
    support: dict[str, list[str]] = {
        system.value: [
            session_type.value for session_type in SessionTypes if session_type in SYSTEM_SESSION_TYPES[system]
        ]
        for system in AcquisitionSystems
    }
    return ok_response(session_type_support=support)


@mcp.tool()
def list_supported_acquisition_systems_tool() -> dict[str, Any]:
    """Enumerates the AcquisitionSystems supported by the Sollertia platform.

    Returns:
        A response dict with ``acquisition_systems`` (a list of dicts containing ``value`` and ``name`` for each
        supported acquisition system).
    """
    entries: list[dict[str, Any]] = [{"value": member.value, "name": member.name} for member in AcquisitionSystems]
    return ok_response(acquisition_systems=entries)


@mcp.tool()
def list_supported_data_assets_tool() -> dict[str, Any]:
    """Enumerates the read-asset data formats supported by the Sollertia platform.

    Read assets are external records the platform reads and caches on disk as typed dataclasses. Use the returned
    ``value`` as the ``data_asset`` argument to ``read_data_asset_tool``, ``write_data_asset_tool``, and
    ``describe_data_asset_schema_tool``.

    Returns:
        A response dict with ``data_assets`` (a list of dicts containing ``value``, ``name``, and ``data_asset_class``
        for each supported read asset).
    """
    entries: list[dict[str, Any]] = [
        {
            "value": read_asset.value,
            "name": read_asset.name,
            "data_asset_class": READ_ASSET_REGISTRY[read_asset].__name__,
        }
        for read_asset in ReadAssets
    ]
    return ok_response(data_assets=entries)


@mcp.tool()
def list_supported_credentials_tool() -> dict[str, Any]:
    """Enumerates the credentials categories supported by the Sollertia platform.

    Use the returned ``value`` as the ``credentials`` argument to ``read_credentials_tool`` and
    ``set_credentials_tool``.

    Returns:
        A response dict with ``credentials`` (a list of dicts containing ``value``, ``name``, and ``file_name``
        for each supported credentials category). The ``file_name`` is the canonical filename under which the
        category's credentials file is stored inside the platform credentials directory.
    """
    entries: list[dict[str, Any]] = [
        {
            "value": member.value,
            "name": member.name,
            "file_name": CREDENTIALS_FILE_REGISTRY[member],
        }
        for member in CredentialsTypes
    ]
    return ok_response(credentials=entries)


@mcp.tool()
def list_supported_trial_types_tool(acquisition_system: str) -> dict[str, Any]:
    """Enumerates the trial classes supported by the ``acquisition_system``'s experiment configuration.

    Trial classes are derived from the system's experiment-configuration ``trial_structures`` field, so each system
    reports its own trial vocabulary. ``trial_structures`` is part of the shared experiment-configuration contract. The
    concrete trial classes vary per system. Use ``list_supported_acquisition_systems_tool`` to enumerate valid
    ``acquisition_system`` values.

    Args:
        acquisition_system: The ``AcquisitionSystems`` value whose trial vocabulary to enumerate.

    Returns:
        A response dict with ``acquisition_system`` and ``trial_types`` (a list of dicts containing ``class_name``
        and ``schema`` for each trial class the system's configuration declares).
    """
    resolved = _resolve_experiment_configuration_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    entries: list[dict[str, Any]] = [
        {"class_name": name, "schema": describe_dataclass(dataclass_type=trial_class)}
        for name, trial_class in collect_field_dataclasses(
            dataclass_type=resolved, field_name="trial_structures"
        ).items()
    ]
    return ok_response(acquisition_system=acquisition_system, trial_types=entries)


@mcp.tool()
def list_supported_trigger_types_tool() -> dict[str, Any]:
    """Enumerates the TriggerType values supported by trial structures.

    Returns:
        A response dict with ``trigger_types`` (a list of dicts containing ``value`` and ``name`` for each
        supported trigger type).
    """
    entries: list[dict[str, Any]] = [{"value": member.value, "name": member.name} for member in TriggerType]
    return ok_response(trigger_types=entries)


def _resolve_experiment_configuration_class(acquisition_system: str) -> type[YamlConfig] | dict[str, Any]:
    """Resolves an ``acquisition_system`` string to its registered experiment configuration dataclass.

    Validates the value against the ``AcquisitionSystems`` enum and then looks up the corresponding class in
    ``EXPERIMENT_CONFIGURATION_REGISTRY``. Returns an error response dict when the value is not a valid acquisition
    system or when no experiment configuration class has been registered for that system yet.

    Args:
        acquisition_system: The ``AcquisitionSystems`` value supplied by the caller.

    Returns:
        The resolved experiment configuration dataclass on success, or an error response dict on failure. Callers
        discriminate via ``isinstance(result, dict)``.
    """
    try:
        acquisition_enum = AcquisitionSystems(acquisition_system)
    except ValueError:
        valid = ", ".join(member.value for member in AcquisitionSystems)
        message = (
            f"Unable to resolve the experiment configuration class. The acquisition_system "
            f"'{acquisition_system}' is not a member of AcquisitionSystems. Valid values: {valid}."
        )
        return error_response(message=message)
    experiment_configuration_class = EXPERIMENT_CONFIGURATION_REGISTRY.get(acquisition_enum)
    if experiment_configuration_class is None:
        registered = ", ".join(member.value for member in EXPERIMENT_CONFIGURATION_REGISTRY)
        message = (
            f"Unable to resolve the experiment configuration class. No class is registered for "
            f"'{acquisition_system}'. Registered systems: {registered}."
        )
        return error_response(message=message)
    return experiment_configuration_class


def _resolve_templates_catalog(template_path: Path) -> Path | None:
    """Returns the configured task templates directory when the target template belongs to the live catalog.

    Both sides of the membership test are resolved, because the setter persists the configured directory in canonical
    form while the caller supplies the destination in any equivalent spelling. A symlinked project prefix and an
    un-normalized ``..`` component both name the directory the catalog occupies, and an unresolved comparison reads
    either spelling as a location outside the catalog.

    Args:
        template_path: The path to the template under authoring or validation.

    Returns:
        The configured task templates directory when the template resolves to a direct child of it. Returns None when
        the host has no templates directory configured, and when the template resolves elsewhere.
    """
    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError:
        return None
    if template_path.resolve().parent != templates_directory.resolve():
        return None
    return templates_directory


def _detect_cue_texture_conflicts(
    templates_directory: Path,
    template_path: Path,
    candidate_cues: list[tuple[str, float, str]],
) -> list[str]:
    """Detects the cue identities that carry more than one texture across the live templates catalog.

    Unity keys a generated cue prefab on the cue name together with its length label and reuses the prefab already on
    disk, so two templates declaring one identity with different textures each render the other's texture. This scan
    applies the identity rule the Unity preflight applies, which makes the authoring verdict match the later
    generation verdict. A sibling template that fails to parse contributes nothing and is skipped, because its
    declarations are unreadable while the authored template is still able to pass.

    Args:
        templates_directory: The configured task templates directory to scan.
        template_path: The path to the template under authoring, held out of the scan by its resolved path so the
            copy already on disk does not conflict with the incoming version.
        candidate_cues: The name, the length in centimeters, and the texture of each cue the authored template
            declares.

    Returns:
        A list of conflict descriptions, one per cue identity carrying more than one texture. Each names the identity
        together with every contributing template stem and the texture that stem declares. The list is empty when
        every identity carries a single texture.
    """
    resolved_template_path = template_path.resolve()
    catalog: list[tuple[str, list[tuple[str, float, str]]]] = [(template_path.stem, candidate_cues)]

    # The Unity preflight scans both YAML suffixes, so a .yml sibling is a catalog member whose cues take part in the
    # identity rule. write_yaml_validated stages its temporary file inside this directory under a leading dot, and
    # Path.glob matches a dotted name, so a staging artifact left behind by a killed write would otherwise enter the
    # scan as a phantom sibling declaring the previous contents of the file being authored.
    template_files = sorted(
        template_file
        for suffix in _TEMPLATE_SUFFIXES
        for template_file in templates_directory.glob(f"*{suffix}")
        if not template_file.name.startswith(".")
    )
    for template_file in template_files:
        if template_file.resolve() == resolved_template_path:
            continue
        sibling: TaskTemplate | None
        try:
            sibling = TaskTemplate.from_yaml(file_path=template_file)
        except Exception:
            sibling = None
        if sibling is not None:
            catalog.append((template_file.stem, [(cue.name, cue.length_cm, cue.texture) for cue in sibling.cues]))

    declarations: dict[str, list[tuple[str, str]]] = {}
    for stem, cues in catalog:
        for name, length_cm, texture in cues:
            length_label = _format_cue_length_label(length_cm=length_cm)
            declarations.setdefault(f"{name} at {length_label}cm", []).append((texture, stem))

    conflicts: list[str] = []
    for identity, entries in declarations.items():
        if len({texture for texture, _ in entries}) <= 1:
            continue
        details = ", ".join(f"{stem} -> '{texture}'" for texture, stem in entries)
        conflicts.append(f"Cue '{identity}': {details}")
    return conflicts


def _extract_payload_cues(template_payload: dict[str, Any]) -> list[tuple[str, float, str]]:
    """Reads the name, the length, and the texture of each cue declared in a raw task template payload.

    The payload reaches this helper before schema validation, so a cue entry whose fields are missing or carry an
    unexpected type is skipped and left for the validator to report.

    Args:
        template_payload: The task template payload as supplied by the caller.

    Returns:
        A list of name, length in centimeters, and texture triplets, one per readable cue entry.
    """
    raw_cues = template_payload.get("cues")
    if not isinstance(raw_cues, list):
        return []
    cues: list[tuple[str, float, str]] = []
    for raw_cue in raw_cues:
        if not isinstance(raw_cue, dict):
            continue
        name = raw_cue.get("name")
        length_cm = raw_cue.get("length_cm")
        texture = raw_cue.get("texture")
        if isinstance(name, str) and isinstance(length_cm, (int, float)) and isinstance(texture, str):
            cues.append((name, float(length_cm), texture))
    return cues


def _format_cue_length_label(length_cm: float) -> str:
    """Formats a cue length the way Unity formats it into the shared ``Cue_{name}_{label}cm`` asset filename.

    Unity holds the length in a single-precision ``float`` and renders it with ``ToString("0.##")`` under the
    invariant culture, which reduces the value to seven significant digits and rounds every tie away from zero at
    both the reduction and the two-fraction-digit rendering. Python rounds a double half to even, so the two labels
    disagree on every length whose rendered digits end in a tie, and the authoring verdict then contradicts the Unity
    generation verdict in both directions.

    Args:
        length_cm: The cue length in centimeters, as declared by the template.

    Returns:
        The label Unity embeds in the generated cue asset filename.
    """
    # A magnitude beyond the single-precision range becomes an infinity the moment Unity parses it, and the invariant
    # culture spells every non-finite value by name. The value reaches this helper before schema validation rejects
    # it, so a label is produced instead of an exception.
    try:
        single_precision: float = struct.unpack(">f", struct.pack(">f", length_cm))[0]
    except OverflowError:
        single_precision = math.copysign(math.inf, length_cm)
    if math.isnan(single_precision):
        return "NaN"
    if math.isinf(single_precision):
        return "Infinity" if single_precision > 0 else "-Infinity"

    # The exact single-precision value is reduced to seven significant digits first, which is what turns 123456.78
    # into 123456.8, and the two-fraction-digit quantization then applies to the reduced value alone. A magnitude
    # large enough for the quantization to exceed the decimal context precision already carries no fraction digits,
    # so the reduced value is the label for it.
    significant = _SINGLE_PRECISION_DIGITS.plus(Decimal(single_precision))
    with contextlib.suppress(InvalidOperation):
        significant = significant.quantize(_LENGTH_LABEL_QUANTUM, rounding=ROUND_HALF_UP)

    label = f"{significant:f}"
    # An integral label carries no separator, so stripping trailing zeros unconditionally would turn 20 into 2.
    if "." in label:
        label = label.rstrip("0").rstrip(".")
    return label
