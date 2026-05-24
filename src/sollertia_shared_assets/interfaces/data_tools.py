"""Provides MCP tools for discovering, reading, writing, and validating runtime data assets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path
from dataclasses import fields, dataclass

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig

from .mcp_instance import (
    CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY,
    DATASET_MARKER_FILENAME,
    HARDWARE_STATE_REGISTRY,
    mcp,
    read_yaml,
    serialize,
    ok_response,
    error_response,
    describe_dataclass,
    write_yaml_validated,
    resolve_root_directory,
    read_descriptor_incomplete,
)
from ..data_classes import (
    RAW_DATA_DIRECTORY,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    RawDataFiles,
    SessionTypes,
    InjectionData,
    ProcedureData,
    ProcessingTrackers,
    filter_sessions,
    get_session_root_from_marker,
)
from ..configuration import AcquisitionSystems

_STATUS_KEYS: tuple[str, ...] = ("uninitialized", "incomplete", "acquired", "processed", "error")
"""Canonical lifecycle status keys used in ``counts`` dicts across the overview and inspection tools."""


@dataclass(frozen=True, slots=True)
class _SessionStatusInfo:
    """Carries the lifecycle-status signals computed from a loaded ``SessionData`` instance."""

    status: str
    """The coarse lifecycle status; one of the values in ``_STATUS_KEYS``."""
    uninitialized: bool
    """Indicates whether the ``nk.bin`` uninitialized marker is present in the session's raw_data."""
    incomplete: bool | None
    """The descriptor's ``incomplete`` field, or None when the session is uninitialized or the descriptor
    read failed."""
    has_processed_data: bool
    """Indicates whether the session's ``processed_data`` directory exists and is non-empty."""
    error_detail: str | None
    """Human-readable detail when the descriptor read failed, otherwise None."""


