"""Provides MCP tools for managing Sollertia platform configuration assets."""

from __future__ import annotations

from typing import Any
from pathlib import Path

from ataraxis_base_utilities import ensure_directory_exists

from .mcp_instance import (
    CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY,
    DATASET_MARKER_FILENAME,
    UNINITIALIZED_SESSION_MARKER,
    mcp,
    read_yaml,
    serialize,
    ok_response,
    safe_iterdir,
    error_response,
    describe_dataclass,
    write_yaml_validated,
    resolve_root_directory,
    read_descriptor_incomplete,
)
from ..data_classes import SessionData, RawDataFiles, SessionTypes, session_root_from_marker
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
    WaterRewardTrial,
    AcquisitionSystems,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory as _set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path as _set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory as _set_task_templates_directory,
    create_experiment_configuration,
    populate_default_experiment_states,
)

_TRIAL_CLASSES: dict[str, type[BaseTrial]] = {
    "WaterRewardTrial": WaterRewardTrial,
    "GasPuffTrial": GasPuffTrial,
}
"""Maps trial class names to their dataclass implementations."""


@mcp.tool()
def get_platform_environment_status_tool() -> dict[str, Any]:
    """Returns a health report for the Sollertia platform configuration components owned by this package.

    Combines working directory, templates directory, and Google credentials status into a single report. System
    configuration mount checks are not included here — those live with the acquisition runtime package
    (sl-experiment).

    Returns:
        A response dict with ``overall_ok`` (the aggregate health flag) and ``components`` mapping each
        environment component name to its individual status report.
    """
    report: dict[str, Any] = {}

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

    overall_ok = all(component.get("ok", False) for component in report.values())
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
        _set_working_directory(path=path)
    except (FileNotFoundError, OSError, ValueError) as exception:
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
def set_task_templates_directory_tool(directory: str) -> dict[str, Any]:
    """Sets the path to the sollertia-unity-tasks task templates directory.

    Args:
        directory: The absolute path to the templates directory.

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
def create_project_tool(project: str, root_directory: str) -> dict[str, Any]:
    """Creates a new project directory and its ``configuration`` subdirectory under the root data directory.

    Args:
        project: The name of the project to create.
        root_directory: The absolute path to the root data directory under which to create the project.

    Returns:
        A response dict with ``project``, ``project_path``, and ``already_exists`` (True when the project
        directory was already present and no changes were made).
    """
    root, error = resolve_root_directory(root_directory=root_directory)
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
def get_project_overview_tool(project: str, root_directory: str) -> dict[str, Any]:
    """Returns aggregate counts (animals, sessions by type, experiments, datasets) for a project.

    Distinguishes **uninitialized** sessions (``nk.bin`` marker still present — trash that the
    acquisition runtime never finished setting up) from **incomplete** sessions (descriptor's
    ``incomplete`` field is True — session ran but had runtime issues and may have data gaps).

    Args:
        project: The name of the project.
        root_directory: The absolute path to the root data directory that contains the project.

    Returns:
        A response dict with ``project``, ``project_path``, ``animal_count``, ``animals``,
        ``sessions_by_type``, ``total_sessions``, ``uninitialized_sessions``,
        ``incomplete_sessions``, ``experiment_count``, and ``dataset_count``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
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

    # Tallies sessions by type and counts the two independent "not-healthy" states.
    sessions_by_type: dict[str, int] = {member.value: 0 for member in SessionTypes}
    uninitialized_count = 0
    incomplete_count = 0
    for marker in project_path.rglob(RawDataFiles.SESSION_DATA):
        try:
            instance = SessionData.load(session_path=session_root_from_marker(marker=marker))
        except Exception:  # noqa: S112 - skip unparseable sessions during best-effort overview.
            continue
        session_type_value = serialize(value=instance.session_type)
        if isinstance(session_type_value, str):
            sessions_by_type[session_type_value] = sessions_by_type.get(session_type_value, 0) + 1

        uninitialized = instance.raw_data_path.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
        if uninitialized:
            uninitialized_count += 1
            # Skips the descriptor read for uninitialized sessions because their descriptor is not meaningful.
            continue
        descriptor_incomplete, _descriptor_error = read_descriptor_incomplete(session=instance)
        if descriptor_incomplete:
            incomplete_count += 1

    # Counts experiment configurations and datasets under the project.
    configuration_directory = project_path.joinpath(CONFIGURATION_DIR)
    experiment_count = len(list(configuration_directory.glob("*.yaml"))) if configuration_directory.is_dir() else 0
    dataset_count = len(list(project_path.rglob(DATASET_MARKER_FILENAME)))

    return ok_response(
        project=project,
        project_path=str(project_path),
        animal_count=len(animals),
        animals=sorted(animals),
        sessions_by_type=sessions_by_type,
        total_sessions=sum(sessions_by_type.values()),
        uninitialized_sessions=uninitialized_count,
        incomplete_sessions=incomplete_count,
        experiment_count=experiment_count,
        dataset_count=dataset_count,
    )


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
def read_template_tool(file_path: str) -> dict[str, Any]:
    """Loads a TaskTemplate YAML.

    Args:
        file_path: Absolute path to the template YAML file. The canonical home of task templates is
            the directory configured via ``set_task_templates_directory_tool``; ``discover_templates_tool``
            returns the full paths of templates in that directory.

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
    """Creates or replaces a TaskTemplate YAML.

    The ``template_payload`` must match the TaskTemplate schema (use ``describe_template_schema_tool`` to
    inspect the required structure). The payload is validated against ``TaskTemplate.__post_init__`` before
    being persisted.

    Args:
        file_path: Absolute path to the destination template YAML file. The canonical home of task
            templates is the directory configured via ``set_task_templates_directory_tool``.
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

    Args:
        file_path: Absolute path to the template YAML file.

    Returns:
        A response dict with ``valid`` and either ``summary`` (cue, segment, and trial counts plus the
        cue offset) or ``issues`` (a list of validation error messages).
    """
    template_path = Path(file_path)
    if not template_path.exists():
        return error_response(message=f"File not found: {template_path}")
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
        configuration_directory = project_path.joinpath(CONFIGURATION_DIR)
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
def read_experiment_configuration_tool(file_path: str) -> dict[str, Any]:
    """Loads a MesoscopeExperimentConfiguration YAML from any canonical location.

    The same experiment configuration schema is used for both the authored per-project source
    config and the frozen per-session snapshot copied at acquisition time. This tool reads both:
    pass the per-project path (``<root>/<project>/configuration/<experiment>.yaml``) to inspect
    the authored source, or the per-session snapshot path
    (``<session>/raw_data/experiment_configuration.yaml``) to inspect the immutable record of
    what was active when the session was acquired.

    Args:
        file_path: Absolute path to the experiment configuration YAML file. Accepts either the
            per-project source path or the per-session frozen snapshot path.

    Returns:
        A response dict with ``data`` containing the full experiment configuration payload.
    """
    return read_yaml(file_path=Path(file_path), validator_cls=MesoscopeExperimentConfiguration)


@mcp.tool()
def write_experiment_configuration_tool(
    file_path: str,
    configuration_payload: dict[str, Any],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates or replaces an experiment configuration YAML.

    The ``configuration_payload`` must match the MesoscopeExperimentConfiguration schema. Use
    ``describe_experiment_configuration_schema_tool`` to inspect the required structure.

    Args:
        file_path: Absolute path to the destination experiment configuration YAML file. Canonical
            per-project location is ``<root>/<project>/configuration/<experiment>.yaml``; callers
            must create the project directory first (see ``create_project_tool``).
        configuration_payload: The complete experiment configuration payload.
        overwrite: Determines whether to overwrite an existing experiment configuration file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated configuration payload).
    """
    return write_yaml_validated(
        file_path=Path(file_path),
        payload=configuration_payload,
        validator_cls=MesoscopeExperimentConfiguration,
        overwrite=overwrite,
    )


