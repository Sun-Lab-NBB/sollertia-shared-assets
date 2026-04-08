"""Provides the MCP server for agentic management of Sollertia platform configuration and runtime data assets.

Exposes the canonical MCP tool surface that all sibling Sollertia libraries (sollertia-experiment,
sollertia-unity-tasks, sollertia-forgery, and downstream agents) use to discover, read, write, validate, and
introspect the configuration and runtime data files defined in this library.
"""

from __future__ import annotations

from enum import Enum
import uuid
from typing import TYPE_CHECKING, Any, Literal, get_type_hints
from pathlib import Path
import contextlib
from dataclasses import MISSING, fields, is_dataclass

import yaml  # type: ignore[import-untyped]
from mcp.server.fastmcp import FastMCP
from ataraxis_base_utilities import ensure_directory_exists

from ..data_classes import (
    DrugData,
    DatasetData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    SessionTypes,
    InjectionData,
    ProcedureData,
    DatasetSession,
    ZaberPositions,
    MesoscopePositions,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)
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

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig


_SESSION_MARKER_FILENAME: str = "session_data.yaml"
"""Marker filename used to identify session directories during recursive discovery walks."""

_DATASET_MARKER_FILENAME: str = "dataset.yaml"
"""Marker filename used to identify dataset directories during recursive discovery walks."""

_INCOMPLETE_SESSION_MARKER: str = "nk.bin"
"""Marker file present in raw_data while a session is incomplete; removed when runtime initializes."""

_RAW_DATA_DIR: str = "raw_data"
"""Subdirectory under each session that holds the raw data and metadata files."""

_PROCESSED_DATA_DIR: str = "processed_data"
"""Subdirectory under each session that holds processed data on processing machines."""

_CONFIGURATION_DIR: str = "configuration"
"""Subdirectory under each project that holds experiment configuration YAML files."""

_HARDWARE_STATE_FILENAME: str = "hardware_state.yaml"
"""Canonical filename for the per-session MesoscopeHardwareState YAML."""

_ZABER_POSITIONS_FILENAME: str = "zaber_positions.yaml"
"""Canonical filename for the per-session ZaberPositions YAML."""

_MESOSCOPE_POSITIONS_FILENAME: str = "mesoscope_positions.yaml"
"""Canonical filename for the per-session MesoscopePositions YAML."""

_SESSION_SYSTEM_CONFIG_FILENAME: str = "system_configuration.yaml"
"""Canonical filename for the per-session snapshot of MesoscopeSystemConfiguration."""

_SESSION_EXPERIMENT_CONFIG_FILENAME: str = "experiment_configuration.yaml"
"""Canonical filename for the per-session snapshot of MesoscopeExperimentConfiguration."""

_SERVER_CONFIG_FILENAME: str = "server_configuration.yaml"
"""Canonical filename for the ServerConfiguration YAML stored in the working directory."""

_DESCRIPTOR_REGISTRY: dict[SessionTypes, tuple[str, type[YamlConfig]]] = {
    SessionTypes.LICK_TRAINING: ("lick_training_descriptor.yaml", LickTrainingDescriptor),
    SessionTypes.RUN_TRAINING: ("run_training_descriptor.yaml", RunTrainingDescriptor),
    SessionTypes.MESOSCOPE_EXPERIMENT: ("experiment_descriptor.yaml", MesoscopeExperimentDescriptor),
    SessionTypes.WINDOW_CHECKING: ("window_checking_descriptor.yaml", WindowCheckingDescriptor),
}
"""Maps each session type to its canonical descriptor filename and dataclass."""

_TRIAL_CLASSES: dict[str, type[BaseTrial]] = {
    "WaterRewardTrial": WaterRewardTrial,
    "GasPuffTrial": GasPuffTrial,
}
"""Maps trial class names to their dataclass implementations."""

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sollertia-shared-assets", json_response=True)


@mcp.tool()
def discover_projects_tool(root_directory: str | None = None) -> dict[str, Any]:
    """Lists all projects accessible to the data acquisition system.

    Scans the immediate children of the data root for project directories, returning each project's name and
    aggregate counts (animals and experiment configurations).

    Args:
        root_directory: Override for the root data directory. When omitted, the active system configuration's
            ``filesystem.root_directory`` is used.

    Returns:
        A response dict with ``projects`` (list of project summary dicts) and ``total_projects``.
    """
    root, error = _resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    projects: list[dict[str, Any]] = []
    for child in sorted(_safe_iterdir(directory=root), key=lambda candidate: candidate.name):  # type: ignore[arg-type]
        if not child.is_dir():
            continue
        configuration_dir = child.joinpath(_CONFIGURATION_DIR)
        experiment_count = len(list(configuration_dir.glob("*.yaml"))) if configuration_dir.is_dir() else 0
        animal_count = sum(
            1 for animal in _safe_iterdir(directory=child) if animal.is_dir() and animal.name != _CONFIGURATION_DIR
        )
        projects.append(
            {
                "name": child.name,
                "path": str(child),
                "animal_count": animal_count,
                "experiment_count": experiment_count,
            }
        )

    return _ok(projects=projects, total_projects=len(projects), root_directory=str(root))


@mcp.tool()
def discover_animals_tool(project: str, root_directory: str | None = None) -> dict[str, Any]:
    """Lists animal subdirectories within a project.

    Args:
        project: The name of the project to enumerate animals for.
        root_directory: Override for the root data directory.

    Returns:
        A response dict with ``animals`` (list of animal summary dicts), ``total_animals``, and ``project``.
    """
    root, error = _resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.is_dir():
        return _err(message=f"Project '{project}' not found at {project_path}")

    animals: list[dict[str, Any]] = []
    for child in sorted(_safe_iterdir(directory=project_path), key=lambda candidate: candidate.name):
        if not child.is_dir() or child.name == _CONFIGURATION_DIR:
            continue
        session_count = len(list(child.glob(f"*/{_RAW_DATA_DIR}/{_SESSION_MARKER_FILENAME}")))
        animals.append({"animal_id": child.name, "path": str(child), "session_count": session_count})

    return _ok(animals=animals, total_animals=len(animals), project=project)