@mcp.tool()
def get_data_root_overview_tool(root_directory: str) -> dict[str, Any]:
    """Walks the data root and groups loadable ``session_data.yaml`` markers into a project / animal / session tree.

    Sessions are bucketed by their SessionData identity fields, not by directory structure, so stray
    directories cannot surface as phantom projects. Markers that fail to load appear in the flat
    ``sessions`` list with ``status="error"`` and an ``error_detail`` field, but do not contribute to
    project or animal aggregation.

    Args:
        root_directory: Absolute path to the data root to scan.

    Returns:
        A response dict with top-level keys ``projects``, ``sessions``, ``counts``, ``total_projects``,
        ``total_animals``, ``total_sessions``, and ``root_directory``. Each ``projects`` entry carries
        ``name``, ``path``, ``animals``, ``session_count``, ``counts``, ``sessions_by_type``,
        ``experiment_count``, and ``dataset_count``. Each animals entry carries ``id``, ``session_paths``,
        ``session_count``, and ``counts``. The ``sessions`` list holds flat per-session entries suitable
        for chaining into ``filter_sessions_tool``. The top-level ``counts`` mapping holds the
        cross-project status tally, including errors.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error

    flat_sessions: list[dict[str, Any]] = []
    top_counts: dict[str, int] = dict.fromkeys(_STATUS_KEYS, 0)

    # Walks every session marker under the root. Broken markers produce error-status entries but do
    # not corrupt the project / animal aggregation because their identity cannot be trusted.
    markers = sorted(root.rglob(RawDataFiles.SESSION_DATA))  # type: ignore[union-attr]
    for marker in markers:
        session_root = get_session_root_from_marker(marker=marker)
        try:
            instance = SessionData.load(session_path=session_root)
        except Exception as exception:
            flat_sessions.append(
                {
                    "session_path": str(session_root),
                    "marker": str(marker),
                    "status": "error",
                    "error_detail": f"Failed to load SessionData: {exception}",
                }
            )
            top_counts["error"] += 1
            continue

        status_info = _compute_session_status(instance=instance)
        entry: dict[str, Any] = {
            "session_name": instance.session_name,
            "project": instance.project_name,
            "animal": instance.animal_id,
            "session_type": serialize(value=instance.session_type),
            "acquisition_system": serialize(value=instance.acquisition_system),
            "experiment_name": instance.experiment_name,
            "session_path": str(session_root),
            "raw_data_path": str(instance.raw_data_path),
            "processed_data_path": str(instance.processed_data_path),
            "status": status_info.status,
            "uninitialized": status_info.uninitialized,
            "incomplete": status_info.incomplete,
            "has_processed_data": status_info.has_processed_data,
        }
        if status_info.error_detail is not None:
            entry["error_detail"] = status_info.error_detail
        flat_sessions.append(entry)
        top_counts[status_info.status] += 1

    projects = _aggregate_projects(root=root, sessions=flat_sessions)  # type: ignore[arg-type]

    for project in projects:
        experiment_count, dataset_count = _count_project_artifacts(project_path=Path(project["path"]))
        project["experiment_count"] = experiment_count
        project["dataset_count"] = dataset_count

    total_animals = sum(len(project["animals"]) for project in projects)

    return ok_response(
        projects=projects,
        sessions=flat_sessions,
        counts=top_counts,
        total_projects=len(projects),
        total_animals=total_animals,
        total_sessions=len(flat_sessions),
        root_directory=str(root),
    )


@mcp.tool()
def inspect_sessions_tool(session_paths: list[str]) -> dict[str, Any]:
    """Produces a per-session health and inventory report for each supplied session path.

    Each report carries lifecycle status, an existence flag for every canonical ``raw_data`` file and
    every ``processed_data`` subdirectory (with paired processing-tracker presence), and a
    ``required_assets`` check (descriptor and system configuration always required; experiment
    configuration also required for ``mesoscope experiment`` sessions). Paths that fail to resolve
    or load surface with ``status="error"`` and an ``error_detail`` field without aborting the batch.

    Args:
        session_paths: Absolute paths to session roots or their ``raw_data`` subdirectories. Pass a
            single-element list to inspect one session.

    Returns:
        A response dict with ``sessions`` (per-session report dicts), ``total_sessions``, and
        ``counts`` (status tally across the batch).
    """
    reports: list[dict[str, Any]] = []
    counts: dict[str, int] = dict.fromkeys(_STATUS_KEYS, 0)

    for raw_path in session_paths:
        session_root, resolve_error = _resolve_session_root(session_path=raw_path)
        if resolve_error is not None or session_root is None:
            reports.append(
                {
                    "session_path": raw_path,
                    "status": "error",
                    "error_detail": resolve_error["error"] if resolve_error is not None else "Unresolved session path",
                }
            )
            counts["error"] += 1
            continue

        try:
            instance = SessionData.load(session_path=session_root)
        except Exception as exception:
            reports.append(
                {
                    "session_path": str(session_root),
                    "status": "error",
                    "error_detail": f"Failed to load SessionData: {exception}",
                }
            )
            counts["error"] += 1
            continue

        report = _build_session_report(instance=instance, session_root=session_root)
        reports.append(report)
        counts[report["status"]] += 1

    return ok_response(sessions=reports, total_sessions=len(reports), counts=counts)


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

    Designed to chain after ``get_data_root_overview_tool``: pass its ``sessions`` list and receive
    a filtered subset with the same structure. Animal filters apply before session filters;
    exclusions take precedence over inclusions.

    Args:
        sessions: Session entry dictionaries, each containing at least ``session_name`` and
            ``animal`` keys. Typically the ``sessions`` list returned by ``get_data_root_overview_tool``.
        start_date: Lower bound (inclusive). Accepts ``YYYY-MM-DD`` or ``YYYY-MM-DD HH:MM:SS``.
            None disables the lower bound.
        end_date: Upper bound (inclusive). Date-only values include the entire day. None disables
            the upper bound.
        include_sessions: Session names to include regardless of the date range, unless overridden
            by ``exclude_sessions``.
        exclude_sessions: Session names to exclude. Takes precedence over all inclusion criteria.
        include_animals: When provided, only sessions from these animal IDs are considered.
        exclude_animals: Animal IDs to exclude. Takes precedence over ``include_animals``.
        utc_timezone: Determines whether to interpret date boundaries and session timestamps in UTC;
            falls back to the host machine's local time when False.

    Returns:
        A response dict with the filtered ``sessions`` list, a ``session_paths`` list of eligible
        session roots from the filtered subset, ``total_sessions`` / ``total_eligible`` counts, and
        an optional ``invalid_entries`` key listing entries missing ``session_name`` or ``animal``.
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

    filtered_entries = sorted(
        (session_map[session_name] for session_name, _ in filtered if session_name in session_map),
        key=lambda filtered_entry: filtered_entry.get("session_name", ""),
    )

    eligible_paths = sorted(
        entry["session_path"]
        for entry in filtered_entries
        if entry.get("status") != "error" and "session_path" in entry
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
def read_session_data_tool(file_path: str) -> dict[str, Any]:
    """Parses a ``session_data.yaml`` file and returns its serialized ``SessionData`` payload.

    For session discovery or lifecycle-status decisions, prefer ``get_data_root_overview_tool`` or
    ``inspect_sessions_tool`` instead — this tool only parses the marker file.

    Args:
        file_path: Absolute path to the ``session_data.yaml`` file. Canonical location is
            ``<session>/raw_data/session_data.yaml``.

    Returns:
        A response dict with ``file_path`` and ``data`` (the full SessionData payload).
    """
    return read_yaml(file_path=Path(file_path), validator_cls=SessionData)


@mcp.tool()
def write_session_data_tool(
    file_path: str,
    session_data_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Validates ``session_data_payload`` against ``SessionData`` and writes it to ``file_path``.

    Intended for agent-driven repair of a corrupted or missing session marker. The primary
    on-disk copy is normally authored by the acquisition runtime via ``SessionData.create``.

    Args:
        file_path: Absolute path to the destination ``session_data.yaml``. Canonical location is
            ``<session>/raw_data/session_data.yaml``.
        session_data_payload: The complete SessionData payload.
        overwrite: Determines whether to overwrite an existing file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated payload).
    """
    return write_yaml_validated(
        file_path=Path(file_path),
        payload=session_data_payload,
        validator_cls=SessionData,
        overwrite=overwrite,
    )