@mcp.tool()
def create_experiment_config_tool(
    file_path: str,
    template_path: str,
    state_count: int = 1,
    unity_scene_name: str | None = None,
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Creates an experiment configuration from a task template using sensible defaults.

    Loads the template at ``template_path``, builds an experiment configuration via
    ``create_experiment_configuration``, populates the requested number of default-valued runtime
    states, and writes the result to ``file_path``. Use ``write_experiment_configuration_tool``
    instead when full control over the payload is required.

    Args:
        file_path: Absolute path to the destination experiment configuration YAML file. Canonical
            per-project location is ``<root>/<project>/configuration/<experiment>.yaml``; callers
            must create the project directory first (see ``create_project_tool``).
        template_path: Absolute path to the TaskTemplate YAML to instantiate.
        state_count: Number of default-valued runtime states to generate.
        unity_scene_name: The Unity scene name to embed in the experiment configuration. Defaults
            to the template file's stem (the filename without the ``.yaml`` extension), which is the
            convention most projects follow.
        overwrite: Determines whether to overwrite an existing experiment configuration file.

    Returns:
        A response dict with ``file_path``, ``template_path``, and ``data`` (the generated experiment
        configuration payload).
    """
    destination = Path(file_path)
    template_file = Path(template_path)
    if destination.exists() and not overwrite:
        return error_response(
            message=f"File already exists: {destination}. Pass overwrite=True to replace."
        )
    if not template_file.exists():
        return error_response(message=f"Template file not found: {template_file}")

    resolved_scene_name = unity_scene_name if unity_scene_name is not None else template_file.stem

    # Loads the template, generates the experiment configuration, and populates default runtime states.
    try:
        task_template = TaskTemplate.from_yaml(file_path=template_file)
        experiment_configuration = create_experiment_configuration(
            template=task_template,
            system=AcquisitionSystems.MESOSCOPE_VR,
            unity_scene_name=resolved_scene_name,
        )
        populate_default_experiment_states(
            experiment_configuration=experiment_configuration,
            state_count=state_count,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        experiment_configuration.to_yaml(file_path=destination)
    except Exception as exception:
        return error_response(message=f"Failed to create experiment configuration: {exception}")

    return ok_response(
        file_path=str(destination),
        template_path=str(template_file),
        data=serialize(value=experiment_configuration),
    )


@mcp.tool()
def validate_experiment_configuration_tool(file_path: str) -> dict[str, Any]:
    """Loads and validates an experiment configuration YAML.

    Args:
        file_path: Absolute path to the experiment configuration YAML file.

    Returns:
        A response dict with ``valid`` and either ``summary`` or ``issues``.
    """
    configuration_path = Path(file_path)
    if not configuration_path.exists():
        return error_response(message=f"File not found: {configuration_path}")
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
def list_supported_session_types_tool() -> dict[str, Any]:
    """Enumerates the SessionTypes supported by the Sollertia platform.

    Returns:
        A response dict with ``session_types`` (a list of dicts containing ``value``, ``name``,
        and ``descriptor_class`` for each supported session type). The descriptor filename is
        always ``session_descriptor.yaml`` regardless of session type and is therefore not
        returned.
    """
    entries: list[dict[str, Any]] = [
        {
            "value": session_type.value,
            "name": session_type.name,
            "descriptor_class": DESCRIPTOR_REGISTRY[session_type].__name__,
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
