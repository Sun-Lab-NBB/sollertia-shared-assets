"""Provides MCP tools for discovering, reading, writing, and validating runtime data assets.

Covers sessions, datasets, subjects, surgery data, and session descriptors. All tools register on the
shared ``mcp`` instance from ``mcp_instance``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

from .mcp_instance import (
    CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY,
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
from ..data_classes import (
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    RawDataFiles,
    SessionTypes,
    InjectionData,
    ProcedureData,
    MesoscopeHardwareState,
)
from ..configuration import (
    MesoscopeExperimentConfiguration,
    get_working_directory,
)

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig


@mcp.tool()
def discover_projects_tool(root_directory: str | None = None) -> dict[str, Any]:
    """Lists all projects accessible to the data acquisition system.

    Scans the immediate children of the data root for project directories, returning each project's name and
    aggregate counts (animals and experiment configurations).

    Args:
        root_directory: The absolute path to the root data directory to scan. Required — the
            system-configuration-based fallback has moved to the acquisition runtime package.

    Returns:
        A response dict with ``projects`` (list of project summary dicts) and ``total_projects``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    projects: list[dict[str, Any]] = []
    for child in sorted(safe_iterdir(directory=root), key=lambda candidate: candidate.name):  # type: ignore[arg-type]
        if not child.is_dir():
            continue
        configuration_dir = child.joinpath(CONFIGURATION_DIR)
        experiment_count = len(list(configuration_dir.glob("*.yaml"))) if configuration_dir.is_dir() else 0
        animal_count = sum(
            1 for animal in safe_iterdir(directory=child) if animal.is_dir() and animal.name != CONFIGURATION_DIR
        )
        projects.append(
            {
                "name": child.name,
                "path": str(child),
                "animal_count": animal_count,
                "experiment_count": experiment_count,
            }
        )

    return ok_response(projects=projects, total_projects=len(projects), root_directory=str(root))


@mcp.tool()
def discover_animals_tool(project: str, root_directory: str | None = None) -> dict[str, Any]:
    """Lists animal subdirectories within a project.

    Args:
        project: The name of the project to enumerate animals for.
        root_directory: The absolute path to the root data directory to scan.

    Returns:
        A response dict with ``animals`` (list of animal summary dicts), ``total_animals``, and ``project``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    project_path = root.joinpath(project)  # type: ignore[union-attr]
    if not project_path.is_dir():
        return error_response(message=f"Project '{project}' not found at {project_path}")

    animals: list[dict[str, Any]] = []
    for child in sorted(safe_iterdir(directory=project_path), key=lambda candidate: candidate.name):
        if not child.is_dir() or child.name == CONFIGURATION_DIR:
            continue
        session_count = len(list(child.glob(f"*/raw_data/{RawDataFiles.SESSION_DATA}")))
        animals.append({"animal_id": child.name, "path": str(child), "session_count": session_count})

    return ok_response(animals=animals, total_animals=len(animals), project=project)


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
        root_directory: The absolute path to the root data directory to scan.
        project: When provided, only sessions belonging to this project are returned.
        animal_id: When provided, only sessions belonging to this animal are returned.
        session_type: When provided, only sessions of this type are returned. Must be a valid SessionTypes value.

    Returns:
        A response dict with ``sessions`` (list of session summary dicts) and ``total_sessions``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    # Validates the optional session_type filter against supported values.
    if session_type is not None:
        try:
            session_type_filter: SessionTypes | None = SessionTypes(session_type)
        except ValueError:
            valid = ", ".join(member.value for member in SessionTypes)
            return error_response(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
    else:
        session_type_filter = None

    # Narrows the search root to a specific project and animal when provided.
    search_root = root
    if project is not None:
        search_root = root.joinpath(project)  # type: ignore[union-attr]
        if not search_root.is_dir():
            return error_response(message=f"Project '{project}' not found at {search_root}")
        if animal_id is not None:
            search_root = search_root.joinpath(animal_id)
            if not search_root.is_dir():
                return error_response(message=f"Animal '{animal_id}' not found at {search_root}")

    # Recursively discovers session markers and applies the active filters to each summary.
    markers = sorted(search_root.rglob(RawDataFiles.SESSION_DATA))  # type: ignore[union-attr]
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

    return ok_response(sessions=sessions, total_sessions=len(sessions), root_directory=str(root))


@mcp.tool()
def discover_session_descriptors_tool(session_path: str) -> dict[str, Any]:
    """Returns the inventory of descriptor, hardware state, and configuration snapshot files present in a
    session's raw_data directory.

    Args:
        session_path: Path to the session root directory (containing the ``raw_data`` subdirectory).

    Returns:
        A response dict with ``files`` (list of name, path, and kind entries describing each YAML file found).
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error

    raw_data_dir = session_root.joinpath("raw_data")  # type: ignore[union-attr]
    if not raw_data_dir.is_dir():
        return error_response(message=f"raw_data directory not found at {raw_data_dir}")

    # Maps canonical filenames to human-readable kind labels for classification. The session descriptor
    # always lives at ``session_descriptor.yaml`` regardless of session type; the per-type descriptor
    # classes in DESCRIPTOR_REGISTRY parse the same file differently based on the session's session_type.
    known_kinds = {
        RawDataFiles.SESSION_DATA: "session_data",
        RawDataFiles.SESSION_DESCRIPTOR: "session_descriptor",
        RawDataFiles.SURGERY_METADATA: "surgery_metadata",
        RawDataFiles.SYSTEM_CONFIGURATION: "system_configuration_snapshot",
        RawDataFiles.EXPERIMENT_CONFIGURATION: "experiment_configuration_snapshot",
        RawDataFiles.HARDWARE_STATE: "hardware_state",
    }

    # Classifies each YAML file in raw_data by matching against known filenames.
    files: list[dict[str, Any]] = []
    for candidate in sorted(raw_data_dir.glob("*.yaml")):
        # noinspection PyTypeChecker
        kind = known_kinds.get(candidate.name, "unknown")
        files.append({"name": candidate.name, "path": str(candidate), "kind": kind})

    incomplete = raw_data_dir.joinpath(INCOMPLETE_SESSION_MARKER).exists()
    return ok_response(files=files, total_files=len(files), session_path=str(session_root), incomplete=incomplete)