@mcp.tool()
def discover_sessions_tool(
    root_directory: str | None = None,
    project: str | None = None,
    animal_id: str | None = None,
    session_type: str | None = None,
) -> dict[str, Any]:
    """Recursively discovers all sessions under the data root.

    Walks the directory tree looking for ``session_data.yaml`` markers and returns a flat list of session
    summaries. The optional ``project``, ``animal_id``, and ``session_type`` filters narrow the search.

    Args:
        root_directory: Override for the root data directory.
        project: When provided, only sessions belonging to this project are returned.
        animal_id: When provided, only sessions belonging to this animal are returned.
        session_type: When provided, only sessions of this type are returned. Must be a valid SessionTypes value.

    Returns:
        A response dict with ``sessions`` (list of session summary dicts) and ``total_sessions``.
    """
    root, error = _resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    if session_type is not None:
        try:
            session_type_filter: SessionTypes | None = SessionTypes(session_type)
        except ValueError:
            valid = ", ".join(member.value for member in SessionTypes)
            return _err(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
    else:
        session_type_filter = None

    search_root = root
    if project is not None:
        search_root = root.joinpath(project)  # type: ignore[union-attr]
        if not search_root.is_dir():
            return _err(message=f"Project '{project}' not found at {search_root}")
        if animal_id is not None:
            search_root = search_root.joinpath(animal_id)
            if not search_root.is_dir():
                return _err(message=f"Animal '{animal_id}' not found at {search_root}")

    markers = sorted(search_root.rglob(_SESSION_MARKER_FILENAME))  # type: ignore[union-attr]
    sessions: list[dict[str, Any]] = []
    for marker in markers:
        summary = _load_session_summary(marker=marker)
        if "error" in summary:
            sessions.append(summary)
            continue
        if project is not None and summary.get("project") != project:
            continue
        if animal_id is not None and summary.get("animal") != animal_id:
            continue
        if session_type_filter is not None and summary.get("session_type") != session_type_filter.value:
            continue
        sessions.append(summary)

    return _ok(sessions=sessions, total_sessions=len(sessions), root_directory=str(root))


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
    root, error = _resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    project_paths: list[Path]
    if project is not None:
        project_path = root.joinpath(project)  # type: ignore[union-attr]
        if not project_path.is_dir():
            return _err(message=f"Project '{project}' not found at {project_path}")
        project_paths = [project_path]
    else:
        project_paths = [child for child in _safe_iterdir(directory=root) if child.is_dir()]  # type: ignore[arg-type]

    experiments: list[dict[str, Any]] = []
    for project_path in sorted(project_paths, key=lambda candidate: candidate.name):
        configuration_dir = project_path.joinpath(_CONFIGURATION_DIR)
        if not configuration_dir.is_dir():
            continue
        experiments.extend(
            {
                "project": project_path.name,
                "experiment": config_file.stem,
                "path": str(config_file),
            }
            for config_file in sorted(configuration_dir.glob("*.yaml"))
        )

    return _ok(experiments=experiments, total_experiments=len(experiments))


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
        return _err(message=str(exception))

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

    return _ok(
        templates=templates,
        total_templates=len(templates),
        templates_directory=str(templates_directory),
    )


@mcp.tool()
def discover_datasets_tool(
    datasets_root: str | None = None,
    project: str | None = None,
) -> dict[str, Any]:
    """Recursively discovers all dataset directories under the datasets root.

    Walks the directory tree looking for ``dataset.yaml`` markers and returns a flat list of dataset summaries.

    Args:
        datasets_root: Override for the datasets root directory. When omitted, the active system configuration's
            ``filesystem.root_directory`` is used (datasets often live alongside acquisition data).
        project: When provided, only datasets belonging to this project are returned.

    Returns:
        A response dict with ``datasets`` (list of dataset summary dicts) and ``total_datasets``.
    """
    root, error = _resolve_root_directory(root_directory=datasets_root)
    if error is not None:
        return error

    markers = sorted(root.rglob(_DATASET_MARKER_FILENAME))  # type: ignore[union-attr]
    datasets: list[dict[str, Any]] = []
    for marker in markers:
        summary = _load_dataset_summary(marker=marker)
        if project is not None and summary.get("project") != project:
            continue
        datasets.append(summary)

    return _ok(datasets=datasets, total_datasets=len(datasets), datasets_root=str(root))


@mcp.tool()
def discover_subjects_tool(project: str | None = None) -> dict[str, Any]:
    """Discovers subjects (animals) by scanning project directories on disk.

    For each subject found on disk, attempts to locate a cached SurgeryData YAML and reports whether one was
    found. This tool is the disk-side counterpart to a future Google Sheets-backed surgery lookup.

    Args:
        project: When provided, only subjects belonging to this project are returned.

    Returns:
        A response dict with ``subjects`` (list of subject summary dicts) and ``total_subjects``.
    """
    root, error = _resolve_root_directory(root_directory=None)
    if error is not None:
        return error

    project_paths: list[Path]
    if project is not None:
        project_path = root.joinpath(project)  # type: ignore[union-attr]
        if not project_path.is_dir():
            return _err(message=f"Project '{project}' not found at {project_path}")
        project_paths = [project_path]
    else:
        project_paths = [child for child in _safe_iterdir(directory=root) if child.is_dir()]  # type: ignore[arg-type]

    seen: dict[str, dict[str, Any]] = {}
    for project_path in project_paths:
        for animal_dir in _safe_iterdir(directory=project_path):
            if not animal_dir.is_dir() or animal_dir.name == _CONFIGURATION_DIR:
                continue
            entry = seen.setdefault(
                animal_dir.name,
                {
                    "subject_id": animal_dir.name,
                    "projects": [],
                    "session_count": 0,
                    "has_cached_surgery_data": False,
                },
            )
            if project_path.name not in entry["projects"]:
                entry["projects"].append(project_path.name)
            entry["session_count"] += len(list(animal_dir.glob(f"*/{_RAW_DATA_DIR}/{_SESSION_MARKER_FILENAME}")))
            surgery_path, _ = _resolve_surgery_path(subject_id=animal_dir.name, project=project_path.name)
            if surgery_path is not None:
                entry["has_cached_surgery_data"] = True
                entry["surgery_data_path"] = str(surgery_path)

    subjects = sorted(seen.values(), key=lambda subject: subject["subject_id"])
    return _ok(subjects=subjects, total_subjects=len(subjects))


@mcp.tool()
def discover_session_descriptors_tool(session_path: str) -> dict[str, Any]:
    """Returns the inventory of descriptor, hardware state, and position files present in a session's raw_data.

    Args:
        session_path: Path to the session root directory (containing the ``raw_data`` subdirectory).

    Returns:
        A response dict with ``files`` (list of name, path, and kind entries describing each YAML file found).
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error

    raw_data_dir = session_root.joinpath(_RAW_DATA_DIR)  # type: ignore[union-attr]
    if not raw_data_dir.is_dir():
        return _err(message=f"raw_data directory not found at {raw_data_dir}")

    known_kinds = {
        _SESSION_MARKER_FILENAME: "session_data",
        _SESSION_SYSTEM_CONFIG_FILENAME: "system_configuration_snapshot",
        _SESSION_EXPERIMENT_CONFIG_FILENAME: "experiment_configuration_snapshot",
        _HARDWARE_STATE_FILENAME: "hardware_state",
        _ZABER_POSITIONS_FILENAME: "zaber_positions",
        _MESOSCOPE_POSITIONS_FILENAME: "mesoscope_positions",
    }
    descriptor_filenames = {filename for filename, _ in _DESCRIPTOR_REGISTRY.values()}

    files: list[dict[str, Any]] = []
    for candidate in sorted(raw_data_dir.glob("*.yaml")):
        if candidate.name in known_kinds:
            kind = known_kinds[candidate.name]
        elif candidate.name in descriptor_filenames:
            kind = "session_descriptor"
        else:
            kind = "unknown"
        files.append({"name": candidate.name, "path": str(candidate), "kind": kind})

    incomplete = raw_data_dir.joinpath(_INCOMPLETE_SESSION_MARKER).exists()
    return _ok(files=files, total_files=len(files), session_path=str(session_root), incomplete=incomplete)


@mcp.tool()
def read_session_data_tool(session_path: str) -> dict[str, Any]:
    """Loads the SessionData YAML for a session.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``data`` (the full SessionData payload) and ``incomplete`` (the nk.bin marker flag).
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    try:
        instance = SessionData.load(session_path=session_root)  # type: ignore[arg-type]
    except Exception as exception:
        return _err(message=f"Failed to load SessionData: {exception}")
    incomplete = instance.raw_data_path.joinpath(_INCOMPLETE_SESSION_MARKER).exists()
    return _ok(data=_serialize(value=instance), incomplete=incomplete, session_path=str(session_root))


@mcp.tool()
def read_session_descriptor_tool(session_path: str) -> dict[str, Any]:
    """Detects the appropriate descriptor class for a session and loads its descriptor YAML.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``data`` (the descriptor payload), ``descriptor_class``, ``session_type``, and
        the resolved ``file_path``.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    try:
        session = SessionData.load(session_path=session_root)  # type: ignore[arg-type]
    except Exception as exception:
        return _err(message=f"Failed to load SessionData: {exception}")

    session_type = (
        session.session_type if isinstance(session.session_type, SessionTypes) else SessionTypes(session.session_type)
    )
    descriptor_path, descriptor_class = _find_descriptor_for_session(
        session_root=session_root,  # type: ignore[arg-type]
        session_type=session_type,
    )
    if descriptor_path is None:
        return _err(
            message=(
                f"Could not locate a descriptor file for session_type '{session_type.value}' under "
                f"{session_root}/{_RAW_DATA_DIR}"
            ),
        )

    response = _read_yaml(file_path=descriptor_path, validator_cls=descriptor_class)
    if response.get("success"):
        response["descriptor_class"] = descriptor_class.__name__
        response["session_type"] = session_type.value
    return response


@mcp.tool()
def read_session_hardware_state_tool(session_path: str) -> dict[str, Any]:
    """Loads the MesoscopeHardwareState YAML for a session.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``data`` containing the hardware state payload.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _HARDWARE_STATE_FILENAME)  # type: ignore[union-attr]
    return _read_yaml(file_path=file_path, validator_cls=MesoscopeHardwareState)


