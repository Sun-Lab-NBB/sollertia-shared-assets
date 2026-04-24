"""Provides MCP tools for discovering, reading, writing, and validating runtime data assets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from pathlib import Path

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig

from .mcp_instance import (
    CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY,
    DATASET_MARKER_FILENAME,
    HARDWARE_STATE_REGISTRY,
    UNINITIALIZED_SESSION_MARKER,
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
    DrugData,
    Directories,
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

_STATUS_KEYS: tuple[str, ...] = ("uninitialized", "incomplete", "acquired", "processed", "error")
"""Canonical lifecycle status keys used in ``counts`` dicts across the overview and inspection tools."""


@mcp.tool()
def get_data_root_overview_tool(root_directory: str) -> dict[str, Any]:
    """Builds a project / animal / session hierarchy under the data root from SessionData contents.

    Recursively discovers every ``session_data.yaml`` marker under ``root_directory``, loads each one
    via ``SessionData.load``, and groups the results by the YAML's identity fields
    (``project_name``, ``animal_id``) rather than by directory structure. A project or animal appears
    only when at least one loaded SessionData names it, so stray directories at the data root cannot
    surface as phantom projects or animals.

    Lifecycle status for each session is derived from the same two-signal model as prior tools: the
    ``nk.bin`` uninitialized marker in ``raw_data`` and the descriptor's ``incomplete`` field. Status
    priority is ``uninitialized > error > incomplete > processed > acquired``. SessionData files that
    fail to load surface as flat-list entries with ``status="error"`` and an ``error_detail`` field;
    error entries do not contribute to project or animal aggregation because their identity is
    untrusted, but they are counted in the top-level ``counts``.

    Args:
        root_directory: The absolute path to the root data directory to scan.

    Returns:
        A response dict. The ``projects`` key holds a list of per-project entries with ``name``,
        ``path``, and a nested ``animals`` list. Each project entry also carries
        ``session_count``, a ``counts`` status tally, ``sessions_by_type``, ``experiment_count``,
        and ``dataset_count``. Each ``animals`` entry carries ``id``, ``session_paths``,
        ``session_count``, and ``counts``. The ``sessions`` key holds a flat list of per-session
        entries (identity, paths, status, and flags) suitable for chaining into
        ``filter_sessions_tool``. The top-level ``counts`` key is a status tally across every
        discovered session, including errors. The response also carries ``total_projects``,
        ``total_animals``, ``total_sessions``, and ``root_directory``.
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
        session_root = session_root_from_marker(marker=marker)
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

        status, uninitialized, incomplete, has_processed_data, error_detail = _compute_session_status(instance=instance)
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
            "status": status,
            "uninitialized": uninitialized,
            "incomplete": incomplete,
            "has_processed_data": has_processed_data,
        }
        if error_detail is not None:
            entry["error_detail"] = error_detail
        flat_sessions.append(entry)
        top_counts[status] += 1

    projects = _aggregate_projects(root=root, sessions=flat_sessions)  # type: ignore[arg-type]
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
    """Produces a detailed health and inventory report for each supplied session.

    Accepts one or more session paths; there is no separate single-vs-batch signature. For each path,
    the tool resolves the session root (accepting either the root or its ``raw_data`` subdirectory),
    loads ``SessionData``, and enumerates every canonical asset path exposed by the data class.
    The report covers lifecycle status using the same two-signal model as
    ``get_data_root_overview_tool``. It enumerates every ``raw_data`` canonical file
    (``RawDataFiles`` entries) with a classification ``kind`` and an ``exists`` flag. It also
    enumerates every ``processed_data`` subdirectory (behavior, cindra, camera_timestamps,
    camera_data, microcontroller_data) with its paired processing tracker presence. Finally, it
    runs a ``required_assets`` check against the session type. The descriptor and system
    configuration snapshot are required for every session type. The experiment configuration
    snapshot is additionally required for ``mesoscope experiment`` sessions.

    Paths that cannot be resolved to a session root, or whose ``SessionData`` fails to load, surface
    with ``status="error"`` and an ``error_detail`` field without aborting the rest of the batch.

    Args:
        session_paths: A list of absolute session-root or ``raw_data`` paths to inspect. Pass a
            single-element list for single-session inspection.

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

    Designed for agentic chaining with ``get_data_root_overview_tool``: accepts the ``sessions`` list
    from its output and returns a filtered subset with the same structure. Each input entry must
    contain ``session_name`` and ``animal`` keys (matching the shape produced by
    ``get_data_root_overview_tool``). Animal filtering is applied before session filtering and
    exclusion always takes precedence over inclusion.

    Args:
        sessions: A list of session entry dictionaries, each containing at least ``session_name`` and
            ``animal`` keys. Typically, the ``sessions`` list returned by
            ``get_data_root_overview_tool``.
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
        Structurally compatible with ``get_data_root_overview_tool`` output for downstream chaining.
        An ``invalid_entries`` key appears when input entries lack the required
        ``session_name`` / ``animal`` fields.
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
    """Loads a ``session_data.yaml`` file via the ``SessionData`` dataclass.

    Plain file-path-based reader, symmetric with ``read_session_descriptor_tool``,
    ``read_session_hardware_state_tool``, and ``read_surgery_data_tool``. Returns the raw
    serialized ``SessionData`` payload exactly as stored in the YAML, including the
    ``python_version`` and ``sollertia_experiment_version`` schema-compatibility fields.

    Callers that need session discovery, identity grouping, or lifecycle-status derivation
    should call ``get_data_root_overview_tool`` (whole-root walk) or ``inspect_sessions_tool``
    (per-session health and inventory report) **before** this tool. Those tools decide whether
    the session holds valid data at all; this tool only parses the marker file.

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
    """Creates or replaces a ``session_data.yaml`` file.

    Validates ``session_data_payload`` against the ``SessionData`` schema and writes the result
    to ``file_path``. Intended for agent-driven repair of a corrupted or partially missing
    session marker; the primary on-disk copy is always authored by the acquisition runtime via
    ``SessionData.create`` at session start.

    Args:
        file_path: Absolute path to the destination ``session_data.yaml`` file. Canonical
            location is ``<session>/raw_data/session_data.yaml``.
        session_data_payload: The complete SessionData payload (all identity fields plus
            ``raw_data_path`` / ``processed_data_path`` strings).
        overwrite: Determines whether to overwrite an existing session_data file.

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
    """Returns the schema for the descriptor associated with a given session type.

    The descriptor always uses the ``session_descriptor.yaml`` filename regardless of session type, only the
    parsing class varies.

    Args:
        session_type: The SessionTypes value to describe.

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

    The hardware-state snapshot always uses the ``hardware_state.yaml`` filename regardless of acquisition system,
    only the parsing class varies.

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