@mcp.tool()
def discover_subjects_tool(root_directory: str, project: str | None = None) -> dict[str, Any]:
    """Discovers subjects (animals) by scanning project directories on disk.

    For each subject found on disk, attempts to locate a cached SurgeryData YAML and reports whether one was
    found. This tool is the disk-side counterpart to a future Google Sheets-backed surgery lookup.

    Args:
        root_directory: The absolute path to the root data directory to scan. Required — the
            system-configuration-based fallback has moved to the acquisition runtime package.
        project: When provided, only subjects belonging to this project are returned.

    Returns:
        A response dict with ``subjects`` (list of subject summary dicts) and ``total_subjects``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    project_paths: list[Path]
    if project is not None:
        project_path = root.joinpath(project)  # type: ignore[union-attr]
        if not project_path.is_dir():
            return error_response(message=f"Project '{project}' not found at {project_path}")
        project_paths = [project_path]
    else:
        project_paths = [child for child in safe_iterdir(directory=root) if child.is_dir()]  # type: ignore[arg-type]

    # Deduplicates subjects that appear across multiple projects, merging session counts.
    seen: dict[str, dict[str, Any]] = {}
    for project_path in project_paths:
        for animal_dir in safe_iterdir(directory=project_path):
            if not animal_dir.is_dir() or animal_dir.name == CONFIGURATION_DIR:
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
            entry["session_count"] += len(list(animal_dir.glob(f"*/raw_data/{RawDataFiles.SESSION_DATA}")))
            surgery_path, _ = _resolve_surgery_path(
                subject_id=animal_dir.name,
                project=project_path.name,
                root_directory=root_directory,
            )
            if surgery_path is not None:
                entry["has_cached_surgery_data"] = True
                entry["surgery_data_path"] = str(surgery_path)

    subjects = sorted(seen.values(), key=lambda subject: subject["subject_id"])
    return ok_response(subjects=subjects, total_subjects=len(subjects))


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
        return error_response(message=f"Failed to load SessionData: {exception}")
    incomplete = instance.raw_data_path.joinpath(INCOMPLETE_SESSION_MARKER).exists()
    return ok_response(data=serialize(value=instance), incomplete=incomplete, session_path=str(session_root))


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
        return error_response(message=f"Failed to load SessionData: {exception}")

    session_type = (
        session.session_type if isinstance(session.session_type, SessionTypes) else SessionTypes(session.session_type)
    )
    descriptor_path, descriptor_class = _find_descriptor_for_session(
        session_root=session_root,  # type: ignore[arg-type]
        session_type=session_type,
    )
    if descriptor_path is None:
        return error_response(
            message=(
                f"Could not locate a descriptor file for session_type '{session_type.value}' under "
                f"{session_root}/raw_data"
            ),
        )

    response = read_yaml(file_path=descriptor_path, validator_cls=descriptor_class)
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
    file_path = session_root.joinpath("raw_data", RawDataFiles.HARDWARE_STATE)  # type: ignore[union-attr]
    return read_yaml(file_path=file_path, validator_cls=MesoscopeHardwareState)


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
    file_path = session_root.joinpath("raw_data", RawDataFiles.EXPERIMENT_CONFIGURATION)  # type: ignore[union-attr]
    return read_yaml(file_path=file_path, validator_cls=MesoscopeExperimentConfiguration)


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
    response = read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    data = response.get("data", {})
    subject = data.get("subject") if isinstance(data, dict) else None
    if subject is None:
        return error_response(message=f"SurgeryData at {surgery_path} does not contain a subject section")
    return ok_response(data=subject, surgery_data_path=str(surgery_path))


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
    return read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]


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
    response = read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    implants = response.get("data", {}).get("implants", []) if isinstance(response.get("data"), dict) else []
    return ok_response(implants=implants, total_implants=len(implants), surgery_data_path=str(surgery_path))


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
    response = read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    injections = response.get("data", {}).get("injections", []) if isinstance(response.get("data"), dict) else []
    return ok_response(injections=injections, total_injections=len(injections), surgery_data_path=str(surgery_path))


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
    response = read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    drugs = response.get("data", {}).get("drugs") if isinstance(response.get("data"), dict) else None
    if drugs is None:
        return error_response(message=f"SurgeryData at {surgery_path} does not contain a drugs section")
    return ok_response(data=drugs, surgery_data_path=str(surgery_path))


@mcp.tool()
def read_subject_procedure_tool(subject_id: str, project: str | None = None) -> dict[str, Any]:
    """Loads the ProcedureData payload for a subject from the cached SurgeryData YAML.

    Args:
        subject_id: The unique identifier of the subject.
        project: Optional project hint to scope the surgery cache lookup.

    Returns:
        A response dict with ``data`` containing the ProcedureData payload and ``surgery_data_path``.
    """
    surgery_path, error = _resolve_surgery_path(subject_id=subject_id, project=project)
    if error is not None:
        return error
    response = read_yaml(file_path=surgery_path, validator_cls=SurgeryData)  # type: ignore[arg-type]
    if not response.get("success"):
        return response
    procedure = response.get("data", {}).get("procedure") if isinstance(response.get("data"), dict) else None
    if procedure is None:
        return error_response(message=f"SurgeryData at {surgery_path} does not contain a procedure section")
    return ok_response(data=procedure, surgery_data_path=str(surgery_path))


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
        return error_response(message=f"Failed to load SessionData: {exception}")

    session_type = (
        session.session_type if isinstance(session.session_type, SessionTypes) else SessionTypes(session.session_type)
    )
    descriptor_class = DESCRIPTOR_REGISTRY[session_type][1]
    file_path = session.session_descriptor_path
    response = write_yaml_validated(
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
    file_path = session_root.joinpath("raw_data", RawDataFiles.HARDWARE_STATE)  # type: ignore[union-attr]
    return write_yaml_validated(
        file_path=file_path,
        payload=hardware_state_payload,
        validator_cls=MesoscopeHardwareState,
        overwrite=overwrite,
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
        return ok_response(valid=False, issues=[error["error"]])

    issues: list[str] = []

    raw_data_dir = session_root.joinpath("raw_data")  # type: ignore[union-attr]
    if not raw_data_dir.is_dir():
        issues.append(f"Missing raw_data directory: {raw_data_dir}")
        return ok_response(valid=False, issues=issues, session_path=str(session_root))

    try:
        session = SessionData.load(session_path=session_root)  # type: ignore[arg-type]
    except Exception as exception:
        return ok_response(
            valid=False,
            issues=[f"Failed to load SessionData: {exception}"],
            session_path=str(session_root),
        )

    session_type = (
        session.session_type if isinstance(session.session_type, SessionTypes) else SessionTypes(session.session_type)
    )

    # Verifies that the required descriptor and configuration snapshot files are present.
    descriptor_path, _ = _find_descriptor_for_session(
        session_root=session_root,  # type: ignore[arg-type]
        session_type=session_type,
    )
    if descriptor_path is None:
        issues.append(f"Missing descriptor file for session_type '{session_type.value}'")

    if session_type == SessionTypes.MESOSCOPE_EXPERIMENT:
        experiment_snapshot = raw_data_dir.joinpath(RawDataFiles.EXPERIMENT_CONFIGURATION)
        if not experiment_snapshot.exists():
            issues.append(f"Missing experiment configuration snapshot: {experiment_snapshot}")

    system_snapshot = raw_data_dir.joinpath(RawDataFiles.SYSTEM_CONFIGURATION)
    if not system_snapshot.exists():
        issues.append(f"Missing system configuration snapshot: {system_snapshot}")

    incomplete = raw_data_dir.joinpath(INCOMPLETE_SESSION_MARKER).exists()

    summary = {
        "session_name": session.session_name,
        "project": session.project_name,
        "animal": session.animal_id,
        "session_type": session_type.value,
        "incomplete": incomplete,
    }
    return ok_response(valid=not issues, issues=issues, summary=summary, session_path=str(session_root))


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
    raw_data_dir = session_root.joinpath("raw_data")  # type: ignore[union-attr]
    if not raw_data_dir.is_dir():
        return error_response(message=f"raw_data directory not found at {raw_data_dir}")
    incomplete = raw_data_dir.joinpath(INCOMPLETE_SESSION_MARKER).exists()
    processed_data_dir = session_root.joinpath("processed_data")  # type: ignore[union-attr]
    has_processed_data = processed_data_dir.is_dir() and any(processed_data_dir.iterdir())

    if incomplete:
        status = "incomplete"
    elif has_processed_data:
        status = "processed"
    else:
        status = "acquired"

    return ok_response(
        status=status,
        incomplete=incomplete,
        has_processed_data=has_processed_data,
        session_path=str(session_root),
    )


@mcp.tool()
def get_batch_session_status_overview_tool(root_directory: str | None = None) -> dict[str, Any]:
    """Aggregates session lifecycle status across every session under the data root.

    Args:
        root_directory: The absolute path to the root data directory to scan.

    Returns:
        A response dict with ``counts`` (per-status counts), ``sessions`` (per-session status entries),
        ``total_sessions``, and ``root_directory``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    # Iterates every session marker under the root, deriving lifecycle status for each.
    counts: dict[str, int] = {"incomplete": 0, "acquired": 0, "processed": 0, "error": 0}
    sessions: list[dict[str, Any]] = []
    for marker in sorted(root.rglob(RawDataFiles.SESSION_DATA)):  # type: ignore[union-attr]
        session_root = session_root_from_marker(marker=marker)
        try:
            instance = SessionData.load(session_path=session_root)
        except Exception as exception:
            counts["error"] += 1
            sessions.append({"session_path": str(session_root), "status": "error", "error": str(exception)})
            continue
        incomplete = instance.raw_data_path.joinpath(INCOMPLETE_SESSION_MARKER).exists()
        processed_data_dir = session_root.joinpath("processed_data")
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
                "session_type": serialize(value=instance.session_type),
                "session_path": str(session_root),
                "status": status,
            }
        )

    return ok_response(counts=counts, sessions=sessions, total_sessions=len(sessions), root_directory=str(root))


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
        return error_response(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
    descriptor_class = DESCRIPTOR_REGISTRY[session_type_enum][1]
    return ok_response(
        session_type=session_type_enum.value,
        descriptor_filename=RawDataFiles.SESSION_DESCRIPTOR.value,
        schema=describe_dataclass(cls=descriptor_class),
    )


@mcp.tool()
def describe_session_hardware_state_schema_tool() -> dict[str, Any]:
    """Returns the schema for MesoscopeHardwareState.

    Returns:
        A response dict with ``hardware_state_filename`` and ``schema`` (the MesoscopeHardwareState dataclass
        schema describing every hardware parameter field and its default).
    """
    return ok_response(
        hardware_state_filename=RawDataFiles.HARDWARE_STATE,
        schema=describe_dataclass(cls=MesoscopeHardwareState),
    )


@mcp.tool()
def describe_surgery_schema_tool() -> dict[str, Any]:
    """Returns the schema for SurgeryData and its nested subclasses.

    Returns:
        A response dict with ``schema`` containing the surgery schema and ``nested_classes`` mapping each
        nested dataclass (subject, procedure, drugs, implants, and injections) to its individual schema.
    """
    schema = describe_dataclass(cls=SurgeryData)
    schema["nested_classes"] = {
        "SubjectData": describe_dataclass(cls=SubjectData),
        "ProcedureData": describe_dataclass(cls=ProcedureData),
        "DrugData": describe_dataclass(cls=DrugData),
        "ImplantData": describe_dataclass(cls=ImplantData),
        "InjectionData": describe_dataclass(cls=InjectionData),
    }
    return ok_response(schema=schema)


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
        return None, error_response(message=f"Session path does not exist: {path}")
    if path.joinpath("raw_data").is_dir():
        return path, None
    if path.name == "raw_data" and path.is_dir():
        return path.parent, None
    return None, error_response(message=f"Could not locate the raw_data directory under {path}")


def _load_session_summary(marker: Path) -> dict[str, Any]:
    """Loads a SessionData YAML and returns a flat summary dict for use in discovery responses.

    Args:
        marker: The path to the ``session_data.yaml`` marker file.

    Returns:
        A flat dict with session identity metadata, paths, and completeness status, or an error dict
        if the session could not be loaded.
    """
    session_root = session_root_from_marker(marker=marker)
    try:
        instance: SessionData = SessionData.load(session_path=session_root)
    except Exception as exception:
        return {
            "session_path": str(session_root),
            "marker": str(marker),
            "error": f"Failed to load session: {exception}",
        }
    incomplete = instance.raw_data_path.joinpath(INCOMPLETE_SESSION_MARKER).exists()
    return {
        "session_name": instance.session_name,
        "project": instance.project_name,
        "animal": instance.animal_id,
        "session_type": serialize(value=instance.session_type),
        "acquisition_system": serialize(value=instance.acquisition_system),
        "experiment_name": instance.experiment_name,
        "session_path": str(session_root),
        "raw_data_path": str(instance.raw_data_path),
        "processed_data_path": str(instance.processed_data_path),
        "incomplete": incomplete,
    }


def _find_descriptor_for_session(
    session_root: Path,
    session_type: SessionTypes,
) -> tuple[Path | None, type[YamlConfig]]:
    """Locates the session-embedded descriptor file and its parsing class for a session.

    The session-embedded descriptor always uses the canonical ``session_descriptor.yaml`` filename regardless
    of session type; the parsing class is session-type-specific and comes from ``DESCRIPTOR_REGISTRY``.

    Args:
        session_root: The session root directory containing the ``raw_data`` subdirectory.
        session_type: The session type whose descriptor class to return.

    Returns:
        A tuple of the canonical descriptor file path (or None when the file does not exist) and the
        descriptor dataclass type matching the session's type.
    """
    _, descriptor_class = DESCRIPTOR_REGISTRY[session_type]
    canonical_path = session_root.joinpath("raw_data", RawDataFiles.SESSION_DESCRIPTOR)
    return canonical_path if canonical_path.exists() else None, descriptor_class


def _resolve_surgery_path(
    subject_id: str,
    project: str | None = None,
    root_directory: str | None = None,
) -> tuple[Path | None, dict[str, Any] | None]:
    """Locates a cached SurgeryData YAML on disk for the given subject.

    Notes:
        This is a best-effort filesystem search. The library does not currently mandate a single canonical
        location for cached surgery data; this helper looks under the configured working directory and the
        caller-provided data root directory for ``surgery_data/<subject_id>.yaml`` and similar conventional
        paths. The previous fallback that read the system configuration's root directory was removed when the
        system configuration moved to the acquisition runtime package.

    Args:
        subject_id: The unique identifier of the subject whose surgery data to locate.
        project: Optional project hint that scopes the lookup to a specific project subtree.
        root_directory: Optional absolute path to the root data directory to scan.

    Returns:
        A tuple of the resolved Path and an error dict. Exactly one element is non-None.
    """
    # Builds a prioritized list of candidate paths under the working and root directories.
    candidate_paths: list[Path] = []
    candidate_filenames = (f"{subject_id}.yaml", f"{subject_id}_surgery.yaml", "surgery_data.yaml")

    try:
        working_directory = get_working_directory()
        candidate_paths.extend(working_directory.joinpath("surgery_data", filename) for filename in candidate_filenames)
        candidate_paths.extend(working_directory.joinpath(filename) for filename in candidate_filenames)
    except OSError, ValueError:
        pass

    if root_directory is not None:
        root = Path(root_directory)
        if project is not None:
            candidate_paths.extend(root.joinpath(project, "surgery_data", filename) for filename in candidate_filenames)
            candidate_paths.extend(root.joinpath(project, subject_id, filename) for filename in candidate_filenames)
        candidate_paths.extend(root.joinpath("surgery_data", filename) for filename in candidate_filenames)

    # Returns the first candidate path that exists on disk.
    for candidate in candidate_paths:
        if candidate.exists():
            return candidate, None

    return None, error_response(
        message=(
            f"Could not locate a cached SurgeryData file for subject '{subject_id}'. Searched under the working "
            f"directory and the provided root directory using conventional paths "
            f"({', '.join(candidate_filenames)})."
        ),
    )