@mcp.tool()
def read_session_zaber_positions_tool(session_path: str) -> dict[str, Any]:
    """Loads the ZaberPositions YAML for a session.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``data`` containing the Zaber positions payload.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _ZABER_POSITIONS_FILENAME)  # type: ignore[union-attr]
    return _read_yaml(file_path=file_path, validator_cls=ZaberPositions)


@mcp.tool()
def read_session_mesoscope_positions_tool(session_path: str) -> dict[str, Any]:
    """Loads the MesoscopePositions YAML for a session.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``data`` containing the Mesoscope positions payload.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _MESOSCOPE_POSITIONS_FILENAME)  # type: ignore[union-attr]
    return _read_yaml(file_path=file_path, validator_cls=MesoscopePositions)


@mcp.tool()
def read_session_system_configuration_tool(session_path: str) -> dict[str, Any]:
    """Loads the per-session snapshot of MesoscopeSystemConfiguration.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``data`` containing the system configuration snapshot payload.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _SESSION_SYSTEM_CONFIG_FILENAME)  # type: ignore[union-attr]
    return _read_yaml(file_path=file_path, validator_cls=MesoscopeSystemConfiguration)


@mcp.tool()
def read_session_experiment_configuration_tool(session_path: str) -> dict[str, Any]:
    """Loads the per-session snapshot of MesoscopeExperimentConfiguration.

    Only meaningful for sessions of type ``mesoscope experiment``.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``data`` containing the experiment configuration snapshot payload.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _SESSION_EXPERIMENT_CONFIG_FILENAME)  # type: ignore[union-attr]
    return _read_yaml(file_path=file_path, validator_cls=MesoscopeExperimentConfiguration)


@mcp.tool()
def read_dataset_tool(dataset_path: str) -> dict[str, Any]:
    """Loads the DatasetData YAML for a dataset.

    Args:
        dataset_path: Path to the dataset root directory (containing ``dataset.yaml``).

    Returns:
        A response dict with ``data`` containing the full DatasetData payload, including the resolved session
        list, and ``dataset_path``.
    """
    path = Path(dataset_path)
    if not path.exists():
        return _err(message=f"Dataset path does not exist: {path}")
    try:
        instance = DatasetData.load(dataset_path=path)
    except Exception as exception:
        return _err(message=f"Failed to load DatasetData: {exception}")
    return _ok(data=_serialize(value=instance), dataset_path=str(path))


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
        return _err(message=str(exception))
    template_path = templates_directory.joinpath(f"{template_name}.yaml")
    return _read_yaml(file_path=template_path, validator_cls=TaskTemplate)


@mcp.tool()
def read_experiment_configuration_tool(project: str, experiment: str) -> dict[str, Any]:
    """Loads a MesoscopeExperimentConfiguration YAML for a project's experiment.

    Args:
        project: The name of the project containing the experiment.
        experiment: The name of the experiment configuration (without the ``.yaml`` extension).

    Returns:
        A response dict with ``data`` containing the full experiment configuration payload.
    """
    root, error = _resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    config_path = root.joinpath(project, _CONFIGURATION_DIR, f"{experiment}.yaml")  # type: ignore[union-attr]
    return _read_yaml(file_path=config_path, validator_cls=MesoscopeExperimentConfiguration)


@mcp.tool()
def read_system_configuration_tool() -> dict[str, Any]:
    """Loads the active MesoscopeSystemConfiguration from the working directory.

    Returns:
        A response dict with ``data`` containing the full system configuration payload.
    """
    try:
        instance = get_system_configuration_data()
    except (FileNotFoundError, OSError, ValueError) as exception:
        return _err(message=str(exception))
    return _ok(data=_serialize(value=instance))


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
        return _err(message=str(exception))
    serialized = _serialize(value=instance)
    if isinstance(serialized, dict) and "password" in serialized:
        serialized["password"] = "<masked>"  # noqa: S105 - literal masking placeholder, not a real password.
    return _ok(data=serialized)


@mcp.tool()
def read_subject_tool(subject_id: str, project: str | None = None) -> dict[str, Any]:
    """Loads SubjectData for a subject from the cached SurgeryData YAML.

    Args:
        subject_id: The unique identifier of the subject.
        project: Optional project hint to scope the surgery cache lookup.

    Returns:
        A response dict with ``data`` containing the SubjectData payload and ``surgery_data_path``.
    """
    surgery_path, error = _resolve_surgery_path(subject_id=subject_id, project=project)
    if error is not None:
        return error
    response = _read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    data = response.get("data", {})
    subject = data.get("subject") if isinstance(data, dict) else None
    if subject is None:
        return _err(message=f"SurgeryData at {surgery_path} does not contain a subject section")
    return _ok(data=subject, surgery_data_path=str(surgery_path))


@mcp.tool()
def read_subject_surgery_tool(subject_id: str, project: str | None = None) -> dict[str, Any]:
    """Loads the full SurgeryData payload for a subject.

    Args:
        subject_id: The unique identifier of the subject.
        project: Optional project hint to scope the surgery cache lookup.

    Returns:
        A response dict with ``data`` containing the full SurgeryData payload (subject, procedure, drugs,
        implants, and injections sections).
    """
    surgery_path, error = _resolve_surgery_path(subject_id=subject_id, project=project)
    if error is not None:
        return error
    return _read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]


@mcp.tool()
def read_subject_implants_tool(subject_id: str, project: str | None = None) -> dict[str, Any]:
    """Loads the list of ImplantData for a subject from the cached SurgeryData YAML.

    Args:
        subject_id: The unique identifier of the subject.
        project: Optional project hint to scope the surgery cache lookup.

    Returns:
        A response dict with ``implants`` (list of ImplantData payloads), ``total_implants``, and
        ``surgery_data_path``.
    """
    surgery_path, error = _resolve_surgery_path(subject_id=subject_id, project=project)
    if error is not None:
        return error
    response = _read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    implants = response.get("data", {}).get("implants", []) if isinstance(response.get("data"), dict) else []
    return _ok(implants=implants, total_implants=len(implants), surgery_data_path=str(surgery_path))


@mcp.tool()
def read_subject_injections_tool(subject_id: str, project: str | None = None) -> dict[str, Any]:
    """Loads the list of InjectionData for a subject from the cached SurgeryData YAML.

    Args:
        subject_id: The unique identifier of the subject.
        project: Optional project hint to scope the surgery cache lookup.

    Returns:
        A response dict with ``injections`` (list of InjectionData payloads), ``total_injections``, and
        ``surgery_data_path``.
    """
    surgery_path, error = _resolve_surgery_path(subject_id=subject_id, project=project)
    if error is not None:
        return error
    response = _read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    injections = response.get("data", {}).get("injections", []) if isinstance(response.get("data"), dict) else []
    return _ok(injections=injections, total_injections=len(injections), surgery_data_path=str(surgery_path))


@mcp.tool()
def read_subject_drugs_tool(subject_id: str, project: str | None = None) -> dict[str, Any]:
    """Loads the DrugData payload for a subject from the cached SurgeryData YAML.

    Args:
        subject_id: The unique identifier of the subject.
        project: Optional project hint to scope the surgery cache lookup.

    Returns:
        A response dict with ``data`` containing the DrugData payload and ``surgery_data_path``.
    """
    surgery_path, error = _resolve_surgery_path(subject_id=subject_id, project=project)
    if error is not None:
        return error
    response = _read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    drugs = response.get("data", {}).get("drugs") if isinstance(response.get("data"), dict) else None
    if drugs is None:
        return _err(message=f"SurgeryData at {surgery_path} does not contain a drugs section")
    return _ok(data=drugs, surgery_data_path=str(surgery_path))


@mcp.tool()
def read_working_directory_tool() -> dict[str, Any]:
    """Returns the configured Sollertia platform working directory path.

    Returns:
        A response dict with ``working_directory`` containing the path.
    """
    try:
        path = get_working_directory()
    except FileNotFoundError as exception:
        return _err(message=str(exception))
    return _ok(working_directory=str(path))


@mcp.tool()
def read_google_credentials_tool() -> dict[str, Any]:
    """Returns the configured path to the Google service account credentials JSON file.

    Returns:
        A response dict with ``google_credentials_path`` containing the path.
    """
    try:
        path = get_google_credentials_path()
    except FileNotFoundError as exception:
        return _err(message=str(exception))
    return _ok(google_credentials_path=str(path))


