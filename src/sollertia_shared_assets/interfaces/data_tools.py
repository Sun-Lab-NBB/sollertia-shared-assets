"""Provides MCP tools for discovering, reading, writing, and validating runtime data assets.

Covers sessions, datasets, subjects, surgery data, and session descriptors. All tools register on the
shared ``mcp`` instance from ``mcp_instance``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

from ataraxis_base_utilities import ensure_directory_exists

from .mcp_instance import (
    _RAW_DATA_DIR,
    _CONFIGURATION_DIR,
    _PROCESSED_DATA_DIR,
    _DESCRIPTOR_REGISTRY,
    _DATASET_MARKER_FILENAME,
    _HARDWARE_STATE_FILENAME,
    _SESSION_MARKER_FILENAME,
    _ZABER_POSITIONS_FILENAME,
    _INCOMPLETE_SESSION_MARKER,
    _MESOSCOPE_POSITIONS_FILENAME,
    _SESSION_SYSTEM_CONFIG_FILENAME,
    _SESSION_EXPERIMENT_CONFIG_FILENAME,
    _ok,
    mcp,
    _err,
    _read_yaml,
    _serialize,
    _safe_iterdir,
    _describe_dataclass,
    _write_yaml_validated,
    _resolve_root_directory,
    _session_root_from_marker,
)
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
    MesoscopeHardwareState,
)
from ..configuration import (
    AcquisitionSystems,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    get_system_configuration_data,
)

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig


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
def describe_dataset_schema_tool() -> dict[str, Any]:
    """Returns the schema for DatasetData and its nested DatasetSession.

    Returns:
        A response dict with ``schema`` containing the dataset schema and ``nested_classes``.
    """
    schema = _describe_dataclass(cls=DatasetData)
    schema["nested_classes"] = {"DatasetSession": _describe_dataclass(cls=DatasetSession)}
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


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


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


def _load_session_summary(marker: Path) -> dict[str, Any]:
    """Loads a SessionData YAML and returns a flat summary dict for use in discovery responses.

    Args:
        marker: The path to the ``session_data.yaml`` marker file.
    """
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
    """Loads a DatasetData YAML and returns a flat summary dict for use in discovery responses.

    Args:
        marker: The path to the ``dataset.yaml`` marker file.
    """
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


def _find_descriptor_for_session(
    session_root: Path,
    session_type: SessionTypes,
) -> tuple[Path | None, type[YamlConfig]]:
    """Locates the descriptor file for a session, falling back to scanning raw_data when necessary.

    Tries the canonical descriptor filename first. If that file is not present, scans the session's raw_data
    directory for any YAML file that successfully loads as the expected descriptor class.

    Args:
        session_root: The session root directory containing the ``raw_data`` subdirectory.
        session_type: The session type whose descriptor to locate.

    Returns:
        A tuple of the resolved descriptor file path (or None when no candidate is found) and the descriptor
        dataclass type.
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
    except OSError, ValueError:
        pass

    try:
        system_configuration = get_system_configuration_data()
        root = system_configuration.filesystem.root_directory
        if project is not None:
            candidate_paths.extend(root.joinpath(project, "surgery_data", filename) for filename in candidate_filenames)
            candidate_paths.extend(root.joinpath(project, subject_id, filename) for filename in candidate_filenames)
        candidate_paths.extend(root.joinpath("surgery_data", filename) for filename in candidate_filenames)
    except OSError, ValueError:
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