@mcp.tool()
def describe_session_data_schema_tool() -> dict[str, Any]:
    """Returns the schema for the ``SessionData`` dataclass.

    Returns:
        A response dict with ``schema`` containing the SessionData field schema.
    """
    return ok_response(schema=describe_dataclass(cls=SessionData))


@mcp.tool()
def list_processing_trackers_tool() -> dict[str, Any]:
    """Enumerates the ProcessingTracker filenames written by each data-integrity and processing pipeline on the
    Sollertia platform.

    Returns:
        A response dict with ``processing_trackers`` (a list of dicts containing ``name``, ``filename``, and
        ``description`` for each tracker member).
    """
    descriptions: dict[ProcessingTrackers, str] = {
        ProcessingTrackers.CHECKSUM: "Tracks the outcome of integrity checks performed by the checksum verification "
        "pipeline.",
        ProcessingTrackers.BEHAVIOR: "Tracks the outcome of behavior-data extraction performed by the "
        "sollertia-forgery behavior-processing pipeline.",
        ProcessingTrackers.CAMERA: "Tracks the outcome of camera-timestamp extraction performed by the "
        "ataraxis-video-system log-processing pipeline.",
        ProcessingTrackers.VIDEO: "Tracks the outcome of DeepLabCut processing and re-packaging performed by the "
        "sollertia-forgery video-processing pipeline.",
        ProcessingTrackers.MICROCONTROLLER: "Tracks the outcome of microcontroller-event extraction performed by "
        "the ataraxis-communication-interface log-processing pipeline.",
        ProcessingTrackers.CINDRA_SINGLE_RECORDING: "Tracks the outcome of single-recording neural imaging analysis "
        "performed by cindra's single-recording pipeline.",
        ProcessingTrackers.CINDRA_MULTI_RECORDING: "Tracks the outcome of multi-recording neural imaging analysis "
        "performed by cindra's multi-recording pipeline.",
        ProcessingTrackers.FORGING: "Tracks the outcome of dataset forging performed by the sollertia-forgery "
        "dataset-forging pipeline.",
        ProcessingTrackers.ANALYSIS: "Tracks the outcome of dataset analysis performed by the sollertia-forgery "
        "analysis pipeline.",
        ProcessingTrackers.MANIFEST: "Tracks the outcome of project manifest generation.",
        ProcessingTrackers.TRANSFER: "Tracks the outcome of batch session transfer and deletion jobs.",
    }
    entries: list[dict[str, Any]] = [
        {"name": member.name, "filename": member.value, "description": descriptions[member]}
        for member in ProcessingTrackers
    ]
    return ok_response(processing_trackers=entries)