@mcp.tool()
def read_task_templates_directory_tool() -> dict[str, Any]:
    """Returns the configured path to the sollertia-unity-tasks templates directory.

    Returns:
        A response dict with ``task_templates_directory`` containing the path.
    """
    try:
        path = get_task_templates_directory()
    except FileNotFoundError as exception:
        return _err(message=str(exception))
    return _ok(task_templates_directory=str(path))


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
        return _err(message=str(exception))
    file_path = templates_directory.joinpath(f"{template_name}.yaml")
    return _write_yaml_validated(
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
    root, error = _resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.is_dir():
        return _err(message=f"Project '{project}' does not exist at {project_path}. Use create_project_tool first.")
    file_path = project_path.joinpath(_CONFIGURATION_DIR, f"{experiment}.yaml")
    return _write_yaml_validated(
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
        return _err(message=f"Invalid acquisition system '{system}'. Valid values: {valid}")

    try:
        working_directory = get_working_directory()
    except FileNotFoundError as exception:
        return _err(message=str(exception))

    file_path = working_directory.joinpath(_CONFIGURATION_DIR, f"{system}_system_configuration.yaml")
    return _write_yaml_validated(
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
        return _err(message=str(exception))
    file_path = working_directory.joinpath(_CONFIGURATION_DIR, _SERVER_CONFIG_FILENAME)
    response = _write_yaml_validated(
        file_path=file_path,
        payload=configuration_payload,
        validator_cls=ServerConfiguration,
        overwrite=overwrite,
    )
    if response.get("success") and isinstance(response.get("data"), dict):
        response["data"]["password"] = "<masked>"  # noqa: S105 - literal masking placeholder, not a real password.
    return response


@mcp.tool()
def write_dataset_tool(
    name: str,
    project: str,
    session_type: str,
    acquisition_system: str,
    sessions: list[dict[str, str]],
    datasets_root: str | None = None,
) -> dict[str, Any]:
    """Creates a new dataset by materializing the dataset hierarchy on disk.

    Wraps ``DatasetData.create``: builds the dataset directory, creates animal and session subdirectories, and
    writes the dataset.yaml manifest. Each entry in ``sessions`` must specify the ``session`` name and ``animal``
    ID; the ``session_path`` field is resolved automatically.

    Args:
        name: The unique dataset name.
        project: The source project name.
        session_type: The SessionTypes value all sessions belong to.
        acquisition_system: The AcquisitionSystems value all sessions were acquired on.
        sessions: List of dicts each containing ``{"session": str, "animal": str}``.
        datasets_root: Override for the datasets root directory. When omitted, the active system configuration's
            ``filesystem.root_directory`` is used.

    Returns:
        A response dict with ``dataset_path``, ``dataset_data_path``, and ``data`` (the materialized DatasetData
        payload).
    """
    try:
        session_type_enum = SessionTypes(session_type)
    except ValueError:
        valid = ", ".join(member.value for member in SessionTypes)
        return _err(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")

    try:
        acquisition_system_enum = AcquisitionSystems(acquisition_system)
    except ValueError:
        valid = ", ".join(member.value for member in AcquisitionSystems)
        return _err(message=f"Invalid acquisition_system '{acquisition_system}'. Valid values: {valid}")

    if not sessions:
        return _err(message="The 'sessions' argument must contain at least one entry.")

    dataset_session_objects: list[DatasetSession] = []
    for entry in sessions:
        if not isinstance(entry, dict) or "session" not in entry or "animal" not in entry:
            return _err(
                message=f"Invalid session entry {entry!r}. Each entry must be a dict with 'session' and 'animal' keys.",
            )
        dataset_session_objects.append(DatasetSession(session=entry["session"], animal=entry["animal"]))

    # Creates the datasets root directory when an explicit override is provided and the directory does not exist.
    root: Path
    if datasets_root is not None:
        root = Path(datasets_root)
        ensure_directory_exists(root)
    else:
        try:
            system_configuration = get_system_configuration_data()
            root = system_configuration.filesystem.root_directory
        except (FileNotFoundError, OSError, ValueError) as exception:
            return _err(message=f"Unable to resolve datasets root directory: {exception}")

    try:
        instance = DatasetData.create(
            name=name,
            project=project,
            session_type=session_type_enum,
            acquisition_system=acquisition_system_enum,
            sessions=tuple(dataset_session_objects),
            datasets_root=root,
        )
    except Exception as exception:
        return _err(message=f"Failed to create dataset: {exception}")

    return _ok(
        dataset_path=str(instance.dataset_data_path.parent),
        dataset_data_path=str(instance.dataset_data_path),
        data=_serialize(value=instance),
    )


@mcp.tool()
def write_session_descriptor_tool(
    session_path: str,
    descriptor_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Creates or replaces a session descriptor YAML for a session.

    Detects the appropriate descriptor class from the session's ``session_type`` (loaded from
    ``session_data.yaml``) and writes the payload to the canonical descriptor filename in ``raw_data``.

    Args:
        session_path: Path to the session root directory.
        descriptor_payload: The complete descriptor payload matching the appropriate descriptor schema.
        overwrite: Determines whether to overwrite an existing descriptor file.

    Returns:
        A response dict with ``file_path``, ``data`` (the validated payload), ``descriptor_class``, and
        ``session_type``.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    try:
        session = SessionData.load(session_path=session_root)  # type: ignore[arg-type]
    except Exception as exception:
        return _err(message=f"Failed to load SessionData: {exception}")

    session_type = (
        session.session_type if isinstance(session.session_type, SessionTypes) else SessionTypes(session.session_type)
    )
    canonical_filename, descriptor_class = _DESCRIPTOR_REGISTRY[session_type]
    file_path = session_root.joinpath(_RAW_DATA_DIR, canonical_filename)  # type: ignore[union-attr]
    response = _write_yaml_validated(
        file_path=file_path,
        payload=descriptor_payload,
        validator_cls=descriptor_class,
        overwrite=overwrite,
    )
    if response.get("success"):
        response["descriptor_class"] = descriptor_class.__name__
        response["session_type"] = session_type.value
    return response


@mcp.tool()
def write_session_hardware_state_tool(
    session_path: str,
    hardware_state_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Creates or replaces the MesoscopeHardwareState YAML for a session.

    Args:
        session_path: Path to the session root directory.
        hardware_state_payload: The complete MesoscopeHardwareState payload.
        overwrite: Determines whether to overwrite an existing hardware state file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated payload).
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _HARDWARE_STATE_FILENAME)  # type: ignore[union-attr]
    return _write_yaml_validated(
        file_path=file_path,
        payload=hardware_state_payload,
        validator_cls=MesoscopeHardwareState,
        overwrite=overwrite,
    )


@mcp.tool()
def write_session_zaber_positions_tool(
    session_path: str,
    positions_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Creates or replaces the ZaberPositions YAML for a session.

    Args:
        session_path: Path to the session root directory.
        positions_payload: The complete ZaberPositions payload.
        overwrite: Determines whether to overwrite an existing positions file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated payload).
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _ZABER_POSITIONS_FILENAME)  # type: ignore[union-attr]
    return _write_yaml_validated(
        file_path=file_path,
        payload=positions_payload,
        validator_cls=ZaberPositions,
        overwrite=overwrite,
    )


@mcp.tool()
def write_session_mesoscope_positions_tool(
    session_path: str,
    positions_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Creates or replaces the MesoscopePositions YAML for a session.

    Args:
        session_path: Path to the session root directory.
        positions_payload: The complete MesoscopePositions payload.
        overwrite: Determines whether to overwrite an existing positions file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated payload).
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    file_path = session_root.joinpath(_RAW_DATA_DIR, _MESOSCOPE_POSITIONS_FILENAME)  # type: ignore[union-attr]
    return _write_yaml_validated(
        file_path=file_path,
        payload=positions_payload,
        validator_cls=MesoscopePositions,
        overwrite=overwrite,
    )


@mcp.tool()
def create_project_tool(project: str) -> dict[str, Any]:
    """Creates a new project directory and its ``configuration`` subdirectory under the system root.

    Args:
        project: The name of the project to create.

    Returns:
        A response dict with ``project``, ``project_path``, and ``already_exists`` (True when the project
        directory was already present and no changes were made).
    """
    root, error = _resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    project_path = root.joinpath(project)  # type: ignore[union-attr]
    configuration_path = project_path.joinpath(_CONFIGURATION_DIR)
    if project_path.exists():
        return _ok(project=project, project_path=str(project_path), already_exists=True)
    try:
        ensure_directory_exists(configuration_path)
    except (FileNotFoundError, OSError) as exception:
        return _err(message=f"Failed to create project directory: {exception}")
    return _ok(project=project, project_path=str(project_path), already_exists=False)


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
    root, error = _resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.exists():
        return _err(message=f"Project '{project}' does not exist. Use create_project_tool to create it first.")

    file_path = project_path.joinpath(_CONFIGURATION_DIR, f"{experiment}.yaml")
    if file_path.exists() and not overwrite:
        return _err(message=f"Experiment '{experiment}' already exists in project '{project}'.")

    try:
        templates_directory = get_task_templates_directory()
    except FileNotFoundError as exception:
        return _err(message=str(exception))
    template_path = templates_directory.joinpath(f"{template}.yaml")
    if not template_path.exists():
        available = sorted(template_file.stem for template_file in templates_directory.glob("*.yaml"))
        return _err(
            message=(
                f"Template '{template}' not found. Available templates: {', '.join(available) if available else 'none'}"
            ),
        )

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
        return _err(message=f"Failed to create experiment configuration: {exception}")

    return _ok(
        project=project,
        experiment=experiment,
        template=template,
        file_path=str(file_path),
        data=_serialize(value=experiment_configuration),
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
        return _err(message=str(exception))
    return _ok(working_directory=str(path))


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
        return _err(message=str(exception))
    return _ok(google_credentials_path=str(path))


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
        return _err(message=str(exception))
    return _ok(task_templates_directory=str(path))


@mcp.tool()
def describe_template_schema_tool() -> dict[str, Any]:
    """Returns the schema for TaskTemplate, including nested Cue, Segment, TrialStructure, and VREnvironment.

    Use the returned schema to construct a valid payload for ``write_template_tool``.

    Returns:
        A response dict with ``schema`` containing the TaskTemplate schema and ``nested_classes`` mapping
        each nested dataclass name to its individual schema.
    """
    schema = _describe_dataclass(cls=TaskTemplate)
    schema["nested_classes"] = {
        "Cue": _describe_dataclass(cls=Cue),
        "Segment": _describe_dataclass(cls=Segment),
        "TrialStructure": _describe_dataclass(cls=TrialStructure),
        "VREnvironment": _describe_dataclass(cls=VREnvironment),
    }
    return _ok(schema=schema)


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
        return _err(message=f"Invalid acquisition_system '{acquisition_system}'. Valid values: {valid}")
    schema = _describe_dataclass(cls=MesoscopeExperimentConfiguration)
    schema["nested_classes"] = {
        "Cue": _describe_dataclass(cls=Cue),
        "Segment": _describe_dataclass(cls=Segment),
        "VREnvironment": _describe_dataclass(cls=VREnvironment),
        "ExperimentState": _describe_dataclass(cls=ExperimentState),
        "WaterRewardTrial": _describe_dataclass(cls=WaterRewardTrial),
        "GasPuffTrial": _describe_dataclass(cls=GasPuffTrial),
    }
    return _ok(schema=schema)


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
        return _err(message=f"Invalid acquisition_system '{acquisition_system}'. Valid values: {valid}")
    schema = _describe_dataclass(cls=MesoscopeSystemConfiguration)
    schema["nested_classes"] = {
        "MesoscopeFileSystem": _describe_dataclass(cls=MesoscopeFileSystem),
        "MesoscopeGoogleSheets": _describe_dataclass(cls=MesoscopeGoogleSheets),
        "MesoscopeCameras": _describe_dataclass(cls=MesoscopeCameras),
        "MesoscopeMicroControllers": _describe_dataclass(cls=MesoscopeMicroControllers),
        "MesoscopeExternalAssets": _describe_dataclass(cls=MesoscopeExternalAssets),
    }
    return _ok(schema=schema)


@mcp.tool()
def describe_session_descriptor_schema_tool(session_type: str) -> dict[str, Any]:
    """Returns the schema for the descriptor associated with a given session type.

    Args:
        session_type: The SessionTypes value to describe.

    Returns:
        A response dict with ``session_type``, ``descriptor_filename``, and ``schema``.
    """
    try:
        session_type_enum = SessionTypes(session_type)
    except ValueError:
        valid = ", ".join(member.value for member in SessionTypes)
        return _err(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
    canonical_filename, descriptor_class = _DESCRIPTOR_REGISTRY[session_type_enum]
    return _ok(
        session_type=session_type_enum.value,
        descriptor_filename=canonical_filename,
        schema=_describe_dataclass(cls=descriptor_class),
    )


@mcp.tool()
def describe_dataset_schema_tool() -> dict[str, Any]:
    """Returns the schema for DatasetData and its nested DatasetSession.

    Returns:
        A response dict with ``schema`` containing the dataset schema and ``nested_classes``.
    """
    schema = _describe_dataclass(cls=DatasetData)
    schema["nested_classes"] = {"DatasetSession": _describe_dataclass(cls=DatasetSession)}
    return _ok(schema=schema)


@mcp.tool()
def describe_surgery_schema_tool() -> dict[str, Any]:
    """Returns the schema for SurgeryData and its nested subclasses.

    Returns:
        A response dict with ``schema`` containing the surgery schema and ``nested_classes`` mapping each
        nested dataclass (subject, procedure, drugs, implants, and injections) to its individual schema.
    """
    schema = _describe_dataclass(cls=SurgeryData)
    schema["nested_classes"] = {
        "SubjectData": _describe_dataclass(cls=SubjectData),
        "ProcedureData": _describe_dataclass(cls=ProcedureData),
        "DrugData": _describe_dataclass(cls=DrugData),
        "ImplantData": _describe_dataclass(cls=ImplantData),
        "InjectionData": _describe_dataclass(cls=InjectionData),
    }
    return _ok(schema=schema)


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
            "descriptor_filename": _DESCRIPTOR_REGISTRY[session_type][0],
            "descriptor_class": _DESCRIPTOR_REGISTRY[session_type][1].__name__,
        }
        for session_type in SessionTypes
    ]
    return _ok(session_types=entries)


@mcp.tool()
def list_supported_acquisition_systems_tool() -> dict[str, Any]:
    """Enumerates the AcquisitionSystems supported by the Sollertia platform.

    Returns:
        A response dict with ``acquisition_systems`` (a list of dicts containing ``value`` and ``name`` for
        each supported acquisition system).
    """
    entries = [{"value": member.value, "name": member.name} for member in AcquisitionSystems]
    return _ok(acquisition_systems=entries)


@mcp.tool()
def list_supported_trial_types_tool() -> dict[str, Any]:
    """Enumerates the trial classes supported by experiment configurations.

    Returns:
        A response dict with ``trial_types`` (a list of dicts containing ``class_name`` and ``schema`` for
        each supported trial class).
    """
    entries = [
        {"class_name": class_name, "schema": _describe_dataclass(cls=trial_class)}
        for class_name, trial_class in _TRIAL_CLASSES.items()
    ]
    return _ok(trial_types=entries)


@mcp.tool()
def list_supported_trigger_types_tool() -> dict[str, Any]:
    """Enumerates the TriggerType values supported by trial structures.

    Returns:
        A response dict with ``trigger_types`` (a list of dicts containing ``value`` and ``name`` for each
        supported trigger type).
    """
    entries = [{"value": member.value, "name": member.name} for member in TriggerType]
    return _ok(trigger_types=entries)


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
        return _err(message=str(exception))
    template_path = templates_directory.joinpath(f"{template_name}.yaml")
    if not template_path.exists():
        return _err(message=f"Template '{template_name}' not found at {template_path}")
    try:
        template = TaskTemplate.from_yaml(file_path=template_path)
    except Exception as exception:
        return _ok(valid=False, issues=[str(exception)], file_path=str(template_path))
    summary = {
        "cue_count": len(template.cues),
        "segment_count": len(template.segments),
        "trial_count": len(template.trial_structures),
        "cue_offset_cm": template.cue_offset_cm,
    }
    return _ok(valid=True, file_path=str(template_path), summary=summary)


@mcp.tool()
def validate_experiment_configuration_tool(project: str, experiment: str) -> dict[str, Any]:
    """Loads and validates an experiment configuration YAML for a project.

    Args:
        project: The name of the project containing the experiment.
        experiment: The name of the experiment configuration (without the ``.yaml`` extension).

    Returns:
        A response dict with ``valid`` and either ``summary`` or ``issues``.
    """
    root, error = _resolve_root_directory(root_directory=None)
    if error is not None:
        return error
    config_path = root.joinpath(project, _CONFIGURATION_DIR, f"{experiment}.yaml")  # type: ignore[union-attr]
    if not config_path.exists():
        return _err(message=f"Experiment '{experiment}' not found at {config_path}")
    try:
        config = MesoscopeExperimentConfiguration.from_yaml(file_path=config_path)
    except Exception as exception:
        return _ok(valid=False, issues=[str(exception)], file_path=str(config_path))
    summary = {
        "cue_count": len(config.cues),
        "segment_count": len(config.segments),
        "trial_count": len(config.trial_structures),
        "state_count": len(config.experiment_states),
        "unity_scene_name": config.unity_scene_name,
    }
    return _ok(valid=True, file_path=str(config_path), summary=summary)


@mcp.tool()
def validate_system_configuration_tool() -> dict[str, Any]:
    """Loads and validates the active system configuration plus all configured filesystem paths.

    Returns:
        A response dict with ``valid``, ``issues``, ``system_name``, and ``paths`` (the per-path mount
        status report).
    """
    try:
        config = get_system_configuration_data()
    except (FileNotFoundError, OSError, ValueError) as exception:
        return _ok(valid=False, issues=[str(exception)])

    filesystem = config.filesystem
    paths_report: dict[str, dict[str, Any]] = {
        "root_directory": _check_path(path=filesystem.root_directory),
        "server_directory": _check_path(path=filesystem.server_directory),
        "nas_directory": _check_path(path=filesystem.nas_directory),
    }
    if hasattr(filesystem, "mesoscope_directory"):
        paths_report["mesoscope_directory"] = _check_path(path=filesystem.mesoscope_directory)

    issues = [
        f"{name}: {report.get('error', 'not OK')}"
        for name, report in paths_report.items()
        if report.get("configured", True) and not report.get("ok", False)
    ]
    return _ok(
        valid=not issues,
        issues=issues,
        system_name=config.name,
        paths=paths_report,
    )


@mcp.tool()
def validate_dataset_tool(dataset_path: str) -> dict[str, Any]:
    """Loads and validates a dataset, verifying that all referenced session paths still exist.

    Args:
        dataset_path: Path to the dataset root directory.

    Returns:
        A response dict with ``valid``, ``issues``, ``missing_sessions`` (when invalid), and ``summary``.
    """
    path = Path(dataset_path)
    if not path.exists():
        return _ok(valid=False, issues=[f"Dataset path does not exist: {path}"])
    try:
        dataset = DatasetData.load(dataset_path=path)
    except Exception as exception:
        return _ok(valid=False, issues=[str(exception)])

    missing: list[dict[str, str]] = [
        {
            "session": session.session,
            "animal": session.animal,
            "expected_path": str(session.session_path),
        }
        for session in dataset.sessions
        if not session.session_path.exists()
    ]

    return _ok(
        valid=not missing,
        issues=[f"Missing session: {entry['animal']}/{entry['session']}" for entry in missing],
        missing_sessions=missing,
        summary={
            "name": dataset.name,
            "project": dataset.project,
            "session_type": _serialize(value=dataset.session_type),
            "session_count": len(dataset.sessions),
            "animal_count": len(dataset.animals),
        },
    )


@mcp.tool()
def validate_session_tool(session_path: str) -> dict[str, Any]:
    """Validates that a session has the expected files for its session_type.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``valid``, ``issues``, ``summary``, and ``session_path``.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return _ok(valid=False, issues=[error["error"]])

    issues: list[str] = []

    raw_data_dir = session_root.joinpath(_RAW_DATA_DIR)  # type: ignore[union-attr]
    if not raw_data_dir.is_dir():
        issues.append(f"Missing raw_data directory: {raw_data_dir}")
        return _ok(valid=False, issues=issues, session_path=str(session_root))

    try:
        session = SessionData.load(session_path=session_root)  # type: ignore[arg-type]
    except Exception as exception:
        return _ok(
            valid=False,
            issues=[f"Failed to load SessionData: {exception}"],
            session_path=str(session_root),
        )

    session_type = (
        session.session_type if isinstance(session.session_type, SessionTypes) else SessionTypes(session.session_type)
    )

    descriptor_path, _ = _find_descriptor_for_session(
        session_root=session_root,  # type: ignore[arg-type]
        session_type=session_type,
    )
    if descriptor_path is None:
        issues.append(f"Missing descriptor file for session_type '{session_type.value}'")

    if session_type == SessionTypes.MESOSCOPE_EXPERIMENT:
        experiment_snapshot = raw_data_dir.joinpath(_SESSION_EXPERIMENT_CONFIG_FILENAME)
        if not experiment_snapshot.exists():
            issues.append(f"Missing experiment configuration snapshot: {experiment_snapshot}")

    system_snapshot = raw_data_dir.joinpath(_SESSION_SYSTEM_CONFIG_FILENAME)
    if not system_snapshot.exists():
        issues.append(f"Missing system configuration snapshot: {system_snapshot}")

    incomplete = raw_data_dir.joinpath(_INCOMPLETE_SESSION_MARKER).exists()

    summary = {
        "session_name": session.session_name,
        "project": session.project_name,
        "animal": session.animal_id,
        "session_type": session_type.value,
        "incomplete": incomplete,
    }
    return _ok(valid=not issues, issues=issues, summary=summary, session_path=str(session_root))


@mcp.tool()
def get_session_status_tool(session_path: str) -> dict[str, Any]:
    """Returns lifecycle status for a single session.

    Reads the session's ``nk.bin`` marker presence and inspects the processed_data directory to derive a
    high-level lifecycle state. The status is ``incomplete`` when ``nk.bin`` is still present, ``acquired``
    when ``nk.bin`` has been removed but no processed data exists, and ``processed`` when the processed_data
    directory contains files.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``status``, ``incomplete``, ``has_processed_data``, and ``session_path``.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    raw_data_dir = session_root.joinpath(_RAW_DATA_DIR)  # type: ignore[union-attr]
    if not raw_data_dir.is_dir():
        return _err(message=f"raw_data directory not found at {raw_data_dir}")
    incomplete = raw_data_dir.joinpath(_INCOMPLETE_SESSION_MARKER).exists()
    processed_data_dir = session_root.joinpath(_PROCESSED_DATA_DIR)  # type: ignore[union-attr]
    has_processed_data = processed_data_dir.is_dir() and any(processed_data_dir.iterdir())

    if incomplete:
        status = "incomplete"
    elif has_processed_data:
        status = "processed"
    else:
        status = "acquired"

    return _ok(
        status=status,
        incomplete=incomplete,
        has_processed_data=has_processed_data,
        session_path=str(session_root),
    )


@mcp.tool()
def get_batch_session_status_overview_tool(root_directory: str | None = None) -> dict[str, Any]:
    """Aggregates session lifecycle status across every session under the data root.

    Args:
        root_directory: Override for the root data directory.

    Returns:
        A response dict with ``counts`` (per-status counts), ``sessions`` (per-session status entries),
        ``total_sessions``, and ``root_directory``.
    """
    root, error = _resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    counts: dict[str, int] = {"incomplete": 0, "acquired": 0, "processed": 0, "error": 0}
    sessions: list[dict[str, Any]] = []
    for marker in sorted(root.rglob(_SESSION_MARKER_FILENAME)):  # type: ignore[union-attr]
        session_root = _session_root_from_marker(marker=marker)
        try:
            instance = SessionData.load(session_path=session_root)
        except Exception as exception:
            counts["error"] += 1
            sessions.append({"session_path": str(session_root), "status": "error", "error": str(exception)})
            continue
        incomplete = instance.raw_data_path.joinpath(_INCOMPLETE_SESSION_MARKER).exists()
        processed_data_dir = session_root.joinpath(_PROCESSED_DATA_DIR)
        has_processed_data = processed_data_dir.is_dir() and any(processed_data_dir.iterdir())
        if incomplete:
            status = "incomplete"
        elif has_processed_data:
            status = "processed"
        else:
            status = "acquired"
        counts[status] += 1
        sessions.append(
            {
                "session_name": instance.session_name,
                "project": instance.project_name,
                "animal": instance.animal_id,
                "session_type": _serialize(value=instance.session_type),
                "session_path": str(session_root),
                "status": status,
            }
        )

    return _ok(counts=counts, sessions=sessions, total_sessions=len(sessions), root_directory=str(root))


@mcp.tool()
def get_project_overview_tool(project: str) -> dict[str, Any]:
    """Returns aggregate counts (animals, sessions by type, experiments, datasets) for a project.

    Args:
        project: The name of the project.

    Returns:
        A response dict with ``project``, ``project_path``, ``animal_count``, ``animals``, ``sessions_by_type``,
        ``total_sessions``, ``incomplete_sessions``, ``experiment_count``, and ``dataset_count``.
    """
    root, error = _resolve_root_directory(root_directory=None)
    if error is not None:
        return error

    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.is_dir():
        return _err(message=f"Project '{project}' not found at {project_path}")

    animals = [
        child.name
        for child in _safe_iterdir(directory=project_path)
        if child.is_dir() and child.name != _CONFIGURATION_DIR
    ]

    sessions_by_type: dict[str, int] = {member.value: 0 for member in SessionTypes}
    incomplete_count = 0
    for marker in project_path.rglob(_SESSION_MARKER_FILENAME):
        try:
            instance = SessionData.load(session_path=_session_root_from_marker(marker=marker))
        except Exception:  # noqa: S112 - skip unparseable sessions during best-effort overview.
            continue
        session_type_value = _serialize(value=instance.session_type)
        if isinstance(session_type_value, str):
            sessions_by_type[session_type_value] = sessions_by_type.get(session_type_value, 0) + 1
        if instance.raw_data_path.joinpath(_INCOMPLETE_SESSION_MARKER).exists():
            incomplete_count += 1

    configuration_dir = project_path.joinpath(_CONFIGURATION_DIR)
    experiment_count = len(list(configuration_dir.glob("*.yaml"))) if configuration_dir.is_dir() else 0
    dataset_count = len(list(project_path.rglob(_DATASET_MARKER_FILENAME)))

    return _ok(
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
    return _ok(overall_ok=overall_ok, components=report)


@mcp.tool()
def check_mount_accessibility_tool(path: str) -> dict[str, Any]:
    """Verifies that a filesystem path is accessible and writable.

    Args:
        path: The filesystem path to verify.

    Returns:
        A response dict with ``path``, ``exists``, ``is_mount``, ``writable``, ``ok``, and (when relevant)
        ``error``.
    """
    return _ok(**_check_path(path=Path(path)))


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
        return _err(message=str(exception))

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

    return _ok(
        system_name=system_configuration.name,
        paths=paths,
        summary={"ok": ok_count, "fail": fail_count, "not_configured": not_configured_count},
    )


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)


def _ok(**payload: Any) -> dict[str, Any]:  # noqa: ANN401 - response builder accepts arbitrary serializable values.
    """Constructs a successful response dict with a ``success`` flag set to True."""
    return {"success": True, **payload}


def _err(message: str) -> dict[str, Any]:
    """Constructs a failure response dict with a ``success`` flag set to False and the provided error message."""
    return {"success": False, "error": message}


def _serialize(value: Any) -> Any:  # noqa: ANN401 - recursive helper accepts any serializable value.
    """Recursively converts a dataclass, Path, Enum, mapping, or sequence into JSON-friendly Python.

    Args:
        value: The value to convert.

    Returns:
        A plain Python representation suitable for JSON serialization.
    """
    if value is None:
        return None
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field_definition.name: _serialize(value=getattr(value, field_definition.name))
            for field_definition in fields(value)
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _serialize(value=item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_serialize(value=item) for item in value]
    return value


def _describe_type(type_hint: Any) -> str:  # noqa: ANN401 - introspection helper accepts arbitrary type hints.
    """Returns a human-readable string for the given type hint."""
    if type_hint is None:
        return "None"
    if isinstance(type_hint, type):
        return type_hint.__name__
    return str(type_hint).replace("typing.", "")


def _describe_dataclass(cls: type, *, recurse: bool = True) -> dict[str, Any]:
    """Returns a structured schema description of a dataclass type.

    The returned dict has shape ``{"class": <name>, "fields": {<field_name>: {"type", "default"|"required",
    "nested"?}}}`` where ``nested`` recursively describes nested dataclass types. The recursion guard prevents
    infinite recursion when a dataclass references itself either directly or transitively.

    Args:
        cls: The dataclass type to describe.
        recurse: Determines whether to recursively describe nested dataclass fields.

    Returns:
        A structured schema dict.
    """

    def _describe_inner(target: type, seen: frozenset[type]) -> dict[str, Any]:
        if target in seen:
            return {"class": target.__name__, "recursive_reference": True}
        next_seen = seen | {target}

        if not is_dataclass(target):
            return {"type": _describe_type(type_hint=target)}

        try:
            hints = get_type_hints(target)
        except Exception:
            hints = {}

        schema: dict[str, Any] = {"class": target.__name__, "fields": {}}
        # noinspection PyDataclass
        for field_definition in fields(target):
            type_hint = hints.get(field_definition.name, field_definition.type)
            field_schema: dict[str, Any] = {"type": _describe_type(type_hint=type_hint)}
            if field_definition.default is not MISSING:
                field_schema["default"] = _serialize(value=field_definition.default)
            elif field_definition.default_factory is not MISSING:
                try:
                    field_schema["default"] = _serialize(value=field_definition.default_factory())
                except Exception:
                    field_schema["required"] = True
            else:
                field_schema["required"] = True
            if recurse and isinstance(type_hint, type) and is_dataclass(type_hint):
                field_schema["nested"] = _describe_inner(target=type_hint, seen=next_seen)
            schema["fields"][field_definition.name] = field_schema

        return schema

    return _describe_inner(target=cls, seen=frozenset())


def _write_yaml_validated(
    file_path: Path,
    payload: dict[str, Any],
    validator_cls: type[YamlConfig],
    *,
    overwrite: bool = False,
    use_save_method: bool = False,
) -> dict[str, Any]:
    """Writes a payload as YAML to ``file_path`` and validates it by loading through ``validator_cls``.

    Notes:
        Writes the payload to a temporary sibling file first, validates by instantiating ``validator_cls`` from
        that file (which triggers the dataclass ``__post_init__`` validation), and only on success re-serializes
        through the canonical ``to_yaml`` (or ``save``) method to produce the final file. Re-runs
        ``__post_init__`` after loading so that any ``init=False`` derived fields whose values may have been
        overwritten by missing YAML keys are recomputed correctly (for example,
        ``ServerConfiguration.shared_storage_root``).

    Args:
        file_path: The destination file path.
        payload: The dict payload to serialize as YAML.
        validator_cls: The YamlConfig dataclass used to validate the payload.
        overwrite: Determines whether to overwrite an existing destination file.
        use_save_method: Determines whether to use ``instance.save(path=...)`` instead of
            ``instance.to_yaml(file_path=...)``. Required for ``MesoscopeSystemConfiguration`` whose ``save``
            method handles valve calibration tuples.

    Returns:
        A response dict with the file path and serialized data on success, or an error dict on failure.
    """
    if file_path.exists() and not overwrite:
        return _err(message=f"File already exists: {file_path}. Pass overwrite=True to replace.")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    # Keeps the temp file ending in .yaml because YamlConfig.from_yaml rejects non-.yaml paths.
    temp_path = file_path.with_name(f".{file_path.stem}.{uuid.uuid4().hex[:8]}.tmp.yaml")

    try:
        temp_path.write_text(yaml.safe_dump(payload, sort_keys=False))
        instance: YamlConfig = validator_cls.from_yaml(file_path=temp_path)
        if hasattr(instance, "__post_init__"):
            instance.__post_init__()
    except Exception as exception:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()
        return _err(message=f"Validation failed for {validator_cls.__name__}: {exception}")
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()

    try:
        if use_save_method and hasattr(instance, "save"):
            instance.save(path=file_path)
        else:
            instance.to_yaml(file_path=file_path)
    except Exception as exception:
        return _err(message=f"Failed to persist {validator_cls.__name__} to {file_path}: {exception}")

    return _ok(file_path=str(file_path), data=_serialize(value=instance))


def _read_yaml(file_path: Path, validator_cls: type[YamlConfig]) -> dict[str, Any]:
    """Loads a YAML file via ``validator_cls`` and returns its serialized form.

    Args:
        file_path: The path to the YAML file to load.
        validator_cls: The YamlConfig dataclass to use for validation.

    Returns:
        A response dict with ``file_path`` and ``data`` (the serialized payload) on success, or an error dict
        on failure.
    """
    if not file_path.exists():
        return _err(message=f"File not found: {file_path}")
    try:
        instance = validator_cls.from_yaml(file_path=file_path)
    except Exception as exception:
        return _err(message=f"Failed to load {file_path} as {validator_cls.__name__}: {exception}")
    return _ok(file_path=str(file_path), data=_serialize(value=instance))


def _resolve_root_directory(root_directory: str | None) -> tuple[Path | None, dict[str, Any] | None]:
    """Resolves the root data directory, falling back to the configured system root.

    Args:
        root_directory: An explicit override for the root data directory, or None to fall back to the active
            system configuration.

    Returns:
        A tuple of the resolved Path and an error dict. Exactly one element is non-None.
    """
    if root_directory is not None:
        path = Path(root_directory)
        if not path.exists():
            return None, _err(message=f"Root directory does not exist: {path}")
        if not path.is_dir():
            return None, _err(message=f"Root directory is not a directory: {path}")
        return path, None
    try:
        system_configuration = get_system_configuration_data()
    except (FileNotFoundError, OSError, ValueError) as exception:
        return None, _err(message=f"Unable to resolve root directory from system configuration: {exception}")
    return system_configuration.filesystem.root_directory, None


def _resolve_session_root(session_path: str) -> tuple[Path | None, dict[str, Any] | None]:
    """Resolves an input session path to its root directory (the parent of ``raw_data``).

    Accepts either the session root itself or its ``raw_data`` subdirectory and returns the canonical session
    root in both cases.

    Args:
        session_path: A path that points either at the session root or at the session's raw_data directory.

    Returns:
        A tuple of the resolved session root Path and an error dict. Exactly one element is non-None.
    """
    path = Path(session_path)
    if not path.exists():
        return None, _err(message=f"Session path does not exist: {path}")
    if path.joinpath(_RAW_DATA_DIR).is_dir():
        return path, None
    if path.name == _RAW_DATA_DIR and path.is_dir():
        return path.parent, None
    return None, _err(message=f"Could not locate the {_RAW_DATA_DIR} directory under {path}")


def _session_root_from_marker(marker: Path) -> Path:
    """Returns the session root directory given a session_data.yaml marker file.

    The marker is expected at ``<session_root>/raw_data/session_data.yaml``, so the session root is two
    directory levels above the marker.
    """
    return marker.parents[1]


def _safe_iterdir(directory: Path) -> list[Path]:
    """Returns immediate non-hidden children of a directory, ignoring permission errors."""
    try:
        return [child for child in directory.iterdir() if not child.name.startswith(".")]
    except OSError, PermissionError:
        return []


def _load_session_summary(marker: Path) -> dict[str, Any]:
    """Loads a SessionData YAML and returns a flat summary dict for use in discovery responses."""
    session_root = _session_root_from_marker(marker=marker)
    try:
        instance: SessionData = SessionData.load(session_path=session_root)
    except Exception as exception:
        return {
            "session_path": str(session_root),
            "marker": str(marker),
            "error": f"Failed to load session: {exception}",
        }
    incomplete = instance.raw_data_path.joinpath(_INCOMPLETE_SESSION_MARKER).exists()
    return {
        "session_name": instance.session_name,
        "project": instance.project_name,
        "animal": instance.animal_id,
        "session_type": _serialize(value=instance.session_type),
        "acquisition_system": _serialize(value=instance.acquisition_system),
        "experiment_name": instance.experiment_name,
        "session_path": str(session_root),
        "raw_data_path": str(instance.raw_data_path),
        "processed_data_path": str(instance.processed_data_path),
        "incomplete": incomplete,
    }


def _load_dataset_summary(marker: Path) -> dict[str, Any]:
    """Loads a DatasetData YAML and returns a flat summary dict for use in discovery responses."""
    dataset_root = marker.parent
    try:
        instance: DatasetData = DatasetData.load(dataset_path=dataset_root)
    except Exception as exception:
        return {
            "dataset_path": str(dataset_root),
            "marker": str(marker),
            "error": f"Failed to load dataset: {exception}",
        }
    return {
        "name": instance.name,
        "project": instance.project,
        "session_type": _serialize(value=instance.session_type),
        "acquisition_system": _serialize(value=instance.acquisition_system),
        "session_count": len(instance.sessions),
        "animal_count": len(instance.animals),
        "dataset_path": str(dataset_root),
        "dataset_data_path": str(instance.dataset_data_path),
    }


def _check_path(path: Path) -> dict[str, Any]:
    """Returns a status dict for a single filesystem path covering existence, mount status, and writability."""
    path_str = str(path)
    if not path or path_str in ("", "."):
        return {"path": path_str, "configured": False}
    if not path.exists():
        return {"path": path_str, "exists": False, "ok": False}

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


def _find_descriptor_for_session(
    session_root: Path,
    session_type: SessionTypes,
) -> tuple[Path | None, type[YamlConfig]]:
    """Locates the descriptor file for a session, falling back to scanning raw_data when necessary.

    Tries the canonical descriptor filename first. If that file is not present, scans the session's raw_data
    directory for any YAML file that successfully loads as the expected descriptor class. Returns ``(None,
    descriptor_class)`` when no candidate file is found.
    """
    canonical_filename, descriptor_class = _DESCRIPTOR_REGISTRY[session_type]
    raw_data_dir = session_root.joinpath(_RAW_DATA_DIR)
    canonical_path = raw_data_dir.joinpath(canonical_filename)
    if canonical_path.exists():
        return canonical_path, descriptor_class

    # Falls back to scanning raw_data for any YAML that loads as the expected descriptor class.
    if raw_data_dir.is_dir():
        for candidate in sorted(raw_data_dir.glob("*.yaml")):
            if candidate.name in {
                _SESSION_MARKER_FILENAME,
                _SESSION_SYSTEM_CONFIG_FILENAME,
                _SESSION_EXPERIMENT_CONFIG_FILENAME,
                _HARDWARE_STATE_FILENAME,
                _ZABER_POSITIONS_FILENAME,
                _MESOSCOPE_POSITIONS_FILENAME,
            }:
                continue
            try:
                descriptor_class.from_yaml(file_path=candidate)
            except Exception:  # noqa: S112 - skip unparseable candidates during best-effort discovery.
                continue
            return candidate, descriptor_class

    return None, descriptor_class


def _resolve_surgery_path(
    subject_id: str,
    project: str | None = None,
) -> tuple[Path | None, dict[str, Any] | None]:
    """Locates a cached SurgeryData YAML on disk for the given subject.

    Notes:
        This is a best-effort filesystem search. The library does not currently mandate a single canonical
        location for cached surgery data; this helper looks under the configured working directory and the
        configured root data directory for ``surgery_data/<subject_id>.yaml`` and similar conventional paths.

    Args:
        subject_id: The unique identifier of the subject whose surgery data to locate.
        project: Optional project hint that scopes the lookup to a specific project subtree.

    Returns:
        A tuple of the resolved Path and an error dict. Exactly one element is non-None.
    """
    candidate_paths: list[Path] = []
    candidate_filenames = (f"{subject_id}.yaml", f"{subject_id}_surgery.yaml", "surgery_data.yaml")

    try:
        working_directory = get_working_directory()
        candidate_paths.extend(working_directory.joinpath("surgery_data", filename) for filename in candidate_filenames)
        candidate_paths.extend(working_directory.joinpath(filename) for filename in candidate_filenames)
    except FileNotFoundError, OSError, ValueError:
        pass

    try:
        system_configuration = get_system_configuration_data()
        root = system_configuration.filesystem.root_directory
        if project is not None:
            candidate_paths.extend(root.joinpath(project, "surgery_data", filename) for filename in candidate_filenames)
            candidate_paths.extend(root.joinpath(project, subject_id, filename) for filename in candidate_filenames)
        candidate_paths.extend(root.joinpath("surgery_data", filename) for filename in candidate_filenames)
    except FileNotFoundError, OSError, ValueError:
        pass

    for candidate in candidate_paths:
        if candidate.exists():
            return candidate, None

    return None, _err(
        message=(
            f"Could not locate a cached SurgeryData file for subject '{subject_id}'. Searched under the working "
            f"directory and the system root directory using conventional paths "
            f"({', '.join(candidate_filenames)})."
        ),
    )
