"""Provides MCP tools for discovering, reading, writing, and validating runtime data assets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig

from .mcp_instance import (
    CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY,
    HARDWARE_STATE_REGISTRY,
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
    filter_sessions,
    session_root_from_marker,
)
from ..configuration import AcquisitionSystems


@mcp.tool()
def discover_projects_tool(root_directory: str) -> dict[str, Any]:
    """Lists all projects accessible to the data acquisition system.

    Scans the immediate children of the data root for project directories, returning each project's name and
    aggregate counts (animals and experiment configurations).

    Args:
        root_directory: The absolute path to the root data directory to scan.

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
        configuration_directory = child.joinpath(CONFIGURATION_DIR)
        experiment_count = len(list(configuration_directory.glob("*.yaml"))) if configuration_directory.is_dir() else 0
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
def discover_animals_tool(root_directory: str, project: str | None = None) -> dict[str, Any]:
    """Discovers animals under the data root, optionally scoped to a single project.

    When ``project`` is ``None``, walks every project directory under the root and deduplicates
    animals that appear in multiple projects into a single entry, aggregating session counts and
    per-project directory paths across each project the animal is enrolled in. When ``project``
    is provided, narrows the search to that project subtree; each animal then has exactly one
    entry in ``projects`` and ``paths``.

    Args:
        root_directory: The absolute path to the root data directory to scan.
        project: When provided, narrows the search to the given project subtree. A missing
            project directory returns an error response.

    Returns:
        A response dict with ``animals`` (list of ``{animal_id, projects, paths, session_count}``
        dicts, where ``projects`` and ``paths`` are aligned per-index lists of the projects the
        animal appears in and the animal directory path within each) and ``total_animals``. When
        ``project`` is provided, the response also echoes the ``project`` field.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    if project is not None:
        project_path = root.joinpath(project)  # type: ignore[union-attr]
        if not project_path.is_dir():
            return error_response(message=f"Project '{project}' not found at {project_path}")
        project_paths: list[Path] = [project_path]
    else:
        project_paths = [child for child in safe_iterdir(directory=root) if child.is_dir()]  # type: ignore[arg-type]

    # Deduplicates animals across projects, merging project membership, per-project directory paths,
    # and session counts into a single entry per animal_id.
    seen: dict[str, dict[str, Any]] = {}
    for project_path in project_paths:
        for animal_directory in safe_iterdir(directory=project_path):
            if not animal_directory.is_dir() or animal_directory.name == CONFIGURATION_DIR:
                continue
            entry = seen.setdefault(
                animal_directory.name,
                {
                    "animal_id": animal_directory.name,
                    "projects": [],
                    "paths": [],
                    "session_count": 0,
                },
            )
            if project_path.name not in entry["projects"]:
                entry["projects"].append(project_path.name)
                entry["paths"].append(str(animal_directory))
            entry["session_count"] += len(list(animal_directory.glob(f"*/raw_data/{RawDataFiles.SESSION_DATA}")))

    animals = sorted(seen.values(), key=lambda candidate: candidate["animal_id"])
    response = ok_response(animals=animals, total_animals=len(animals))
    if project is not None:
        response["project"] = project
    return response


@mcp.tool()
def discover_sessions_tool(
    root_directory: str,
    project: str | None = None,
    animal_id: str | None = None,
    session_types: list[str] | None = None,
) -> dict[str, Any]:
    """Recursively discovers all sessions under the data root and classifies eligibility by session type.

    Walks the directory tree looking for ``session_data.yaml`` markers and returns a flat list of
    session summaries plus a ``session_paths`` list of eligible session roots ready to hand off to
    downstream batch tools (e.g. forgery's ``prepare_*_batch_tool`` family). The optional ``project``
    and ``animal_id`` arguments narrow the directory tree that is searched; ``session_types`` acts as
    an eligibility filter that classifies every discovered session without removing it from the
    response, so agents can still see ineligible or broken sessions for diagnosis.

    Args:
        root_directory: The absolute path to the root data directory to scan.
        project: When provided, narrows the search to the given project subtree. A missing project
            directory returns an error response.
        animal_id: When provided (with ``project``), narrows the search to the given animal subtree.
            Ignored when ``project`` is ``None``.
        session_types: An optional list of session type strings to classify sessions against. When
            provided, each session entry includes ``eligible=True`` only if its type is in the list,
            and ``session_paths`` contains only eligible roots. When omitted, every discovered session
            is eligible. Must contain only valid ``SessionTypes`` values.

    Returns:
        A response dict with ``sessions`` (list of per-session summary dicts each including an
        ``eligible`` flag), ``session_paths`` (flat list of eligible session root paths),
        ``total_sessions``, ``total_eligible``, and ``root_directory``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    # Validates the optional session_types eligibility filter against the supported values.
    types_filter: frozenset[SessionTypes] | None = None
    if session_types is not None:
        try:
            types_filter = frozenset(SessionTypes(candidate) for candidate in session_types)
        except ValueError as exception:
            valid = ", ".join(member.value for member in SessionTypes)
            return error_response(message=f"Invalid session type in filter: {exception}. Valid values: {valid}")

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

    # Recursively discovers session markers and classifies each summary against the eligibility filter.
    markers = sorted(search_root.rglob(RawDataFiles.SESSION_DATA))  # type: ignore[union-attr]
    sessions: list[dict[str, Any]] = []
    eligible_paths: list[str] = []
    for marker in markers:
        summary = _load_session_summary(marker=marker)
        if "error" in summary:
            summary["eligible"] = False
            sessions.append(summary)
            continue

        if types_filter is None:
            eligible = True
        else:
            try:
                eligible = SessionTypes(summary["session_type"]) in types_filter
            except ValueError:
                eligible = False
        summary["eligible"] = eligible

        if eligible:
            eligible_paths.append(summary["session_path"])

        sessions.append(summary)

    return ok_response(
        sessions=sessions,
        session_paths=eligible_paths,
        total_sessions=len(sessions),
        total_eligible=len(eligible_paths),
        root_directory=str(root),
    )


@mcp.tool()
def filter_sessions_tool(
    sessions: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
    include_sessions: list[str] | None = None,
    exclude_sessions: list[str] | None = None,
    include_animals: list[str] | None = None,
    exclude_animals: list[str] | None = None,
    *,
    utc_timezone: bool = True,
) -> dict[str, Any]:
    """Filters a list of session entries by date range and inclusion-exclusion criteria.

    Designed for agentic chaining with ``discover_sessions_tool``: accepts the ``sessions`` list from
    its output and returns a filtered subset with the same structure. Each input entry must contain
    ``session_name`` and ``animal`` keys (matching the shape produced by ``discover_sessions_tool``).
    Animal filtering is applied before session filtering and exclusion always takes precedence over
    inclusion.

    Args:
        sessions: A list of session entry dictionaries, each containing at least ``session_name`` and
            ``animal`` keys. Typically, the ``sessions`` list returned by ``discover_sessions_tool``.
        start_date: Sessions recorded on or after this date are included. Accepts formats like
            ``YYYY-MM-DD`` or ``YYYY-MM-DD HH:MM:SS``. When ``None``, no start bound is applied.
        end_date: Sessions recorded on or before this date are included. Date-only values include the
            entire day. When ``None``, no end bound is applied.
        include_sessions: Session names to include regardless of the date range, unless overridden by
            ``exclude_sessions``.
        exclude_sessions: Session names to exclude from the results. Takes precedence over all other
            inclusion criteria.
        include_animals: Animal identifiers to include. When provided, only sessions from these
            animals are considered.
        exclude_animals: Animal identifiers to exclude. Takes precedence over ``include_animals``.
        utc_timezone: Determines whether to interpret date boundaries and session timestamps in UTC.
            When ``False``, uses America/New_York.

    Returns:
        A response dict with a filtered ``sessions`` list, a ``session_paths`` list of eligible
        session roots from the filtered subset, and ``total_sessions`` / ``total_eligible`` counts.
        Structurally identical to ``discover_sessions_tool`` output for downstream chaining. An
        ``invalid_entries`` key appears when input entries lack the required ``session_name`` /
        ``animal`` fields.
    """
    # Builds a (session_name, animal) tuple set and a reverse map from session name to the original
    # entry so the filter helper can operate on plain tuples and results can be rehydrated to dicts.
    session_keys: set[tuple[str, str]] = set()
    session_map: dict[str, dict[str, Any]] = {}
    invalid_entries: list[dict[str, Any]] = []

    for entry in sessions:
        session_name = entry.get("session_name")
        animal = entry.get("animal")

        if session_name is None or animal is None:
            invalid_entries.append({**entry, "filter_error": "Missing required 'session_name' or 'animal' field."})
            continue

        session_keys.add((str(session_name), str(animal)))
        session_map[str(session_name)] = entry

    filtered = filter_sessions(
        sessions=session_keys,
        start_date=start_date,
        end_date=end_date,
        include_sessions=set(include_sessions) if include_sessions else None,
        exclude_sessions=set(exclude_sessions) if exclude_sessions else None,
        include_animals=set(include_animals) if include_animals else None,
        exclude_animals=set(exclude_animals) if exclude_animals else None,
        utc_timezone=utc_timezone,
    )

    # Rehydrates filtered tuples back to the original entry dictionaries and recomputes session_paths
    # from the filtered subset.
    filtered_entries = sorted(
        (session_map[session_name] for session_name, _ in filtered if session_name in session_map),
        key=lambda filtered_entry: filtered_entry.get("session_name", ""),
    )

    eligible_paths = sorted(
        entry["session_path"] for entry in filtered_entries if entry.get("eligible", True) and "session_path" in entry
    )

    response: dict[str, Any] = ok_response(
        sessions=filtered_entries,
        session_paths=eligible_paths,
        total_sessions=len(filtered_entries),
        total_eligible=len(eligible_paths),
    )

    if invalid_entries:
        response["invalid_entries"] = invalid_entries

    return response


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

    raw_data_directory = session_root.joinpath("raw_data")  # type: ignore[union-attr]
    if not raw_data_directory.is_dir():
        return error_response(message=f"raw_data directory not found at {raw_data_directory}")

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
    for candidate in sorted(raw_data_directory.glob("*.yaml")):
        # noinspection PyTypeChecker
        kind = known_kinds.get(candidate.name, "unknown")
        files.append({"name": candidate.name, "path": str(candidate), "kind": kind})

    uninitialized = raw_data_directory.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
    return ok_response(
        files=files,
        total_files=len(files),
        session_path=str(session_root),
        uninitialized=uninitialized,
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

    raw_data_directory = session_root.joinpath("raw_data")  # type: ignore[union-attr]
    if not raw_data_directory.is_dir():
        issues.append(f"Missing raw_data directory: {raw_data_directory}")
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
    descriptor_path = raw_data_directory.joinpath(RawDataFiles.SESSION_DESCRIPTOR)
    if not descriptor_path.exists():
        issues.append(f"Missing descriptor file: {descriptor_path}")

    if session_type == SessionTypes.MESOSCOPE_EXPERIMENT:
        experiment_snapshot = raw_data_directory.joinpath(RawDataFiles.EXPERIMENT_CONFIGURATION)
        if not experiment_snapshot.exists():
            issues.append(f"Missing experiment configuration snapshot: {experiment_snapshot}")

    system_snapshot = raw_data_directory.joinpath(RawDataFiles.SYSTEM_CONFIGURATION)
    if not system_snapshot.exists():
        issues.append(f"Missing system configuration snapshot: {system_snapshot}")

    uninitialized = raw_data_directory.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
    descriptor_incomplete, _descriptor_error = read_descriptor_incomplete(session=session)

    summary = {
        "session_name": session.session_name,
        "project": session.project_name,
        "animal": session.animal_id,
        "session_type": session_type.value,
        "uninitialized": uninitialized,
        "incomplete": descriptor_incomplete,
    }
    return ok_response(valid=not issues, issues=issues, summary=summary, session_path=str(session_root))


@mcp.tool()
def get_session_status_tool(session_path: str) -> dict[str, Any]:
    """Returns lifecycle status for a single session.

    Inspects three independent signals to derive the high-level state. The presence of the
    ``nk.bin`` marker under ``raw_data/`` indicates that the acquisition runtime has not yet
    finished initializing the session; in that case the data is not valid, the session is a
    trash target (``uninitialized``), and no further checks are meaningful. The ``incomplete``
    field on the session's descriptor YAML is true when the session ran but encountered a
    runtime issue that may have left data gaps, in which case the session still holds real
    data and should be reviewed manually rather than skipped; this signal is independent of
    ``uninitialized``. The population of ``processed_data/`` indicates that downstream
    processing has started or completed when any files exist there. The ``status`` field is
    a coarse projection with priority ``uninitialized`` > ``error`` > ``incomplete`` >
    ``processed`` > ``acquired``, and the individual boolean and nullable flags are also
    returned so callers can compose their own logic.

    Args:
        session_path: Path to the session root directory.

    Returns:
        A response dict with ``status``, ``uninitialized`` (bool), ``incomplete`` (bool or None
        when the descriptor could not be read), ``has_processed_data``, ``session_path``, and an
        optional ``error_detail`` when ``status`` is ``"error"``.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    raw_data_directory = session_root.joinpath("raw_data")  # type: ignore[union-attr]
    if not raw_data_directory.is_dir():
        return error_response(message=f"raw_data directory not found at {raw_data_directory}")

    uninitialized = raw_data_directory.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
    processed_data_directory = session_root.joinpath("processed_data")  # type: ignore[union-attr]
    has_processed_data = processed_data_directory.is_dir() and any(processed_data_directory.iterdir())

    # Skips the descriptor load for uninitialized sessions because their descriptor is never meaningful.
    if uninitialized:
        return ok_response(
            status="uninitialized",
            uninitialized=True,
            incomplete=None,
            has_processed_data=has_processed_data,
            session_path=str(session_root),
        )

    try:
        session = SessionData.load(session_path=session_root)  # type: ignore[arg-type]
    except Exception as exception:
        return ok_response(
            status="error",
            uninitialized=False,
            incomplete=None,
            has_processed_data=has_processed_data,
            session_path=str(session_root),
            error_detail=f"Failed to load SessionData: {exception}",
        )

    descriptor_incomplete, descriptor_error = read_descriptor_incomplete(session=session)
    if descriptor_incomplete is None:
        return ok_response(
            status="error",
            uninitialized=False,
            incomplete=None,
            has_processed_data=has_processed_data,
            session_path=str(session_root),
            error_detail=descriptor_error,
        )

    if descriptor_incomplete:
        status = "incomplete"
    elif has_processed_data:
        status = "processed"
    else:
        status = "acquired"

    return ok_response(
        status=status,
        uninitialized=False,
        incomplete=descriptor_incomplete,
        has_processed_data=has_processed_data,
        session_path=str(session_root),
    )


@mcp.tool()
def get_batch_session_status_overview_tool(root_directory: str) -> dict[str, Any]:
    """Aggregates session lifecycle status across every session under the data root.

    Uses the same two-signal model as ``get_session_status_tool``: the ``nk.bin`` uninitialized
    marker and the descriptor's ``incomplete`` field. Status values are ``uninitialized``,
    ``incomplete``, ``acquired``, ``processed``, and ``error``.

    Args:
        root_directory: The absolute path to the root data directory to scan.

    Returns:
        A response dict with ``counts`` (a dict with keys ``uninitialized``, ``incomplete``,
        ``acquired``, ``processed``, ``error``), ``sessions`` (per-session entries each carrying
        ``status``, ``uninitialized``, ``incomplete``, ``has_processed_data``), ``total_sessions``,
        and ``root_directory``.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    # Iterates every session marker under the root and classifies each using the same two-signal model
    # as ``get_session_status_tool``: the ``nk.bin`` marker (uninitialized) and the descriptor's
    # ``incomplete`` field (incomplete-but-real).
    counts: dict[str, int] = {
        "uninitialized": 0,
        "incomplete": 0,
        "acquired": 0,
        "processed": 0,
        "error": 0,
    }
    sessions: list[dict[str, Any]] = []
    for marker in sorted(root.rglob(RawDataFiles.SESSION_DATA)):  # type: ignore[union-attr]
        session_root = session_root_from_marker(marker=marker)
        try:
            instance = SessionData.load(session_path=session_root)
        except Exception as exception:
            counts["error"] += 1
            sessions.append({"session_path": str(session_root), "status": "error", "error": str(exception)})
            continue

        uninitialized = instance.raw_data_path.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
        processed_data_directory = session_root.joinpath("processed_data")
        has_processed_data = processed_data_directory.is_dir() and any(processed_data_directory.iterdir())

        if uninitialized:
            status = "uninitialized"
            descriptor_incomplete: bool | None = None
        else:
            descriptor_incomplete, _descriptor_error = read_descriptor_incomplete(session=instance)
            if descriptor_incomplete is None:
                status = "error"
            elif descriptor_incomplete:
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
                "uninitialized": uninitialized,
                "incomplete": descriptor_incomplete,
                "has_processed_data": has_processed_data,
            }
        )

    return ok_response(counts=counts, sessions=sessions, total_sessions=len(sessions), root_directory=str(root))