def _compute_session_status(
    instance: SessionData,
) -> tuple[str, bool, bool | None, bool, str | None]:
    """Derives lifecycle status for a loaded ``SessionData`` using the canonical two-signal model.

    Combines the ``nk.bin`` uninitialized marker, the descriptor's ``incomplete`` flag, and the
    processed_data directory population to project a coarse status. Status priority is
    ``uninitialized > error > incomplete > processed > acquired``.

    Args:
        instance: A loaded ``SessionData`` instance.

    Returns:
        A tuple of ``(status, uninitialized, incomplete, has_processed_data, error_detail)`` where
        ``incomplete`` is None for uninitialized sessions or when the descriptor read fails.
    """
    uninitialized = instance.raw_data_path.joinpath(UNINITIALIZED_SESSION_MARKER).exists()
    processed_data_directory = instance.processed_data_path
    has_processed_data = processed_data_directory.is_dir() and any(processed_data_directory.iterdir())

    if uninitialized:
        return "uninitialized", True, None, has_processed_data, None

    descriptor_incomplete, descriptor_error = read_descriptor_incomplete(session=instance)
    if descriptor_incomplete is None:
        return "error", False, None, has_processed_data, descriptor_error

    if descriptor_incomplete:
        status = "incomplete"
    elif has_processed_data:
        status = "processed"
    else:
        status = "acquired"
    return status, False, descriptor_incomplete, has_processed_data, None


