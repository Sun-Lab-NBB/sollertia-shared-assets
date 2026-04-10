"""Provides MCP tools for managing Sollertia platform configuration assets.

Covers experiment configurations, task templates, system and server configuration, platform setup,
schema introspection, and enumeration tools. All tools register on the shared ``mcp`` instance from
``mcp_instance``.
"""

from __future__ import annotations

import uuid
from typing import Any
from pathlib import Path

from ataraxis_base_utilities import ensure_directory_exists

from .mcp_instance import (
    CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY,
    DATASET_MARKER_FILENAME,
    SESSION_MARKER_FILENAME,
    INCOMPLETE_SESSION_MARKER,
    mcp,
    read_yaml,
    serialize,
    ok_response,
    safe_iterdir,
    error_response,
    describe_dataclass,
    write_yaml_validated,
    resolve_root_directory,
    session_root_from_marker,
)
from ..data_classes import SessionData, SessionTypes
from ..configuration import (
    Cue,
    Segment,
    BaseTrial,
    TriggerType,
    GasPuffTrial,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
    ExperimentState,
    MesoscopeCameras,
    WaterRewardTrial,
    AcquisitionSystems,
    MesoscopeFileSystem,
    ServerConfiguration,
    MesoscopeGoogleSheets,
    MesoscopeExternalAssets,
    MesoscopeMicroControllers,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory as _set_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    set_google_credentials_path as _set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory as _set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
    populate_default_experiment_states,
)

_SERVER_CONFIG_FILENAME: str = "server_configuration.yaml"
"""Canonical filename for the ServerConfiguration YAML stored in the working directory."""

_TRIAL_CLASSES: dict[str, type[BaseTrial]] = {
    "WaterRewardTrial": WaterRewardTrial,
    "GasPuffTrial": GasPuffTrial,
}
"""Maps trial class names to their dataclass implementations."""