@mcp.tool()
def read_session_descriptor_tool(file_path: str, session_type: str) -> dict[str, Any]:
    """Loads a session descriptor YAML, parsing it with the dataclass that matches ``session_type``.

    The descriptor filename is always ``session_descriptor.yaml`` — only the parsing class varies, so
    ``session_type`` must be supplied. Use ``list_supported_session_types_tool`` to enumerate valid values.

    Args:
        file_path: Absolute path to the descriptor YAML. Canonical location is
            ``<session>/raw_data/session_descriptor.yaml``.
        session_type: The ``SessionTypes`` value identifying which descriptor dataclass to use
            (``lick training``, ``run training``, ``mesoscope experiment``, or ``window checking``).

    Returns:
        A response dict with ``data`` (the descriptor payload), ``descriptor_class``, ``session_type``,
        and ``file_path``.
    """
    resolved = _resolve_descriptor_class(session_type=session_type)
    if isinstance(resolved, dict):
        return resolved
    response = read_yaml(file_path=Path(file_path), validator_cls=resolved)
    if response.get("success"):
        response["descriptor_class"] = resolved.__name__
        response["session_type"] = session_type
    return response


@mcp.tool()
def write_session_descriptor_tool(
    file_path: str,
    session_type: str,
    descriptor_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Validates ``descriptor_payload`` against the descriptor for ``session_type`` and writes it to ``file_path``.

    Use ``list_supported_session_types_tool`` to enumerate valid ``session_type`` values.

    Args:
        file_path: Absolute path to the destination descriptor YAML. Canonical location is
            ``<session>/raw_data/session_descriptor.yaml``.
        session_type: The ``SessionTypes`` value identifying which descriptor dataclass to validate
            against (``lick training``, ``run training``, ``mesoscope experiment``, or
            ``window checking``).
        descriptor_payload: The complete descriptor payload matching the schema for ``session_type``.
        overwrite: Determines whether to overwrite an existing file.

    Returns:
        A response dict with ``file_path``, ``data`` (the validated payload), ``descriptor_class``,
        and ``session_type``.
    """
    resolved = _resolve_descriptor_class(session_type=session_type)
    if isinstance(resolved, dict):
        return resolved
    response = write_yaml_validated(
        file_path=Path(file_path),
        payload=descriptor_payload,
        validator_cls=resolved,
        overwrite=overwrite,
    )
    if response.get("success"):
        response["descriptor_class"] = resolved.__name__
        response["session_type"] = session_type
    return response


@mcp.tool()
def describe_session_descriptor_schema_tool(session_type: str) -> dict[str, Any]:
    """Returns the schema for the descriptor dataclass associated with ``session_type``.

    Args:
        session_type: The ``SessionTypes`` value to describe.

    Returns:
        A response dict with ``session_type`` (the validated enum value) and ``schema`` (the
        descriptor dataclass field schema).
    """
    resolved = _resolve_descriptor_class(session_type=session_type)
    if isinstance(resolved, dict):
        return resolved
    return ok_response(
        session_type=session_type,
        schema=describe_dataclass(cls=resolved),
    )


@mcp.tool()
def read_session_hardware_state_tool(file_path: str, acquisition_system: str) -> dict[str, Any]:
    """Loads a hardware-state YAML, parsing it with the dataclass that matches ``acquisition_system``.

    The hardware-state filename is always ``hardware_state.yaml`` — only the parsing class varies, so
    ``acquisition_system`` must be supplied. Use ``list_supported_acquisition_systems_tool`` to
    enumerate valid values.

    Args:
        file_path: Absolute path to the hardware-state YAML. Canonical location is
            ``<session>/raw_data/hardware_state.yaml``.
        acquisition_system: The ``AcquisitionSystems`` value identifying which hardware-state
            dataclass to use.

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
    """Validates ``hardware_state_payload`` against the ``acquisition_system`` schema and writes it to ``file_path``.

    Use ``list_supported_acquisition_systems_tool`` to enumerate valid ``acquisition_system`` values.

    Args:
        file_path: Absolute path to the destination hardware-state YAML. Canonical location is
            ``<session>/raw_data/hardware_state.yaml``.
        acquisition_system: The ``AcquisitionSystems`` value identifying which hardware-state
            dataclass to validate against.
        hardware_state_payload: The complete hardware-state payload.
        overwrite: Determines whether to overwrite an existing file.

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
    """Returns the schema for the hardware-state dataclass of ``acquisition_system``.

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
    """Loads a per-session surgery-metadata YAML and returns the full SurgeryData payload.

    Surgery metadata is a single monolithic record — callers extract the ``subject``, ``procedure``,
    ``drugs``, ``implants``, or ``injections`` sections from the returned payload themselves.

    Args:
        file_path: Absolute path to the surgery-metadata YAML. Canonical location is
            ``<session>/raw_data/surgery_metadata.yaml``.

    Returns:
        A response dict with ``file_path`` and ``data`` (the full SurgeryData payload, with
        ``subject``, ``procedure``, ``drugs``, ``implants``, and ``injections`` sections).
    """
    return read_yaml(file_path=Path(file_path), validator_cls=SurgeryData)


@mcp.tool()
def write_surgery_data_tool(
    file_path: str,
    surgery_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Validates ``surgery_payload`` against ``SurgeryData`` and writes it to ``file_path``.

    The payload must include all sections (``subject``, ``procedure``, ``drugs``, ``implants``,
    ``injections``); surgery metadata is a single monolithic record with no per-section tools.

    Args:
        file_path: Absolute path to the destination surgery-metadata YAML. Canonical location is
            ``<session>/raw_data/surgery_metadata.yaml``.
        surgery_payload: The complete SurgeryData payload.
        overwrite: Determines whether to overwrite an existing file.

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


def _compute_session_status(instance: SessionData) -> _SessionStatusInfo:
    """Derives lifecycle status for a loaded ``SessionData`` using the canonical two-signal model.

    Combines the ``nk.bin`` uninitialized marker, the descriptor's ``incomplete`` flag, and the
    processed_data directory population to project a coarse status. Status priority is
    ``uninitialized > error > incomplete > processed > acquired``.

    Args:
        instance: A loaded ``SessionData`` instance.

    Returns:
        A ``_SessionStatusInfo`` carrying the status string, the two boolean signals, the processed_data
        population flag, and an optional descriptor-read error detail.
    """
    uninitialized = instance.raw_data.nk_path.exists()
    processed_data_directory = instance.processed_data_path
    has_processed_data = processed_data_directory.is_dir() and any(processed_data_directory.iterdir())

    if uninitialized:
        return _SessionStatusInfo(
            status="uninitialized",
            uninitialized=True,
            incomplete=None,
            has_processed_data=has_processed_data,
            error_detail=None,
        )

    descriptor_incomplete, descriptor_error = read_descriptor_incomplete(session=instance)
    if descriptor_incomplete is None:
        return _SessionStatusInfo(
            status="error",
            uninitialized=False,
            incomplete=None,
            has_processed_data=has_processed_data,
            error_detail=descriptor_error,
        )

    if descriptor_incomplete:
        status = "incomplete"
    elif has_processed_data:
        status = "processed"
    else:
        status = "acquired"
    return _SessionStatusInfo(
        status=status,
        uninitialized=False,
        incomplete=descriptor_incomplete,
        has_processed_data=has_processed_data,
        error_detail=None,
    )


def _aggregate_projects(root: Path, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups flat session entries into the ``projects -> animals -> sessions`` hierarchy.

    Error-status entries (whose identity could not be trusted from SessionData) are excluded from
    aggregation; they remain in the top-level flat ``sessions`` list only. The returned per-project
    dicts do not include filesystem-derived counts such as ``experiment_count`` or ``dataset_count``;
    callers obtain those via ``_count_project_artifacts``.

    Args:
        root: The resolved data root path used to construct each project's reported ``path``.
        sessions: Flat per-session entries produced by ``get_data_root_overview_tool``.

    Returns:
        A list of per-project aggregate dicts sorted by project name.
    """
    # Buckets by SessionData identity rather than directory layout to suppress phantom-project entries from stray dirs.
    project_buckets: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for entry in sessions:
        if entry.get("status") == "error":
            continue
        project_name = entry.get("project")
        animal_id = entry.get("animal")
        if not isinstance(project_name, str) or not isinstance(animal_id, str):
            continue
        if not project_name or not animal_id:
            continue
        project_buckets.setdefault(project_name, {}).setdefault(animal_id, []).append(entry)

    projects: list[dict[str, Any]] = []
    for project_name in sorted(project_buckets):
        animal_buckets = project_buckets[project_name]
        project_path = root.joinpath(project_name)

        animals: list[dict[str, Any]] = []
        project_counts: dict[str, int] = dict.fromkeys(_STATUS_KEYS, 0)
        sessions_by_type: dict[str, int] = {member.value: 0 for member in SessionTypes}
        project_session_count = 0
        for animal_id in sorted(animal_buckets):
            animal_entries = animal_buckets[animal_id]
            animal_counts: dict[str, int] = dict.fromkeys(_STATUS_KEYS, 0)
            session_paths: list[str] = []
            for animal_entry in animal_entries:
                status_key = animal_entry["status"]
                animal_counts[status_key] = animal_counts.get(status_key, 0) + 1
                project_counts[status_key] = project_counts.get(status_key, 0) + 1
                session_type_value = animal_entry.get("session_type")
                if isinstance(session_type_value, str):
                    sessions_by_type[session_type_value] = sessions_by_type.get(session_type_value, 0) + 1
                session_paths.append(animal_entry["session_path"])
            animals.append(
                {
                    "id": animal_id,
                    "session_paths": sorted(session_paths),
                    "session_count": len(animal_entries),
                    "counts": animal_counts,
                }
            )
            project_session_count += len(animal_entries)

        projects.append(
            {
                "name": project_name,
                "path": str(project_path),
                "animals": animals,
                "session_count": project_session_count,
                "counts": project_counts,
                "sessions_by_type": sessions_by_type,
            }
        )

    return projects


def _count_project_artifacts(project_path: Path) -> tuple[int, int]:
    """Counts experiment configuration YAMLs and dataset markers under a project directory.

    Args:
        project_path: The path to the project directory under the data root.

    Returns:
        A tuple of ``(experiment_count, dataset_count)``. Experiment count is the number of
        ``.yaml`` files directly under ``<project>/configuration/``; dataset count is the
        number of ``DATASET_MARKER_FILENAME`` occurrences anywhere under the project.
    """
    configuration_directory = project_path.joinpath(CONFIGURATION_DIR)
    experiment_count = len(list(configuration_directory.glob("*.yaml"))) if configuration_directory.is_dir() else 0
    dataset_count = len(list(project_path.rglob(DATASET_MARKER_FILENAME))) if project_path.is_dir() else 0
    return experiment_count, dataset_count


def _build_session_report(instance: SessionData, session_root: Path) -> dict[str, Any]:
    """Produces a per-session inspection report from a loaded ``SessionData`` instance.

    Enumerates every canonical ``raw_data`` file and ``processed_data`` subdirectory exposed by
    ``SessionData``, checks the required-asset set for the session's type, and attaches the same
    lifecycle status that ``get_data_root_overview_tool`` computes.

    Args:
        instance: The loaded ``SessionData`` instance.
        session_root: The resolved session root directory.

    Returns:
        A per-session report dict.
    """
    session_type = SessionTypes(instance.session_type)
    status_info = _compute_session_status(instance=instance)

    raw_data_files = _raw_data_inventory(instance=instance)
    processed_data_subdirs = _processed_data_inventory(instance=instance)
    required_assets = _required_asset_inventory(instance=instance, session_type=session_type)
    issues = [
        f"Missing required {asset['name']} at {asset['path']}" for asset in required_assets if not asset["present"]
    ]

    report: dict[str, Any] = {
        "session_path": str(session_root),
        "identity": {
            "project": instance.project_name,
            "animal": instance.animal_id,
            "session_name": instance.session_name,
            "session_type": session_type.value,
            "acquisition_system": serialize(value=instance.acquisition_system),
            "experiment_name": instance.experiment_name,
        },
        "status": status_info.status,
        "uninitialized": status_info.uninitialized,
        "incomplete": status_info.incomplete,
        "has_processed_data": status_info.has_processed_data,
        "raw_data_files": raw_data_files,
        "processed_data_subdirs": processed_data_subdirs,
        "required_assets": required_assets,
        "issues": issues,
    }
    if status_info.error_detail is not None:
        report["error_detail"] = status_info.error_detail
    return report


def _raw_data_inventory(instance: SessionData) -> list[dict[str, Any]]:
    """Returns the existence and classification of every canonical asset under the session's ``raw_data`` directory.

    Iterates ``dataclasses.fields()`` over ``instance.raw_data`` (generic raw assets) and
    ``instance.system_raw_data`` (acquisition-system-specific raw assets) so that new fields and new system
    extensions are picked up automatically without per-class hardcoding here.

    Args:
        instance: A loaded ``SessionData`` instance with sub-dataclass attributes populated by
            ``_build_sub_dataclasses``.

    Returns:
        A list of ``{field, path, scope, kind, exists}`` dicts. ``scope`` is ``"generic"`` for fields read off
        ``raw_data`` and ``"system"`` for fields read off ``system_raw_data``. ``kind`` is ``"file"`` for paths
        that carry a filename suffix and ``"directory"`` otherwise.
    """
    inventory: list[dict[str, Any]] = []
    for field_definition in fields(instance.raw_data):
        path = getattr(instance.raw_data, field_definition.name)
        inventory.append(_inventory_entry(scope="generic", field_name=field_definition.name, path=path))
    for field_definition in fields(instance.system_raw_data):
        path = getattr(instance.system_raw_data, field_definition.name)
        inventory.append(_inventory_entry(scope="system", field_name=field_definition.name, path=path))
    return inventory


def _processed_data_inventory(instance: SessionData) -> list[dict[str, Any]]:
    """Returns the existence and classification of every canonical asset under the session's ``processed_data``
    directory.

    Iterates ``dataclasses.fields()`` over ``instance.processed_data`` so that new processed-data fields are
    picked up automatically without per-pipeline hardcoding here.

    Args:
        instance: A loaded ``SessionData`` instance with sub-dataclass attributes populated by
            ``_build_sub_dataclasses``.

    Returns:
        A list of ``{field, path, scope, kind, exists}`` dicts. ``scope`` is always ``"generic"``. ``kind`` is
        ``"file"`` for paths that carry a filename suffix and ``"directory"`` otherwise.
    """
    return [
        _inventory_entry(
            scope="generic",
            field_name=field_definition.name,
            path=getattr(instance.processed_data, field_definition.name),
        )
        for field_definition in fields(instance.processed_data)
    ]


def _inventory_entry(scope: str, field_name: str, path: Path) -> dict[str, Any]:
    """Builds one inventory entry for a sub-dataclass path field.

    Args:
        scope: Either ``"generic"`` (read off the system-agnostic sub-dataclass) or ``"system"`` (read off the
            acquisition-system-specific extension sub-dataclass).
        field_name: The name of the dataclass field (e.g., ``"session_descriptor_path"``).
        path: The resolved path value held in the field.

    Returns:
        A dict with ``field``, ``path``, ``scope``, ``kind``, and ``exists`` keys. The ``kind`` is derived from
        the path's suffix: paths with a non-empty suffix are reported as files, others as directories.
    """
    is_file = bool(path.suffix)
    return {
        "field": field_name,
        "path": str(path),
        "scope": scope,
        "kind": "file" if is_file else "directory",
        "exists": path.is_file() if is_file else path.is_dir(),
    }


def _required_asset_inventory(instance: SessionData, session_type: SessionTypes) -> list[dict[str, Any]]:
    """Returns the existence of each asset required for the session's type.

    Every session requires the descriptor and the system configuration snapshot; ``mesoscope experiment``
    sessions additionally require the experiment configuration snapshot.

    Args:
        instance: The loaded ``SessionData`` instance.
        session_type: The session's validated ``SessionTypes`` value.

    Returns:
        A list of ``{name, path, present, required_for_session_type}`` dicts.
    """
    required: list[tuple[str, Path]] = [
        (RawDataFiles.SESSION_DESCRIPTOR.value, instance.raw_data.session_descriptor_path),
        (RawDataFiles.SYSTEM_CONFIGURATION.value, instance.raw_data.system_configuration_path),
    ]
    if session_type == SessionTypes.MESOSCOPE_EXPERIMENT:
        required.append((RawDataFiles.EXPERIMENT_CONFIGURATION.value, instance.raw_data.experiment_configuration_path))
        required.append((RawDataFiles.VR_CONFIGURATION.value, instance.raw_data.vr_configuration_path))
    return [
        {
            "name": name,
            "path": str(path),
            "present": path.exists(),
            "required_for_session_type": session_type.value,
        }
        for name, path in required
    ]


def _resolve_descriptor_class(session_type: str) -> type[YamlConfig] | dict[str, Any]:
    """Resolves a ``session_type`` string to its registered descriptor dataclass.

    Validates the value against the ``SessionTypes`` enum and then looks up the corresponding class
    in ``DESCRIPTOR_REGISTRY``. Returns an error response dict when the value is not a valid session
    type.

    Args:
        session_type: The ``SessionTypes`` value supplied by the caller.

    Returns:
        The resolved descriptor dataclass on success, or an error response dict on failure. Callers
        discriminate via ``isinstance(result, dict)``.
    """
    try:
        session_type_enum = SessionTypes(session_type)
    except ValueError:
        valid = ", ".join(member.value for member in SessionTypes)
        message = (
            f"Unable to resolve the descriptor class. The session_type '{session_type}' is not a member of "
            f"SessionTypes. Valid values: {valid}."
        )
        return error_response(message=message)
    return DESCRIPTOR_REGISTRY[session_type_enum]


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
        message = (
            f"Unable to resolve the hardware-state class. The acquisition_system '{acquisition_system}' is "
            f"not a member of AcquisitionSystems. Valid values: {valid}."
        )
        return error_response(message=message)
    hardware_state_class = HARDWARE_STATE_REGISTRY.get(acquisition_enum)
    if hardware_state_class is None:
        registered = ", ".join(member.value for member in HARDWARE_STATE_REGISTRY)
        message = (
            f"Unable to resolve the hardware-state class. No class is registered for '{acquisition_system}'. "
            f"Registered systems: {registered}."
        )
        return error_response(message=message)
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
        message = f"Unable to resolve the session root. The path {path} does not exist."
        return None, error_response(message=message)
    if path.joinpath(RAW_DATA_DIRECTORY).is_dir():
        return path, None
    if path.name == RAW_DATA_DIRECTORY and path.is_dir():
        return path.parent, None
    message = f"Unable to resolve the session root. No {RAW_DATA_DIRECTORY} directory was located under {path}."
    return None, error_response(message=message)