def _aggregate_projects(root: Path, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Groups flat session entries into the ``projects -> animals -> sessions`` hierarchy.

    Error-status entries (whose identity could not be trusted from SessionData) are excluded from
    aggregation; they remain in the top-level flat ``sessions`` list only. For each discovered
    project, the helper also computes ``experiment_count`` (YAML files under ``<project>/configuration/``)
    and ``dataset_count`` (``DATASET_MARKER_FILENAME`` occurrences under the project).

    Args:
        root: The resolved data root path.
        sessions: Flat per-session entries produced by ``get_data_root_overview_tool``.

    Returns:
        A list of per-project aggregate dicts sorted by project name.
    """
    # Buckets sessions under their project and animal by the SessionData identity fields.
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

        # Aggregates per-animal summaries and accumulates per-project status and type counts.
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

        # Counts experiment configurations and dataset markers under the project on disk.
        configuration_directory = project_path.joinpath(CONFIGURATION_DIR)
        experiment_count = len(list(configuration_directory.glob("*.yaml"))) if configuration_directory.is_dir() else 0
        dataset_count = len(list(project_path.rglob(DATASET_MARKER_FILENAME))) if project_path.is_dir() else 0

        projects.append(
            {
                "name": project_name,
                "path": str(project_path),
                "animals": animals,
                "session_count": project_session_count,
                "counts": project_counts,
                "sessions_by_type": sessions_by_type,
                "experiment_count": experiment_count,
                "dataset_count": dataset_count,
            }
        )

    return projects


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
    session_type = (
        instance.session_type
        if isinstance(instance.session_type, SessionTypes)
        else SessionTypes(instance.session_type)
    )
    status, uninitialized, incomplete, has_processed_data, status_error = _compute_session_status(instance=instance)

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
        "status": status,
        "uninitialized": uninitialized,
        "incomplete": incomplete,
        "has_processed_data": has_processed_data,
        "raw_data_files": raw_data_files,
        "processed_data_subdirs": processed_data_subdirs,
        "required_assets": required_assets,
        "issues": issues,
    }
    if status_error is not None:
        report["error_detail"] = status_error
    return report


def _raw_data_inventory(instance: SessionData) -> list[dict[str, Any]]:
    """Returns the existence and classification of every canonical ``raw_data`` file."""
    mapping: list[tuple[str, Path]] = [
        (RawDataFiles.SESSION_DATA.name, instance.session_data_path),
        (RawDataFiles.SESSION_DESCRIPTOR.name, instance.session_descriptor_path),
        (RawDataFiles.SURGERY_METADATA.name, instance.surgery_metadata_path),
        (RawDataFiles.HARDWARE_STATE.name, instance.hardware_state_path),
        (RawDataFiles.EXPERIMENT_CONFIGURATION.name, instance.experiment_configuration_path),
        (RawDataFiles.SYSTEM_CONFIGURATION.name, instance.system_configuration_path),
        (RawDataFiles.CHECKSUM.name, instance.checksum_path),
        (RawDataFiles.ZABER_POSITIONS.name, instance.zaber_positions_path),
        (RawDataFiles.MESOSCOPE_POSITIONS.name, instance.mesoscope_positions_path),
        (RawDataFiles.WINDOW_SCREENSHOT.name, instance.window_screenshot_path),
    ]
    # Also includes the raw_data subdirectories that carry bulk acquisition artifacts.
    directory_mapping: list[tuple[str, Path]] = [
        (f"{Directories.CAMERA_DATA.name}_RAW", instance.raw_camera_data_path),
        (f"{Directories.BEHAVIOR_DATA.name}_RAW", instance.raw_behavior_data_path),
        (f"{Directories.MICROCONTROLLER_DATA.name}_RAW", instance.raw_microcontroller_data_path),
        (f"{Directories.MESOSCOPE_DATA.name}_RAW", instance.raw_mesoscope_data_path),
    ]
    inventory: list[dict[str, Any]] = []
    for kind, path in mapping:
        inventory.append({"name": path.name, "path": str(path), "kind": kind, "exists": path.exists()})
    for kind, path in directory_mapping:
        inventory.append({"name": path.name, "path": str(path), "kind": kind, "exists": path.is_dir()})
    return inventory


def _processed_data_inventory(instance: SessionData) -> list[dict[str, Any]]:
    """Returns per-subdirectory population and tracker presence under ``processed_data``."""
    mapping: list[tuple[str, Path, Path]] = [
        (Directories.BEHAVIOR_DATA.name, instance.behavior_data_path, instance.behavior_tracker_path),
        (Directories.CINDRA.name, instance.cindra_data_path, instance.cindra_single_recording_tracker_path),
        (Directories.CAMERA_TIMESTAMPS.name, instance.camera_timestamps_path, instance.camera_tracker_path),
        (Directories.CAMERA_DATA.name, instance.camera_data_path, instance.video_tracker_path),
        (
            Directories.MICROCONTROLLER_DATA.name,
            instance.microcontroller_data_path,
            instance.microcontroller_tracker_path,
        ),
    ]
    inventory: list[dict[str, Any]] = []
    for kind, directory_path, tracker_path in mapping:
        inventory.append(
            {
                "name": directory_path.name,
                "path": str(directory_path),
                "kind": kind,
                "exists": directory_path.is_dir(),
                "tracker_path": str(tracker_path),
                "tracker_exists": tracker_path.exists(),
            }
        )
    # Reports the cindra multi-recording subdirectory separately because it is a sibling of the
    # single-recording tracker inside ``cindra/``.
    inventory.append(
        {
            "name": instance.cindra_multi_recording_path.name,
            "path": str(instance.cindra_multi_recording_path),
            "kind": Directories.MULTI_RECORDING.name,
            "exists": instance.cindra_multi_recording_path.is_dir(),
            "tracker_path": None,
            "tracker_exists": False,
        }
    )
    return inventory


def _required_asset_inventory(instance: SessionData, session_type: SessionTypes) -> list[dict[str, Any]]:
    """Returns the existence of each asset required for the session's type.

    Mirrors the required-file set previously enforced by ``validate_session_tool``: every session
    requires the descriptor and the system configuration snapshot; ``mesoscope experiment`` sessions
    additionally require the experiment configuration snapshot.

    Args:
        instance: The loaded ``SessionData`` instance.
        session_type: The session's validated ``SessionTypes`` value.

    Returns:
        A list of ``{name, path, present, required_for_session_type}`` dicts.
    """
    required: list[tuple[str, Path]] = [
        (RawDataFiles.SESSION_DESCRIPTOR.value, instance.session_descriptor_path),
        (RawDataFiles.SYSTEM_CONFIGURATION.value, instance.system_configuration_path),
    ]
    if session_type == SessionTypes.MESOSCOPE_EXPERIMENT:
        required.append((RawDataFiles.EXPERIMENT_CONFIGURATION.value, instance.experiment_configuration_path))
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
        return error_response(message=f"Invalid session_type '{session_type}'. Valid values: {valid}")
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
        return error_response(message=f"Invalid acquisition_system '{acquisition_system}'. Valid values: {valid}")
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
