"""Provides MCP tools for managing Sollertia platform configuration assets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

if TYPE_CHECKING:
    from collections.abc import Sized

    from ataraxis_data_structures import YamlConfig

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


@mcp.tool()
def get_platform_environment_status_tool() -> dict[str, Any]:
    """Returns a health report for the Sollertia platform configuration components owned by this package.

    Combines working directory, data root, templates directory, and per-category credentials status into a single
    report. Only the working directory is required for ``slsa mcp`` to function. The task templates directory is
    needed only when authoring task templates or experiment configurations. Credentials are needed only by hosts
    that integrate with the corresponding external service (for example, Google credentials are used to read
    subject metadata from and write water-restriction logs to Google Sheets). ``overall_ok`` reflects the required
    components only — optional components contribute ``configured`` and ``ok`` per-component but do not gate the
    aggregate. System configuration mount checks are not included here — those live with the acquisition runtime
    package (sl-experiment).

    Returns:
        A response dict with ``overall_ok`` (the aggregate health flag, computed from required components only)
        and ``components`` mapping each environment component name to a dict carrying ``required``,
        ``configured``, ``ok``, and either ``path`` (when configured) or ``error`` (when not).
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
        created project's resolved paths.
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
        return error_response(message=f"Unable to resolve the data root from {root_directory}.")

    project = ProjectData(root=root, project_name=project_name).create()
    return ok_response(
        project_name=project_name,
        project_path=str(project.path),
        configuration_directory=str(project.configuration_directory),
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
        TaskTemplates live in two places. The **live** template at ``<templates-directory>/<name>.yaml`` is the
        authoring surface managed via this skill and is shared across projects; ``discover_templates_tool`` returns
        the absolute paths of every live template. The per-session **frozen snapshot** at
        ``<session>/raw_data/vr_configuration.yaml`` is the immutable copy cached by ``SessionData.create()`` at
        acquisition time and records the exact template active when the session was acquired. This tool reads either
        — the caller chooses by passing the corresponding absolute path.

    Args:
        file_path: Absolute path to the template YAML file. Pass a path under the configured templates directory
            to read a live template, or a per-session ``raw_data/vr_configuration.yaml`` path to read the frozen
            session snapshot.

    Returns:
        A response dict with ``data`` containing the full TaskTemplate payload and the resolved
        ``file_path``.
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
        This tool targets the **live** authoring surface — TaskTemplate YAMLs under the configured templates
        directory. Per-session frozen snapshots at ``<session>/raw_data/vr_configuration.yaml`` are immutable
        records of the template active at acquisition time and are produced exclusively by ``SessionData.create()``.
        Do not point this tool at a session's ``vr_configuration.yaml``; if a snapshot is corrupted or out of sync,
        repair the live template and re-acquire, or restore the snapshot from a backup.

    Args:
        file_path: Absolute path to the destination template YAML file under the directory configured via
            ``set_task_templates_directory_tool``.
        template_payload: The complete TaskTemplate payload as a JSON-friendly dict.
        overwrite: Determines whether to overwrite an existing template file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated template payload).
    """
    return write_yaml_validated(
        file_path=Path(file_path),
        payload=template_payload,
        validator_cls=TaskTemplate,
        overwrite=overwrite,
    )


@mcp.tool()
def validate_template_tool(file_path: str) -> dict[str, Any]:
    """Loads and validates a TaskTemplate against its schema and cross-reference constraints.

    Notes:
        Accepts both live templates under the configured templates directory and per-session frozen snapshots at
        ``<session>/raw_data/vr_configuration.yaml``. The validation logic is identical in either case — the schema
        and cross-reference constraints belong to ``TaskTemplate``, not to a particular storage location.

    Args:
        file_path: Absolute path to the template YAML file (live template or session snapshot).

    Returns:
        A response dict with ``file_path``, ``valid``, and either ``summary`` (carrying ``cue_count``,
        ``trial_count``, and ``cue_offset_cm``) or ``issues`` (a list of validation error messages).
    """
    template_path = Path(file_path)
    if not template_path.exists():
        message = f"Unable to validate the task template at {template_path}: the file does not exist."
        return error_response(message=message)
    try:
        template = TaskTemplate.from_yaml(file_path=template_path)
    except Exception as exception:
        return ok_response(valid=False, issues=[str(exception)], file_path=str(template_path))
    summary = {
        "cue_count": len(template.cues),
        "trial_count": len(template.trial_structures),
        "cue_offset_cm": template.vr_environment.cue_offset_cm,
    }
    return ok_response(valid=True, file_path=str(template_path), summary=summary)


@mcp.tool()
def describe_template_schema_tool() -> dict[str, Any]:
    """Returns the schema for TaskTemplate, including nested Cue, TrialStructure, and VREnvironment.

    Use the returned schema to construct a valid payload for ``write_template_tool``.

    Returns:
        A response dict with ``schema`` containing the TaskTemplate schema. The ``schema`` carries a
        ``nested_classes`` sub-mapping of each nested dataclass name (Cue, TrialStructure, VREnvironment) to its
        individual schema.
    """
    schema = describe_dataclass(cls=TaskTemplate)
    schema["nested_classes"] = {
        "Cue": describe_dataclass(cls=Cue),
        "TrialStructure": describe_dataclass(cls=TrialStructure),
        "VREnvironment": describe_dataclass(cls=VREnvironment),
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
        A response dict with ``experiments`` (a list of per-experiment summary dicts) and
        ``total_experiments``. Each summary dict carries ``project`` (the project directory name),
        ``experiment`` (the experiment configuration filename stem), and ``path`` (the absolute YAML
        path).
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
        On success, a response dict with ``data`` (the full experiment configuration payload),
        ``acquisition_system``, and ``file_path``. On failure, a dict with ``success`` false and ``error`` (the
        ``acquisition_system`` key is present only on success).
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
            location is ``<root>/<project>/configuration/<experiment>.yaml``. Project directories are created
            implicitly by the sollertia-experiment session-creation flow; this tool does not create them.
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
            location is ``<root>/<project>/configuration/<experiment>.yaml``. Project directories are created
            implicitly by the sollertia-experiment session-creation flow; this tool does not create them.
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

    config_class = EXPERIMENT_CONFIGURATION_REGISTRY[acquisition_enum]

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
        build_from_template: Any = getattr(config_class, "from_task_template", None)
        experiment_configuration = build_from_template(
            template=task_template,
            unity_scene_name=resolved_scene_name,
            state_count=state_count,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        experiment_configuration.to_yaml(file_path=destination)
    except Exception as exception:
        return error_response(message=f"Failed to create experiment configuration: {exception}")

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
        A response dict with ``file_path``, ``acquisition_system``, ``valid``, and either ``summary`` (carrying the
        configuration's trial, state, and scene fields when present) or ``issues`` (a list of validation errors).
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
    schema = describe_dataclass(cls=resolved)
    schema["nested_classes"] = {
        name: describe_dataclass(cls=nested_class)
        for name, nested_class in collect_field_dataclasses(cls=resolved).items()
    }
    return ok_response(acquisition_system=acquisition_system, schema=schema)


@mcp.tool()
def list_supported_session_types_tool(acquisition_system: str | None = None) -> dict[str, Any]:
    """Enumerates the SessionTypes supported by the platform, optionally scoped to one acquisition system.

    When ``acquisition_system`` is provided, only the session types that system can run are returned (per
    ``SYSTEM_SESSION_TYPES``); when omitted, every platform session type is returned. Agents operating within a
    configured acquisition system should pass that system so the result reflects what the local host can actually
    run. Use ``list_supported_acquisition_systems_tool`` to enumerate valid ``acquisition_system`` values, and
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

    Use this to retrieve the entire system-to-session-type landscape in a single call; use
    ``list_supported_session_types_tool`` with an ``acquisition_system`` argument when only one system's session
    types are needed.

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

    Read assets are external records the platform reads and caches on disk as typed dataclasses. Use the
    returned ``value`` as the ``data_asset`` argument to ``read_data_asset_tool``,
    ``write_data_asset_tool``, and ``describe_data_asset_schema_tool``.

    Returns:
        A response dict with ``data_assets`` (a list of dicts containing ``value``, ``name``, and
        ``data_asset_class`` for each supported read asset).
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
    reports its own trial vocabulary. ``trial_structures`` is part of the shared experiment-configuration contract;
    the concrete trial classes vary per system. Use ``list_supported_acquisition_systems_tool`` to enumerate valid
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
        {"class_name": name, "schema": describe_dataclass(cls=trial_class)}
        for name, trial_class in collect_field_dataclasses(cls=resolved, field_name="trial_structures").items()
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

    Validates the value against the ``AcquisitionSystems`` enum and then looks up the corresponding
    class in ``EXPERIMENT_CONFIGURATION_REGISTRY``. Returns an error response dict when the value is
    not a valid acquisition system or when no experiment configuration class has been registered for
    that system yet.

    Args:
        acquisition_system: The ``AcquisitionSystems`` value supplied by the caller.

    Returns:
        The resolved experiment configuration dataclass on success, or an error response dict on
        failure. Callers discriminate via ``isinstance(result, dict)``.
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