@mcp.tool()
def read_session_data_tool(session_path: str) -> dict[str, Any]:
    """Loads the SessionData YAML for a session.

    ``SessionData`` is the session's identity marker (the file whose presence promotes a directory
    into a Sollertia session), so this tool is scoped at the session level. For per-asset reads
    (descriptors, hardware state, surgery metadata, frozen experiment configuration) use the
    file-path-based read tools.

    Args:
        session_path: Path to the session root directory (or its ``raw_data`` subdirectory).

    Returns:
        A response dict with ``data`` (the full SessionData payload) and ``uninitialized`` (True when
        the ``nk.bin`` marker is still present, i.e. the acquisition runtime has not yet finished
        initializing the session and its data is not considered valid). To check whether the session
        ran into issues during acquisition (the descriptor ``incomplete`` field), call
        ``read_session_descriptor_tool`` or ``get_session_status_tool``.
    """
    session_root, error = _resolve_session_root(session_path=session_path)
    if error is not None:
        return error
    try:
        instance = SessionData.load(session_path=session_root)  # type: ignore[arg-type]
    except Exception as exception:
        return error_response(message=f"Failed to load SessionData: {exception}")
    uninitialized = instance.raw_data_path.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
    return ok_response(
        data=serialize(value=instance),
        uninitialized=uninitialized,
        session_path=str(session_root),
    )


