"""Provides MCP tools for managing Sollertia platform configuration assets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig

from .mcp_instance import (
    CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY,
    mcp,
    read_yaml,
    serialize,
    ok_response,
    safe_iterdir,
    error_response,
    describe_dataclass,
    write_yaml_validated,
    resolve_root_directory,
)
from ..data_classes import SessionTypes
from ..configuration import (
    EXPERIMENT_CONFIGURATION_REGISTRY,
    Cue,
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
    set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    create_experiment_configuration,
    populate_default_experiment_states,
)

_TRIAL_CLASSES: dict[str, type[WaterRewardTrial | GasPuffTrial]] = {
    "WaterRewardTrial": WaterRewardTrial,
    "GasPuffTrial": GasPuffTrial,
}
"""Maps trial class names to their concrete trial type."""


@mcp.tool()
def get_platform_environment_status_tool() -> dict[str, Any]:
    """Returns a health report for the Sollertia platform configuration components owned by this package.

    Combines working directory, templates directory, and Google credentials status into a single report. Only
    the working directory is required for ``slsa mcp`` to function. The task templates directory is needed only
    when authoring task templates or experiment configurations. Google credentials are needed only by hosts that
    fetch subject metadata or water-restriction logs from Google Sheets. ``overall_ok`` reflects the
    required components only — optional components contribute ``configured`` and ``ok`` per-component but do
    not gate the aggregate. System configuration mount checks are not included here — those live with the
    acquisition runtime package (sl-experiment).

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

    try:
        google_credentials = get_google_credentials_path()
        report["google_credentials"] = {
            "required": False,
            "configured": True,
            "path": str(google_credentials),
            "ok": True,
        }
    except FileNotFoundError as exception:
        report["google_credentials"] = {
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
        set_google_credentials_path(path=path)
    except (FileNotFoundError, OSError, ValueError) as exception:
        return error_response(message=str(exception))
    return ok_response(google_credentials_path=str(path))


@mcp.tool()
def read_task_templates_directory_tool() -> dict[str, Any]:
    """Returns the configured path to the sollertia-unity-tasks task templates directory.

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
        A response dict with ``schema`` containing the TaskTemplate schema and ``nested_classes`` mapping
        each nested dataclass name to its individual schema.
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

    # Restricts the search to a single project when specified, otherwise scans all project directories.
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
    config and the frozen per-session snapshot copied at acquisition time. This tool reads both.
    Pass the per-project path (``<root>/<project>/configuration/<experiment>.yaml``) to inspect
    the authored source. Pass the per-session snapshot path
    (``<session>/raw_data/experiment_configuration.yaml``) to inspect the immutable record of
    what was active when the session was acquired.

    Args:
        file_path: Absolute path to the experiment configuration YAML file. Accepts either the
            per-project source path or the per-session frozen snapshot path.

    Returns:
        A response dict with ``file_path`` and ``data`` containing the full experiment configuration
        payload.
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
            per-project location is ``<root>/<project>/configuration/<experiment>.yaml``. Project
            directories are created implicitly by the sollertia-experiment session-creation flow;
            this tool does not create them.
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
def create_experiment_configuration_tool(
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
            per-project location is ``<root>/<project>/configuration/<experiment>.yaml``. Project
            directories are created implicitly by the sollertia-experiment session-creation flow;
            this tool does not create them.
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
        message = (
            f"Unable to write the experiment configuration to {destination}: a file already exists at this path. "
            f"Pass overwrite=True to replace it."
        )
        return error_response(message=message)
    if not template_file.exists():
        message = f"Unable to load the task template from {template_file}: the file does not exist."
        return error_response(message=message)

    resolved_scene_name = unity_scene_name if unity_scene_name is not None else template_file.stem

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
        A response dict with ``file_path``, ``valid``, and either ``summary`` (carrying ``trial_count``,
        ``state_count``, and ``unity_scene_name``) or ``issues`` (a list of validation error messages).
    """
    configuration_path = Path(file_path)
    if not configuration_path.exists():
        message = f"Unable to validate the experiment configuration at {configuration_path}: the file does not exist."
        return error_response(message=message)
    try:
        experiment_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=configuration_path)
    except Exception as exception:
        return ok_response(valid=False, issues=[str(exception)], file_path=str(configuration_path))
    summary = {
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
        A response dict with ``acquisition_system`` (the validated enum value), ``schema`` (the
        experiment configuration schema for the resolved acquisition system), and ``nested_classes``
        mapping each nested dataclass name (including the supported trial classes) to its individual
        schema.
    """
    resolved = _resolve_experiment_configuration_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    schema = describe_dataclass(cls=resolved)
    schema["nested_classes"] = {
        "ExperimentState": describe_dataclass(cls=ExperimentState),
        "WaterRewardTrial": describe_dataclass(cls=WaterRewardTrial),
        "GasPuffTrial": describe_dataclass(cls=GasPuffTrial),
    }
    return ok_response(acquisition_system=acquisition_system, schema=schema)


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
    entries: list[dict[str, Any]] = [{"value": member.value, "name": member.name} for member in AcquisitionSystems]
    return ok_response(acquisition_systems=entries)


@mcp.tool()
def list_supported_trial_types_tool() -> dict[str, Any]:
    """Enumerates the trial classes supported by experiment configurations.

    Returns:
        A response dict with ``trial_types`` (a list of dicts containing ``class_name`` and ``schema`` for
        each supported trial class).
    """
    entries: list[dict[str, Any]] = [
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