@mcp.tool()
def discover_experiments_tool(
    root_directory: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    """Discovers all experiment configuration YAML files under the data root.

    Walks each project's ``configuration`` directory for experiment YAML files and returns a flat list of
    experiment summaries.

    Args:
        root_directory: Override for the root data directory.
        project: When provided, restricts the search to a single project.

    Returns:
        A response dict with ``experiments`` (list of experiment summary dicts) and ``total_experiments``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    # Restricts the search to a single project when specified, otherwise scans all project directories.
    project_paths: list[Path]
    if project is not None:
        project_path = root.joinpath(project)  # type: ignore[union-attr]
        if not project_path.is_dir():
            return error_response(message=f"Project '{project}' not found at {project_path}")
        project_paths = [project_path]
    else:
        project_paths = [child for child in safe_iterdir(directory=root) if child.is_dir()]  # type: ignore[arg-type]

    # Collects experiment summaries from each project's configuration directory.
    experiments: list[dict[str, Any]] = []
    for project_path in sorted(project_paths, key=lambda candidate: candidate.name):
        configuration_dir = project_path.joinpath(CONFIGURATION_DIR)
        if not configuration_dir.is_dir():
            continue
        experiments.extend(
            {
                "project": project_path.name,
                "experiment": configuration_file.stem,
                "path": str(configuration_file),
            }
            for configuration_file in sorted(configuration_dir.glob("*.yaml"))
        )

    return ok_response(experiments=experiments, total_experiments=len(experiments))


@mcp.tool()
def discover_templates_tool() -> dict[str, Any]:
    """Lists all task templates in the configured templates directory.

    Returns:
        A response dict with ``templates`` (list of template summary dicts including cue, segment, and trial
        counts) and ``total_templates``.
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
            entry["segment_count"] = len(template.segments)
            entry["trial_count"] = len(template.trial_structures)
            entry["cue_offset_cm"] = template.cue_offset_cm
        templates.append(entry)

    return ok_response(
        templates=templates,
        total_templates=len(templates),
        templates_directory=str(templates_directory),
    )


@mcp.tool()
def read_experiment_configuration_tool(project: str, experiment: str) -> dict[str, Any]:
    """Loads a MesoscopeExperimentConfiguration YAML for a project's experiment.

    Args:
        project: The name of the project containing the experiment.
        experiment: The name of the experiment configuration (without the ``.yaml`` extension).

    Returns:
        A response dict with ``data`` containing the full experiment configuration payload.
    """
    root, error = resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    configuration_path = root.joinpath(project, CONFIGURATION_DIR, f"{experiment}.yaml")  # type: ignore[union-attr]
    return read_yaml(file_path=configuration_path, validator_cls=MesoscopeExperimentConfiguration)


@mcp.tool()
def read_template_tool(template_name: str) -> dict[str, Any]:
    """Loads a TaskTemplate YAML by name from the configured templates directory.

    Args:
        template_name: The name of the template (without the ``.yaml`` extension).

    Returns:
        A response dict with ``data`` containing the full TaskTemplate payload and the resolved ``file_path``.
    """
    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    template_path = templates_directory.joinpath(f"{template_name}.yaml")
    return read_yaml(file_path=template_path, validator_cls=TaskTemplate)


@mcp.tool()
def read_system_configuration_tool() -> dict[str, Any]:
    """Loads the active MesoscopeSystemConfiguration from the working directory.

    Returns:
        A response dict with ``data`` containing the full system configuration payload.
    """
    try:
        instance = get_system_configuration_data()
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(data=serialize(value=instance))


@mcp.tool()
def read_server_configuration_tool() -> dict[str, Any]:
    """Loads the ServerConfiguration from the working directory with the password masked.

    Returns:
        A response dict with ``data`` containing the server configuration payload. The password field is
        replaced with the literal string ``"<masked>"`` for security.
    """
    try:
        instance = get_server_configuration()
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    serialized = serialize(value=instance)
    if isinstance(serialized, dict) and "password" in serialized:
        serialized["password"] = "<masked>"  # noqa: S105 - literal masking placeholder, not a real password.
    return ok_response(data=serialized)


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
def read_google_credentials_tool() -> dict[str, Any]:
    """Returns the configured path to the Google service account credentials JSON file.

    Returns:
        A response dict with ``google_credentials_path`` containing the path.
    """
    try:
        path = get_google_credentials_path()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    return ok_response(google_credentials_path=str(path))


@mcp.tool()
def read_task_templates_directory_tool() -> dict[str, Any]:
    """Returns the configured path to the sollertia-unity-tasks templates directory.

    Returns:
        A response dict with ``task_templates_directory`` containing the path.
    """
    try:
        path = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    return ok_response(task_templates_directory=str(path))


@mcp.tool()
def write_template_tool(
    template_name: str,
    template_payload: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates or replaces a TaskTemplate YAML in the configured templates directory.

    The ``template_payload`` must match the TaskTemplate schema (use ``describe_template_schema_tool`` to
    inspect the required structure). The payload is validated against ``TaskTemplate.__post_init__`` before
    being persisted.

    Args:
        template_name: The destination filename without the ``.yaml`` extension.
        template_payload: The complete TaskTemplate payload as a JSON-friendly dict.
        overwrite: Determines whether to overwrite an existing template file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated template payload).
    """
    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    file_path = templates_directory.joinpath(f"{template_name}.yaml")
    return write_yaml_validated(
        file_path=file_path,
        payload=template_payload,
        validator_cls=TaskTemplate,
        overwrite=overwrite,
    )


@mcp.tool()
def write_experiment_configuration_tool(
    project: str,
    experiment: str,
    configuration_payload: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates or replaces an experiment configuration YAML for a project.

    The ``configuration_payload`` must match the MesoscopeExperimentConfiguration schema. Use
    ``describe_experiment_configuration_schema_tool`` to inspect the required structure.

    Args:
        project: The name of the project that owns the experiment.
        experiment: The destination filename (without the ``.yaml`` extension).
        configuration_payload: The complete experiment configuration payload.
        overwrite: Determines whether to overwrite an existing experiment configuration file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated configuration payload).
    """
    root, error = resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.is_dir():
        return error_response(
            message=f"Project '{project}' does not exist at {project_path}. Use create_project_tool first."
        )
    file_path = project_path.joinpath(CONFIGURATION_DIR, f"{experiment}.yaml")
    return write_yaml_validated(
        file_path=file_path,
        payload=configuration_payload,
        validator_cls=MesoscopeExperimentConfiguration,
        overwrite=overwrite,
    )


@mcp.tool()
def write_system_configuration_tool(
    system: str,
    configuration_payload: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates or replaces a system configuration YAML in the working directory.

    Args:
        system: The acquisition system name (e.g., ``"mesoscope"``). Determines the destination filename.
        configuration_payload: The complete system configuration payload.
        overwrite: Determines whether to overwrite an existing system configuration file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated configuration payload).
    """
    try:
        AcquisitionSystems(system)
    except ValueError:
        valid = ", ".join(member.value for member in AcquisitionSystems)
        return error_response(message=f"Invalid acquisition system '{system}'. Valid values: {valid}")

    try:
        working_directory = get_working_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))

    file_path = working_directory.joinpath(CONFIGURATION_DIR, f"{system}_system_configuration.yaml")
    return write_yaml_validated(
        file_path=file_path,
        payload=configuration_payload,
        validator_cls=MesoscopeSystemConfiguration,
        overwrite=overwrite,
        use_save_method=True,
    )


@mcp.tool()
def write_server_configuration_tool(
    configuration_payload: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates or replaces the ServerConfiguration YAML in the working directory.

    Args:
        configuration_payload: The complete ServerConfiguration payload (must include ``username``, ``password``,
            ``host``, ``storage_root``, ``working_root``, and ``shared_directory_name``).
        overwrite: Determines whether to overwrite an existing server configuration file.

    Returns:
        A response dict with ``file_path`` and ``data`` containing the validated payload with the password masked.
    """
    try:
        working_directory = get_working_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    file_path = working_directory.joinpath(CONFIGURATION_DIR, _SERVER_CONFIG_FILENAME)
    response = write_yaml_validated(
        file_path=file_path,
        payload=configuration_payload,
        validator_cls=ServerConfiguration,
        overwrite=overwrite,
    )
    if response.get("success") and isinstance(response.get("data"), dict):
        response["data"]["password"] = "<masked>"  # noqa: S105 - literal masking placeholder, not a real password.
    return response


@mcp.tool()
def create_project_tool(project: str) -> dict[str, Any]:
    """Creates a new project directory and its ``configuration`` subdirectory under the system root.

    Args:
        project: The name of the project to create.

    Returns:
        A response dict with ``project``, ``project_path``, and ``already_exists`` (True when the project
        directory was already present and no changes were made).
    """
    root, error = resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    project_path = root.joinpath(project)  # type: ignore[union-attr]
    configuration_path = project_path.joinpath(CONFIGURATION_DIR)
    if project_path.exists():
        return ok_response(project=project, project_path=str(project_path), already_exists=True)
    try:
        ensure_directory_exists(path=configuration_path)
    except (FileNotFoundError, OSError) as exception:
        return error_response(message=f"Failed to create project directory: {exception}")
    return ok_response(project=project, project_path=str(project_path), already_exists=False)


@mcp.tool()
def create_experiment_config_tool(
    project: str,
    experiment: str,
    template: str,
    state_count: int = 1,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates an experiment configuration from a task template using sensible defaults.

    Loads the named template, builds an experiment configuration via ``create_experiment_configuration``,
    populates the requested number of default-valued runtime states, and writes the result. Use
    ``write_experiment_configuration_tool`` instead when full control over the payload is required.

    Args:
        project: The name of the project for which to create the experiment.
        experiment: The destination experiment name (without the ``.yaml`` extension).
        template: The name of the task template to use (without the ``.yaml`` extension).
        state_count: Number of default-valued runtime states to generate.
        overwrite: Determines whether to overwrite an existing experiment configuration file.

    Returns:
        A response dict with ``project``, ``experiment``, ``template``, ``file_path``, and ``data`` (the
        generated experiment configuration payload).
    """
    root, error = resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.exists():
        return error_response(
            message=f"Project '{project}' does not exist. Use create_project_tool to create it first."
        )

    file_path = project_path.joinpath(CONFIGURATION_DIR, f"{experiment}.yaml")
    if file_path.exists() and not overwrite:
        return error_response(message=f"Experiment '{experiment}' already exists in project '{project}'.")

    # Resolves the template file and verifies it exists in the templates directory.
    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    template_path = templates_directory.joinpath(f"{template}.yaml")
    if not template_path.exists():
        available = sorted(template_file.stem for template_file in templates_directory.glob("*.yaml"))
        return error_response(
            message=(
                f"Template '{template}' not found. Available templates: {', '.join(available) if available else 'none'}"
            ),
        )

    # Loads the template, generates the experiment configuration, and populates default runtime states.
    try:
        task_template = TaskTemplate.from_yaml(file_path=template_path)
        system_configuration = get_system_configuration_data()
        experiment_configuration = create_experiment_configuration(
            template=task_template,
            system=system_configuration.name,
            unity_scene_name=template,
        )
        populate_default_experiment_states(
            experiment_configuration=experiment_configuration,
            state_count=state_count,
        )
        experiment_configuration.to_yaml(file_path=file_path)
    except Exception as exception:
        return error_response(message=f"Failed to create experiment configuration: {exception}")

    return ok_response(
        project=project,
        experiment=experiment,
        template=template,
        file_path=str(file_path),
        data=serialize(value=experiment_configuration),
    )


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
        _set_working_directory(path=path)
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(working_directory=str(path))


@mcp.tool()
def set_google_credentials_tool(credentials_path: str) -> dict[str, Any]:
    """Sets the path to the Google service account credentials JSON file.

    Args:
        credentials_path: The absolute path to the credentials JSON file.

    Returns:
        A response dict with ``google_credentials_path`` containing the configured path.
    """
    try:
        path = Path(credentials_path)
        _set_google_credentials_path(path=path)
    except (FileNotFoundError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(google_credentials_path=str(path))


@mcp.tool()
def set_task_templates_directory_tool(directory: str) -> dict[str, Any]:
    """Sets the path to the sollertia-unity-tasks task templates directory.

    Args:
        directory: The absolute path to the templates' directory.

    Returns:
        A response dict with ``task_templates_directory`` containing the configured path.
    """
    try:
        path = Path(directory)
        _set_task_templates_directory(path=path)
    except (FileNotFoundError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(task_templates_directory=str(path))


@mcp.tool()
def describe_template_schema_tool() -> dict[str, Any]:
    """Returns the schema for TaskTemplate, including nested Cue, Segment, TrialStructure, and VREnvironment.

    Use the returned schema to construct a valid payload for ``write_template_tool``.

    Returns:
        A response dict with ``schema`` containing the TaskTemplate schema and ``nested_classes`` mapping
        each nested dataclass name to its individual schema.
    """
    schema = describe_dataclass(cls=TaskTemplate)
    schema["nested_classes"] = {
        "Cue": describe_dataclass(cls=Cue),
        "Segment": describe_dataclass(cls=Segment),
        "TrialStructure": describe_dataclass(cls=TrialStructure),
        "VREnvironment": describe_dataclass(cls=VREnvironment),
    }
    return ok_response(schema=schema)


@mcp.tool()
def describe_experiment_configuration_schema_tool(acquisition_system: str = "mesoscope") -> dict[str, Any]:
    """Returns the schema for the experiment configuration of a given acquisition system.

    Args:
        acquisition_system: The AcquisitionSystems value to describe. Defaults to ``"mesoscope"``.

    Returns:
        A response dict with ``schema`` containing the experiment configuration schema and ``nested_classes``
        mapping each nested dataclass name (including the supported trial classes) to its individual schema.
    """
    try:
        AcquisitionSystems(acquisition_system)
    except ValueError:
        valid = ", ".join(member.value for member in AcquisitionSystems)
        return error_response(message=f"Invalid acquisition_system '{acquisition_system}'. Valid values: {valid}")
    schema = describe_dataclass(cls=MesoscopeExperimentConfiguration)
    schema["nested_classes"] = {
        "Cue": describe_dataclass(cls=Cue),
        "Segment": describe_dataclass(cls=Segment),
        "VREnvironment": describe_dataclass(cls=VREnvironment),
        "ExperimentState": describe_dataclass(cls=ExperimentState),
        "WaterRewardTrial": describe_dataclass(cls=WaterRewardTrial),
        "GasPuffTrial": describe_dataclass(cls=GasPuffTrial),
    }
    return ok_response(schema=schema)


@mcp.tool()
def describe_system_configuration_schema_tool(acquisition_system: str = "mesoscope") -> dict[str, Any]:
    """Returns the schema for the system configuration of a given acquisition system.

    Args:
        acquisition_system: The AcquisitionSystems value to describe. Defaults to ``"mesoscope"``.

    Returns:
        A response dict with ``schema`` containing the system configuration schema and ``nested_classes``
        mapping each nested dataclass name to its individual schema.
    """
    try:
        AcquisitionSystems(acquisition_system)
    except ValueError:
        valid = ", ".join(member.value for member in AcquisitionSystems)
        return error_response(message=f"Invalid acquisition_system '{acquisition_system}'. Valid values: {valid}")
    schema = describe_dataclass(cls=MesoscopeSystemConfiguration)
    schema["nested_classes"] = {
        "MesoscopeFileSystem": describe_dataclass(cls=MesoscopeFileSystem),
        "MesoscopeGoogleSheets": describe_dataclass(cls=MesoscopeGoogleSheets),
        "MesoscopeCameras": describe_dataclass(cls=MesoscopeCameras),
        "MesoscopeMicroControllers": describe_dataclass(cls=MesoscopeMicroControllers),
        "MesoscopeExternalAssets": describe_dataclass(cls=MesoscopeExternalAssets),
    }
    return ok_response(schema=schema)


@mcp.tool()
def validate_template_tool(template_name: str) -> dict[str, Any]:
    """Loads and validates a TaskTemplate against its schema and cross-reference constraints.

    Args:
        template_name: The name of the template (without the ``.yaml`` extension).

    Returns:
        A response dict with ``valid`` and either ``summary`` (cue, segment, and trial counts plus the
        cue offset) or ``issues`` (a list of validation error messages).
    """
    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError as exception:
        return error_response(message=str(exception))
    template_path = templates_directory.joinpath(f"{template_name}.yaml")
    if not template_path.exists():
        return error_response(message=f"Template '{template_name}' not found at {template_path}")
    try:
        template = TaskTemplate.from_yaml(file_path=template_path)
    except Exception as exception:
        return ok_response(valid=False, issues=[str(exception)], file_path=str(template_path))
    summary = {
        "cue_count": len(template.cues),
        "segment_count": len(template.segments),
        "trial_count": len(template.trial_structures),
        "cue_offset_cm": template.cue_offset_cm,
    }
    return ok_response(valid=True, file_path=str(template_path), summary=summary)


@mcp.tool()
def validate_experiment_configuration_tool(project: str, experiment: str) -> dict[str, Any]:
    """Loads and validates an experiment configuration YAML for a project.

    Args:
        project: The name of the project containing the experiment.
        experiment: The name of the experiment configuration (without the ``.yaml`` extension).

    Returns:
        A response dict with ``valid`` and either ``summary`` or ``issues``.
    """
    root, error = resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    configuration_path = root.joinpath(project, CONFIGURATION_DIR, f"{experiment}.yaml")  # type: ignore[union-attr]
    if not configuration_path.exists():
        return error_response(message=f"Experiment '{experiment}' not found at {configuration_path}")
    try:
        experiment_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=configuration_path)
    except Exception as exception:
        return ok_response(valid=False, issues=[str(exception)], file_path=str(configuration_path))
    summary = {
        "cue_count": len(experiment_configuration.cues),
        "segment_count": len(experiment_configuration.segments),
        "trial_count": len(experiment_configuration.trial_structures),
        "state_count": len(experiment_configuration.experiment_states),
        "unity_scene_name": experiment_configuration.unity_scene_name,
    }
    return ok_response(valid=True, file_path=str(configuration_path), summary=summary)


@mcp.tool()
def validate_system_configuration_tool() -> dict[str, Any]:
    """Loads and validates the active system configuration plus all configured filesystem paths.

    Returns:
        A response dict with ``valid``, ``issues``, ``system_name``, and ``paths`` (the per-path mount
        status report).
    """
    try:
        system_configuration = get_system_configuration_data()
    except (FileNotFoundError, OSError, ValueError) as exception:
        return ok_response(valid=False, issues=[str(exception)])

    # Probes each configured filesystem path for existence and writability.
    filesystem = system_configuration.filesystem
    paths_report: dict[str, dict[str, Any]] = {
        "root_directory": _check_path(path=filesystem.root_directory),
        "server_directory": _check_path(path=filesystem.server_directory),
        "nas_directory": _check_path(path=filesystem.nas_directory),
    }
    if hasattr(filesystem, "mesoscope_directory"):
        paths_report["mesoscope_directory"] = _check_path(path=filesystem.mesoscope_directory)

    # Aggregates issues from paths that are configured but not accessible.
    issues = [
        f"{name}: {report.get('error', 'not OK')}"
        for name, report in paths_report.items()
        if report.get("configured", True) and not report.get("ok", False)
    ]
    return ok_response(
        valid=not issues,
        issues=issues,
        system_name=system_configuration.name,
        paths=paths_report,
    )


@mcp.tool()
def get_project_overview_tool(project: str) -> dict[str, Any]:
    """Returns aggregate counts (animals, sessions by type, experiments, datasets) for a project.

    Args:
        project: The name of the project.

    Returns:
        A response dict with ``project``, ``project_path``, ``animal_count``, ``animals``, ``sessions_by_type``,
        ``total_sessions``, ``incomplete_sessions``, ``experiment_count``, and ``dataset_count``.
    """
    root, error = resolve_root_directory(root_directory=None)
    if error is not None:
        return error

    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.is_dir():
        return error_response(message=f"Project '{project}' not found at {project_path}")

    # Enumerates animal subdirectories, excluding the configuration directory.
    animals = [
        child.name
        for child in safe_iterdir(directory=project_path)
        if child.is_dir() and child.name != CONFIGURATION_DIR
    ]

    # Tallies sessions by type and counts incomplete sessions across the project tree.
    sessions_by_type: dict[str, int] = {member.value: 0 for member in SessionTypes}
    incomplete_count = 0
    for marker in project_path.rglob(SESSION_MARKER_FILENAME):
        try:
            instance = SessionData.load(session_path=session_root_from_marker(marker=marker))
        except Exception:  # noqa: S112 - skip unparseable sessions during best-effort overview.
            continue
        session_type_value = serialize(value=instance.session_type)
        if isinstance(session_type_value, str):
            sessions_by_type[session_type_value] = sessions_by_type.get(session_type_value, 0) + 1
        if instance.raw_data_path.joinpath(INCOMPLETE_SESSION_MARKER).exists():
            incomplete_count += 1

    # Counts experiment configurations and datasets under the project.
    configuration_dir = project_path.joinpath(CONFIGURATION_DIR)
    experiment_count = len(list(configuration_dir.glob("*.yaml"))) if configuration_dir.is_dir() else 0
    dataset_count = len(list(project_path.rglob(DATASET_MARKER_FILENAME)))

    return ok_response(
        project=project,
        project_path=str(project_path),
        animal_count=len(animals),
        animals=sorted(animals),
        sessions_by_type=sessions_by_type,
        total_sessions=sum(sessions_by_type.values()),
        incomplete_sessions=incomplete_count,
        experiment_count=experiment_count,
        dataset_count=dataset_count,
    )


@mcp.tool()
def get_acquisition_environment_status_tool() -> dict[str, Any]:
    """Returns a comprehensive health report for the local acquisition environment.

    Combines working directory, templates directory, server configuration, Google credentials, and system
    configuration mount checks into a single report.

    Returns:
        A response dict with ``overall_ok`` (the aggregate health flag) and ``components`` mapping each
        environment component name to its individual status report.
    """
    report: dict[str, Any] = {}

    # Checks each platform component in turn: working directory, templates, credentials, server, system.
    try:
        working_directory = get_working_directory()
        report["working_directory"] = {"configured": True, "path": str(working_directory), "ok": True}
    except FileNotFoundError as exception:
        report["working_directory"] = {"configured": False, "error": str(exception), "ok": False}

    try:
        templates_directory = get_task_templates_directory()
        report["task_templates_directory"] = {
            "configured": True,
            "path": str(templates_directory),
            "ok": True,
        }
    except FileNotFoundError as exception:
        report["task_templates_directory"] = {"configured": False, "error": str(exception), "ok": False}

    try:
        google_credentials = get_google_credentials_path()
        report["google_credentials"] = {"configured": True, "path": str(google_credentials), "ok": True}
    except FileNotFoundError as exception:
        report["google_credentials"] = {"configured": False, "error": str(exception), "ok": False}

    try:
        server_configuration = get_server_configuration()
        report["server_configuration"] = {
            "configured": True,
            "host": server_configuration.host,
            "username": server_configuration.username,
            "ok": True,
        }
    except (FileNotFoundError, ValueError) as exception:
        report["server_configuration"] = {"configured": False, "error": str(exception), "ok": False}

    try:
        system_configuration = get_system_configuration_data()
        filesystem = system_configuration.filesystem
        paths_report: dict[str, dict[str, Any]] = {
            "root_directory": _check_path(path=filesystem.root_directory),
            "server_directory": _check_path(path=filesystem.server_directory),
            "nas_directory": _check_path(path=filesystem.nas_directory),
        }
        if hasattr(filesystem, "mesoscope_directory"):
            paths_report["mesoscope_directory"] = _check_path(path=filesystem.mesoscope_directory)
        report["system_configuration"] = {
            "configured": True,
            "system_name": system_configuration.name,
            "paths": paths_report,
            "ok": all(path.get("ok", False) for path in paths_report.values()),
        }
    except (FileNotFoundError, OSError, ValueError) as exception:
        report["system_configuration"] = {"configured": False, "error": str(exception), "ok": False}

    overall_ok = all(component.get("ok", False) for component in report.values())
    return ok_response(overall_ok=overall_ok, components=report)


@mcp.tool()
def check_mount_accessibility_tool(path: str) -> dict[str, Any]:
    """Verifies that a filesystem path is accessible and writable.

    Args:
        path: The filesystem path to verify.

    Returns:
        A response dict with ``path``, ``exists``, ``is_mount``, ``writable``, ``ok``, and (when relevant)
        ``error``.
    """
    return ok_response(**_check_path(path=Path(path)))


@mcp.tool()
def check_system_mounts_tool() -> dict[str, Any]:
    """Verifies all filesystem paths in the active system configuration.

    Returns:
        A response dict with ``system_name``, ``paths`` (the per-path status report), and ``summary`` (counts
        of OK, failed, and not-configured paths).
    """
    try:
        system_configuration = get_system_configuration_data()
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))

    filesystem = system_configuration.filesystem
    paths: dict[str, dict[str, Any]] = {
        "root_directory": _check_path(path=filesystem.root_directory),
        "server_directory": _check_path(path=filesystem.server_directory),
        "nas_directory": _check_path(path=filesystem.nas_directory),
    }
    if hasattr(filesystem, "mesoscope_directory"):
        paths["mesoscope_directory"] = _check_path(path=filesystem.mesoscope_directory)

    ok_count = sum(1 for entry in paths.values() if entry.get("ok"))
    fail_count = sum(1 for entry in paths.values() if entry.get("configured", True) and not entry.get("ok"))
    not_configured_count = sum(1 for entry in paths.values() if not entry.get("configured", True))

    return ok_response(
        system_name=system_configuration.name,
        paths=paths,
        summary={"ok": ok_count, "fail": fail_count, "not_configured": not_configured_count},
    )


@mcp.tool()
def list_supported_session_types_tool() -> dict[str, Any]:
    """Enumerates the SessionTypes supported by the Sollertia platform.

    Returns:
        A response dict with ``session_types`` (a list of dicts containing ``value``, ``name``,
        ``descriptor_filename``, and ``descriptor_class`` for each supported session type).
    """
    entries: list[dict[str, Any]] = [
        {
            "value": session_type.value,
            "name": session_type.name,
            "descriptor_filename": DESCRIPTOR_REGISTRY[session_type][0],
            "descriptor_class": DESCRIPTOR_REGISTRY[session_type][1].__name__,
        }
        for session_type in SessionTypes
    ]
    return ok_response(session_types=entries)


@mcp.tool()
def list_supported_acquisition_systems_tool() -> dict[str, Any]:
    """Enumerates the AcquisitionSystems supported by the Sollertia platform.

    Returns:
        A response dict with ``acquisition_systems`` (a list of dicts containing ``value`` and ``name`` for
        each supported acquisition system).
    """
    entries = [{"value": member.value, "name": member.name} for member in AcquisitionSystems]
    return ok_response(acquisition_systems=entries)


@mcp.tool()
def list_supported_trial_types_tool() -> dict[str, Any]:
    """Enumerates the trial classes supported by experiment configurations.

    Returns:
        A response dict with ``trial_types`` (a list of dicts containing ``class_name`` and ``schema`` for
        each supported trial class).
    """
    entries = [
        {"class_name": class_name, "schema": describe_dataclass(cls=trial_class)}
        for class_name, trial_class in _TRIAL_CLASSES.items()
    ]
    return ok_response(trial_types=entries)


@mcp.tool()
def list_supported_trigger_types_tool() -> dict[str, Any]:
    """Enumerates the TriggerType values supported by trial structures.

    Returns:
        A response dict with ``trigger_types`` (a list of dicts containing ``value`` and ``name`` for each
        supported trigger type).
    """
    entries = [{"value": member.value, "name": member.name} for member in TriggerType]
    return ok_response(trigger_types=entries)


def _check_path(path: Path) -> dict[str, Any]:
    """Returns a status dict for a single filesystem path covering existence, mount status, and writability.

    Args:
        path: The filesystem path to check.

    Returns:
        A dict with ``path``, ``exists``, ``is_mount``, ``writable``, and ``ok`` keys describing the path status.
    """
    path_str = str(path)
    # Treats empty or dot-relative paths as unconfigured and short-circuits.
    if not path or path_str in ("", "."):
        return {"path": path_str, "configured": False}
    if not path.exists():
        return {"path": path_str, "exists": False, "ok": False}

    # Probes mount status and write access by creating and removing a temporary test file.
    is_mount = path.is_mount()
    writable = False
    error: str | None = None
    try:
        test_file = path.joinpath(f".mount_test_{uuid.uuid4().hex[:8]}")
        test_file.write_text("test")
        test_file.unlink()
        writable = True
    except PermissionError:
        error = "Permission denied"
    except OSError as os_error:
        error = str(os_error)

    result: dict[str, Any] = {
        "path": path_str,
        "exists": True,
        "is_mount": is_mount,
        "writable": writable,
        "ok": writable,
    }
    if error is not None:
        result["error"] = error
    return result