@mcp.tool()
def read_session_descriptor_tool(file_path: str, session_type: str) -> dict[str, Any]:
    """Loads a session descriptor YAML, parsing it with the dataclass that matches ``session_type``.

    The descriptor filename is always ``session_descriptor.yaml`` regardless of session type — only the
    parsing class varies. The caller must supply ``session_type`` because the file path alone does not
    disambiguate which descriptor class to instantiate; use ``list_supported_session_types_tool`` to
    enumerate the valid values.

    Args:
        file_path: Absolute path to the descriptor YAML file. Canonical location is
            ``<session>/raw_data/session_descriptor.yaml``.
        session_type: The ``SessionTypes`` value identifying which descriptor dataclass to use
            (``lick training``, ``run training``, ``mesoscope experiment``, or ``window checking``).

    Returns:
        A response dict with ``data`` (the descriptor payload), ``descriptor_class``, ``session_type``,
        and ``file_path``.
    """
    try:
        session_type_enum = SessionTypes(session_type)
    except ValueError:
        valid = ", ".join(member.value for member in SessionTypes)
        return error_response(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
    descriptor_class = DESCRIPTOR_REGISTRY[session_type_enum]
    response = read_yaml(file_path=Path(file_path), validator_cls=descriptor_class)
    if response.get("success"):
        response["descriptor_class"] = descriptor_class.__name__
        response["session_type"] = session_type_enum.value
    return response


@mcp.tool()
def write_session_descriptor_tool(
    file_path: str,
    session_type: str,
    descriptor_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Creates or replaces a session descriptor YAML.

    Validates ``descriptor_payload`` against the descriptor dataclass that matches ``session_type`` and
    writes the result to ``file_path``. The caller is responsible for choosing the destination path;
    canonical location is ``<session>/raw_data/session_descriptor.yaml``.

    Args:
        file_path: Absolute path to the destination descriptor YAML file.
        session_type: The ``SessionTypes`` value identifying which descriptor dataclass to validate
            against (``lick training``, ``run training``, ``mesoscope experiment``, or
            ``window checking``).
        descriptor_payload: The complete descriptor payload matching the appropriate descriptor schema.
        overwrite: Determines whether to overwrite an existing descriptor file.

    Returns:
        A response dict with ``file_path``, ``data`` (the validated payload), ``descriptor_class``,
        and ``session_type``.
    """
    try:
        session_type_enum = SessionTypes(session_type)
    except ValueError:
        valid = ", ".join(member.value for member in SessionTypes)
        return error_response(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
    descriptor_class = DESCRIPTOR_REGISTRY[session_type_enum]
    response = write_yaml_validated(
        file_path=Path(file_path),
        payload=descriptor_payload,
        validator_cls=descriptor_class,
        overwrite=overwrite,
    )
    if response.get("success"):
        response["descriptor_class"] = descriptor_class.__name__
        response["session_type"] = session_type_enum.value
    return response


@mcp.tool()
def describe_session_descriptor_schema_tool(session_type: str) -> dict[str, Any]:
    """Returns the schema for the descriptor associated with a given session type.

    The descriptor always lives at the canonical ``<session>/raw_data/session_descriptor.yaml``
    path regardless of session type; only the parsing class varies.

    Args:
        session_type: The SessionTypes value to describe.

    Returns:
        A response dict with ``session_type`` (the validated enum value) and ``schema`` (the
        descriptor dataclass field schema).
    """
    try:
        session_type_enum = SessionTypes(session_type)
    except ValueError:
        valid = ", ".join(member.value for member in SessionTypes)
        return error_response(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
    descriptor_class = DESCRIPTOR_REGISTRY[session_type_enum]
    return ok_response(
        session_type=session_type_enum.value,
        schema=describe_dataclass(cls=descriptor_class),
    )


@mcp.tool()
def read_session_hardware_state_tool(file_path: str, acquisition_system: str) -> dict[str, Any]:
    """Loads a hardware-state YAML, parsing it with the dataclass that matches ``acquisition_system``.

    The hardware-state filename is always ``hardware_state.yaml`` regardless of acquisition system —
    only the parsing class varies. The caller must supply ``acquisition_system`` because the file
    path alone does not disambiguate which hardware-state class to instantiate; use
    ``list_supported_acquisition_systems_tool`` to enumerate the valid values.

    Args:
        file_path: Absolute path to the hardware-state YAML file. Canonical location is
            ``<session>/raw_data/hardware_state.yaml``.
        acquisition_system: The ``AcquisitionSystems`` value identifying which hardware-state
            dataclass to use. Today only ``mesoscope`` is registered; future systems join
            ``HARDWARE_STATE_REGISTRY``.

    Returns:
        A response dict with ``data`` (the hardware-state payload), ``hardware_state_class``,
        ``acquisition_system``, and ``file_path``.
    """
    resolved = _resolve_hardware_state_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    response = read_yaml(file_path=Path(file_path), validator_cls=resolved)
    if response.get("success"):
        response["hardware_state_class"] = resolved.__name__
        response["acquisition_system"] = acquisition_system
    return response


@mcp.tool()
def write_session_hardware_state_tool(
    file_path: str,
    acquisition_system: str,
    hardware_state_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Creates or replaces a hardware-state YAML.

    Validates ``hardware_state_payload`` against the hardware-state dataclass that matches
    ``acquisition_system`` and writes the result to ``file_path``. Use
    ``list_supported_acquisition_systems_tool`` to enumerate the valid values.

    Args:
        file_path: Absolute path to the destination hardware-state YAML file. Canonical location is
            ``<session>/raw_data/hardware_state.yaml``.
        acquisition_system: The ``AcquisitionSystems`` value identifying which hardware-state
            dataclass to validate against.
        hardware_state_payload: The complete hardware-state payload.
        overwrite: Determines whether to overwrite an existing hardware state file.

    Returns:
        A response dict with ``file_path``, ``data`` (the validated payload), ``hardware_state_class``,
        and ``acquisition_system``.
    """
    resolved = _resolve_hardware_state_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    response = write_yaml_validated(
        file_path=Path(file_path),
        payload=hardware_state_payload,
        validator_cls=resolved,
        overwrite=overwrite,
    )
    if response.get("success"):
        response["hardware_state_class"] = resolved.__name__
        response["acquisition_system"] = acquisition_system
    return response


@mcp.tool()
def describe_session_hardware_state_schema_tool(acquisition_system: str = "mesoscope") -> dict[str, Any]:
    """Returns the schema for the hardware-state dataclass of a given acquisition system.

    The hardware-state snapshot always lives at the canonical
    ``<session>/raw_data/hardware_state.yaml`` path regardless of acquisition system; only the
    parsing class varies.

    Args:
        acquisition_system: The ``AcquisitionSystems`` value to describe. Defaults to ``"mesoscope"``.

    Returns:
        A response dict with ``acquisition_system`` (the validated enum value) and ``schema``
        (the hardware-state dataclass field schema).
    """
    resolved = _resolve_hardware_state_class(acquisition_system=acquisition_system)
    if isinstance(resolved, dict):
        return resolved
    return ok_response(
        acquisition_system=acquisition_system,
        schema=describe_dataclass(cls=resolved),
    )


@mcp.tool()
def read_surgery_data_tool(file_path: str) -> dict[str, Any]:
    """Loads the full SurgeryData payload from a per-session surgery-metadata snapshot.

    The returned payload is the whole YAML — callers extract the ``subject``, ``procedure``, ``drugs``,
    ``implants``, or ``injections`` sections themselves. Surgery metadata is treated as a single
    monolithic record; there are no per-section MCP tools.

    Args:
        file_path: Absolute path to the surgery-metadata YAML file. Canonical location is
            ``<session>/raw_data/surgery_metadata.yaml``.

    Returns:
        A response dict with ``data`` containing the full SurgeryData payload (subject, procedure,
        drugs, implants, and injections sections).
    """
    return read_yaml(file_path=Path(file_path), validator_cls=SurgeryData)


@mcp.tool()
def write_surgery_data_tool(
    file_path: str,
    surgery_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Creates or replaces a per-session surgery-metadata YAML.

    Validates ``surgery_payload`` against the full ``SurgeryData`` schema and writes the result to
    ``file_path``. Surgery metadata is a single monolithic record; the payload must contain all
    sections (``subject``, ``procedure``, ``drugs``, ``implants``, and ``injections``).

    Args:
        file_path: Absolute path to the destination surgery-metadata YAML file. Canonical location is
            ``<session>/raw_data/surgery_metadata.yaml``.
        surgery_payload: The complete SurgeryData payload.
        overwrite: Determines whether to overwrite an existing surgery-metadata file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated payload).
    """
    return write_yaml_validated(
        file_path=Path(file_path),
        payload=surgery_payload,
        validator_cls=SurgeryData,
        overwrite=overwrite,
    )


@mcp.tool()
def describe_surgery_data_schema_tool() -> dict[str, Any]:
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


def _resolve_hardware_state_class(acquisition_system: str) -> type[YamlConfig] | dict[str, Any]:
    """Resolves an ``acquisition_system`` string to its registered hardware-state dataclass.

    Validates the value against the ``AcquisitionSystems`` enum and then looks up the corresponding
    class in ``HARDWARE_STATE_REGISTRY``. Returns an error response dict when the value is not a
    valid acquisition system or when no hardware-state class has been registered for that system yet.

    Args:
        acquisition_system: The ``AcquisitionSystems`` value supplied by the caller.

    Returns:
        The resolved hardware-state dataclass on success, or an error response dict on failure.
        Callers discriminate via ``isinstance(result, dict)``.
    """
    try:
        acquisition_enum = AcquisitionSystems(acquisition_system)
    except ValueError:
        valid = ", ".join(member.value for member in AcquisitionSystems)
        return error_response(
            message=f"Invalid acquisition_system '{acquisition_system}'. Valid values: {valid}"
        )
    hardware_state_class = HARDWARE_STATE_REGISTRY.get(acquisition_enum)
    if hardware_state_class is None:
        registered = ", ".join(member.value for member in HARDWARE_STATE_REGISTRY)
        return error_response(
            message=f"No hardware-state class registered for '{acquisition_system}'. Registered: {registered}"
        )
    return hardware_state_class


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
    uninitialized = instance.raw_data_path.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
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
        "uninitialized": uninitialized,
    }
