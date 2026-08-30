"""Provides MCP tools for discovering, reading, writing, and validating forged dataset assets."""

from __future__ import annotations

from typing import Any
from pathlib import Path

from ataraxis_data_structures import index_marker_files

from ..enums import SessionTypes
from ..registries import SESSION_TYPES_USING_VR_TASK
from .mcp_instance import (
    mcp,
    read_yaml,
    serialize,
    ok_response,
    error_response,
    describe_dataclass,
    write_yaml_validated,
    resolve_root_directory,
    collect_field_dataclasses,
)
from ..data_hierarchy import (
    DATASET_MARKER_FILENAME,
    DatasetData,
    DatasetFiles,
    RawDataFiles,
)

_DISCOVERY_STATUS_KEYS: tuple[str, ...] = ("ok", "error")
"""Canonical status keys used in the ``counts`` dict returned by the dataset discovery tool, which reports whether each
marker loads rather than whether the dataset it describes is complete."""

_INSPECTION_STATUS_KEYS: tuple[str, ...] = ("complete", "incomplete", "error")
"""Canonical status keys used in the ``counts`` dict returned by the dataset inspection tool, which stats every
artifact and therefore reports completeness."""


@mcp.tool()
def discover_datasets_tool(root_directory: str, project: str | None = None) -> dict[str, Any]:
    """Discovers every forged dataset under the data root by locating and loading its ``dataset.yaml`` marker.

    Expands the per-project ``dataset_count`` that ``get_data_root_overview_tool`` reports into the identity and the
    membership of each dataset. Reports the dataset container alone. Forging job state lives with the pipeline that
    produces it, so questions about what has been forged go to sollertia-forgery's ``list_project_datasets_tool`` and
    ``read_dataset_state_tool`` instead.

    Markers that fail to load appear in the ``datasets`` list with ``status="error"`` and an ``error_detail`` field,
    and are excluded from the chainable ``dataset_paths`` list.

    Args:
        root_directory: Absolute path to the data root to scan.
        project: When provided, narrows the scan to that project's directory, which also bounds the cost of the walk
            on a data root holding many projects.

    Returns:
        A response dict with ``datasets``, ``dataset_paths``, ``total_datasets``, ``counts``, ``root_directory``, and
        ``project`` (the echoed filter, or None). Each loaded ``datasets`` entry carries ``name``, ``project``,
        ``session_type``, ``acquisition_system``, ``dataset_path``, ``marker_path``, ``session_count``,
        ``animal_count``, ``animals``, ``has_descriptions``, and ``status``. A marker that fails to load instead
        carries ``dataset_path``, ``marker_path``, ``status``, and ``error_detail``. The ``dataset_paths`` list holds
        the sorted roots of the loadable datasets and is accepted directly by sollertia-forgery's
        ``generate_dataset_state_tool`` and ``plan_dataset_jobs_tool``. The ``counts`` mapping tallies the loadable
        and the broken markers.
    """
    root, error = resolve_root_directory(root_directory=root_directory)
    if error is not None:
        return error
    if root is None:
        message = f"Unable to resolve the data root from {root_directory}."
        return error_response(message=message)

    scan_root = root
    if project is not None:
        scan_root = root.joinpath(project)
        if not scan_root.is_dir():
            message = f"Unable to discover datasets. The project '{project}' was not found at {scan_root}."
            return error_response(message=message)

    # The scan reports a directory it cannot read instead of skipping it, which is surfaced as a failed response
    # rather than a listing that silently covers only the readable part of the tree.
    try:
        markers = index_marker_files(directory=scan_root, marker_names=(DATASET_MARKER_FILENAME,))
    except OSError as exception:
        message = f"Unable to scan {scan_root} for dataset markers: {exception}"
        return error_response(message=message)

    datasets: list[dict[str, Any]] = []
    counts: dict[str, int] = dict.fromkeys(_DISCOVERY_STATUS_KEYS, 0)
    for marker in markers[DATASET_MARKER_FILENAME]:
        try:
            instance = DatasetData.load(dataset_path=marker.parent)
        except Exception as exception:
            datasets.append(
                {
                    "dataset_path": str(marker.parent),
                    "marker_path": str(marker),
                    "status": "error",
                    "error_detail": f"Failed to load DatasetData: {exception}",
                }
            )
            counts["error"] += 1
            continue

        datasets.append(_dataset_overview_entry(instance=instance))
        counts["ok"] += 1

    dataset_paths = sorted(entry["dataset_path"] for entry in datasets if entry["status"] != "error")

    return ok_response(
        datasets=datasets,
        dataset_paths=dataset_paths,
        total_datasets=len(datasets),
        counts=counts,
        root_directory=str(root),
        project=project,
    )


@mcp.tool()
def inspect_datasets_tool(dataset_paths: list[str]) -> dict[str, Any]:
    """Produces a per-dataset structural inventory report for each supplied dataset path.

    Each report carries an ``identity`` block, the resolved path of every artifact the dataset hierarchy holds, and an
    ``issues`` list naming every structural problem it found. The marker keeps every path out of its serialized
    form, so this is the only tool that resolves the per-animal and per-session artifact paths.

    An artifact is required when the forging pipeline guarantees it. The per-dataset descriptions companion, the
    assembled ``data.feather``, and the session descriptor are required, and the VR configuration is required when the
    dataset's session type runs the corridor task. The experiment configuration is required per session rather than per
    dataset, and the per-animal surgery metadata is skipped when the source session lacks it, so both are reported
    without being demanded. Paths that fail to resolve or load surface with ``status="error"`` and an ``error_detail``
    field without aborting the batch.

    Args:
        dataset_paths: Absolute paths to dataset roots or to their ``dataset.yaml`` markers. Pass a single-element
            list to inspect one dataset.

    Returns:
        A response dict with ``datasets`` (per-dataset report dicts), ``total_datasets``, and ``counts`` (status tally
        across the batch). Each report carries ``dataset_path``, ``marker_path``, ``identity`` (``name``, ``project``,
        ``session_type``, ``acquisition_system``), ``status``, ``session_count``, ``animal_count``, ``descriptions``
        (``path``, ``present``, ``column_count``), ``animals`` (``animal``, ``animal_path``, ``session_count``, and a
        ``surgery_metadata`` artifact entry), ``sessions`` (``animal``, ``session``, ``session_path``,
        ``directory_present``, and an ``artifacts`` list), and ``issues``. Every artifact entry carries ``artifact``,
        ``path``, ``present``, and ``required``. A path that fails to resolve or load instead carries ``dataset_path``,
        ``status``, and ``error_detail`` alone.
    """
    reports: list[dict[str, Any]] = []
    counts: dict[str, int] = dict.fromkeys(_INSPECTION_STATUS_KEYS, 0)

    for raw_path in dataset_paths:
        instance, load_error = _load_dataset(dataset_path=raw_path)
        if load_error is not None or instance is None:
            reports.append(
                {
                    "dataset_path": raw_path,
                    "status": "error",
                    "error_detail": load_error["error"] if load_error is not None else "Unresolved dataset path",
                }
            )
            counts["error"] += 1
            continue

        report = _build_dataset_report(instance=instance)
        reports.append(report)
        counts[report["status"]] += 1

    return ok_response(datasets=reports, total_datasets=len(reports), counts=counts)


@mcp.tool()
def read_dataset_data_tool(file_path: str) -> dict[str, Any]:
    """Parses a ``dataset.yaml`` file and returns its serialized ``DatasetData`` payload.

    The marker keeps every path out of the written document so the dataset stays portable across processing machines,
    so the returned payload carries the dataset identity and its session membership without a single resolved path.
    Use ``inspect_datasets_tool`` to obtain the paths of the dataset's artifacts.

    Args:
        file_path: Absolute path to the ``dataset.yaml`` file. Canonical location is ``<dataset>/dataset.yaml``.

    Returns:
        A response dict with ``file_path`` and ``data`` (the DatasetData payload, carrying ``name``, ``project``,
        ``session_type``, ``acquisition_system``, and ``sessions``, where each session carries ``session`` and
        ``animal`` alone).
    """
    return read_yaml(file_path=Path(file_path), validator_cls=DatasetData)


@mcp.tool()
def write_dataset_data_tool(
    file_path: str,
    dataset_data_payload: dict[str, Any],
    *,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Validates ``dataset_data_payload`` against ``DatasetData`` and writes it to ``file_path``.

    Intended for agent-driven repair of a corrupted dataset marker. The primary on-disk copy is authored by
    sollertia-forgery's ``define_forging_dataset_tool``, which composes a dataset under an admission policy this tool
    does not apply. Use that tool to add sessions to a dataset.

    Validation covers the session type and the acquisition system vocabulary alone, so a payload that names a session
    the hierarchy does not hold, or that repeats an animal and session pair, is written as supplied. Run
    ``inspect_datasets_tool`` afterwards to confirm the marker matches the directory tree it describes.

    Args:
        file_path: Absolute path to the destination ``dataset.yaml``. Canonical location is ``<dataset>/dataset.yaml``.
        dataset_data_payload: The complete DatasetData payload.
        overwrite: Determines whether to overwrite an existing file.

    Returns:
        A response dict with ``file_path`` and ``data`` (the validated payload).
    """
    return write_yaml_validated(
        file_path=Path(file_path),
        payload=dataset_data_payload,
        validator_cls=DatasetData,
        overwrite=overwrite,
    )


@mcp.tool()
def describe_dataset_data_schema_tool() -> dict[str, Any]:
    """Returns the schema for the ``DatasetData`` dataclass, including the nested ``DatasetSession``.

    Use the returned schema to construct a valid payload for ``write_dataset_data_tool``.

    Returns:
        A response dict with ``schema`` containing the DatasetData field schema. The ``schema`` carries a
        ``nested_classes`` sub-mapping of each nested dataclass name to its individual schema, which resolves
        ``DatasetSession`` out of the ``sessions`` tuple annotation. ``DatasetAnimal`` is absent, since the dataset
        derives its animals from the session list rather than storing them. Use ``inspect_datasets_tool`` for
        animal-level facts.
    """
    schema = describe_dataclass(dataclass_type=DatasetData)
    schema["nested_classes"] = {
        name: describe_dataclass(dataclass_type=nested_class)
        for name, nested_class in collect_field_dataclasses(dataclass_type=DatasetData).items()
    }
    return ok_response(schema=schema)


@mcp.tool()
def read_dataset_column_descriptions_tool(dataset_path: str) -> dict[str, Any]:
    """Reads the mapping from each column in a dataset's assembled data to its human-readable description.

    Every forged dataset carries a ``data_descriptions.feather`` companion at its root that describes each column the
    dataset's acquisition system can emit into a session's ``data.feather``. The mapping is written once, when the
    dataset is created, and is the interpretation contract for every session the dataset holds.

    Args:
        dataset_path: Absolute path to the dataset root or to its ``dataset.yaml`` marker.

    Returns:
        A response dict with ``dataset_path``, ``descriptions_path``, ``column_descriptions`` (the ordered mapping
        from column name to description), and ``total_columns``.
    """
    instance, load_error = _load_dataset(dataset_path=dataset_path)
    if load_error is not None or instance is None:
        return load_error if load_error is not None else error_response(message="Unresolved dataset path")

    try:
        descriptions = instance.column_descriptions()
    except Exception as exception:
        message = f"Unable to read the column descriptions for the dataset at {dataset_path}: {exception}"
        return error_response(message=message)

    return ok_response(
        dataset_path=str(instance.dataset_data_path.parent),
        descriptions_path=str(instance.descriptions_path),
        column_descriptions=descriptions,
        total_columns=len(descriptions),
    )


@mcp.tool()
def validate_dataset_descriptions_tool(dataset_path: str) -> dict[str, Any]:
    """Verifies that every column written into any of a dataset's sessions carries a description.

    Reads the schema of each session's assembled ``data.feather`` without loading its data and confirms that each
    column it holds appears in the dataset's ``data_descriptions.feather``. The contract is one-directional, so a
    described column that no session emits passes. Intended to run once a dataset is fully composed.

    Args:
        dataset_path: Absolute path to the dataset root or to its ``dataset.yaml`` marker.

    Returns:
        A response dict with ``dataset_path``, ``valid``, and either ``summary`` (carrying ``session_count`` and
        ``described_column_count``) or ``issues`` (a list holding the verification failure, which names every
        undescribed column together with the sessions that emit it). A dataset whose descriptions companion or whose
        session data is missing reports ``valid`` false rather than the error envelope, since both are verification
        verdicts. A path that does not resolve to a dataset instead returns the error envelope.
    """
    instance, load_error = _load_dataset(dataset_path=dataset_path)
    if load_error is not None or instance is None:
        return load_error if load_error is not None else error_response(message="Unresolved dataset path")

    dataset_root = str(instance.dataset_data_path.parent)
    try:
        instance.verify_data_descriptions()
        described_columns = instance.column_descriptions()
    except Exception as exception:
        return ok_response(valid=False, dataset_path=dataset_root, issues=[str(exception)])

    summary = {"session_count": len(instance.sessions), "described_column_count": len(described_columns)}
    return ok_response(valid=True, dataset_path=dataset_root, summary=summary)


def _dataset_overview_entry(instance: DatasetData) -> dict[str, Any]:
    """Builds the discovery entry for a loaded dataset.

    Notes:
        Reports the identity and the membership the marker already carries, so enumerating a whole data root costs one
        marker load and one metadata query per dataset instead of a stat of every artifact each dataset holds.

    Args:
        instance: A loaded ``DatasetData`` instance whose summary to build.

    Returns:
        A dict carrying the dataset's identity, its resolved paths, its membership counts, and its status.
    """
    return {
        "name": instance.name,
        "project": instance.project,
        "session_type": serialize(value=instance.session_type),
        "acquisition_system": serialize(value=instance.acquisition_system),
        "dataset_path": str(instance.dataset_data_path.parent),
        "marker_path": str(instance.dataset_data_path),
        "session_count": len(instance.sessions),
        "animal_count": len(instance.animals),
        "animals": [animal.animal for animal in instance.animals],
        "has_descriptions": instance.descriptions_path.is_file(),
        "status": "ok",
    }


def _build_dataset_report(instance: DatasetData) -> dict[str, Any]:
    """Produces a structural inventory report from a loaded ``DatasetData`` instance.

    Args:
        instance: A loaded ``DatasetData`` instance whose hierarchy to inventory.

    Returns:
        A report dict with ``dataset_path``, ``marker_path``, ``identity``, ``status``, ``session_count``,
        ``animal_count``, ``descriptions``, ``animals``, ``sessions``, and ``issues`` keys.
    """
    descriptions, description_issues = _descriptions_inventory(instance=instance)
    animals = _dataset_animal_inventory(instance=instance)
    sessions = _dataset_session_inventory(instance=instance)

    issues = [
        *description_issues,
        *(
            f"Missing session directory at {session['session_path']}"
            for session in sessions
            if not session["directory_present"]
        ),
        *(
            f"Missing required {artifact['artifact']} at {artifact['path']}"
            for session in sessions
            for artifact in session["artifacts"]
            if artifact["required"] and not artifact["present"]
        ),
    ]

    return {
        "dataset_path": str(instance.dataset_data_path.parent),
        "marker_path": str(instance.dataset_data_path),
        "identity": {
            "name": instance.name,
            "project": instance.project,
            "session_type": serialize(value=instance.session_type),
            "acquisition_system": serialize(value=instance.acquisition_system),
        },
        "status": "incomplete" if issues else "complete",
        "session_count": len(instance.sessions),
        "animal_count": len(animals),
        "descriptions": descriptions,
        "animals": animals,
        "sessions": sessions,
        "issues": issues,
    }


def _descriptions_inventory(instance: DatasetData) -> tuple[dict[str, Any], list[str]]:
    """Returns the presence and the column count of the dataset's descriptions companion, with any issue it raises.

    Notes:
        The column count is read through the companion feather rather than derived, so a file that exists but cannot
        be parsed is reported as an issue instead of passing as a healthy artifact.

    Args:
        instance: A loaded ``DatasetData`` instance whose descriptions companion to inventory.

    Returns:
        A tuple of the descriptions dict, carrying ``path``, ``present``, and ``column_count``, and the list of issues
        the companion raised, which is empty when it reads cleanly.
    """
    descriptions_path = instance.descriptions_path
    entry: dict[str, Any] = {
        "path": str(descriptions_path),
        "present": descriptions_path.is_file(),
        "column_count": None,
    }
    if not entry["present"]:
        return entry, [f"Missing required {DatasetFiles.DESCRIPTIONS.value} at {descriptions_path}"]

    try:
        entry["column_count"] = len(instance.column_descriptions())
    except Exception as exception:
        return entry, [f"Unable to read {DatasetFiles.DESCRIPTIONS.value} at {descriptions_path}: {exception}"]

    return entry, []


def _dataset_animal_inventory(instance: DatasetData) -> list[dict[str, Any]]:
    """Returns the resolved path and the co-located artifacts of every animal in the dataset.

    Args:
        instance: A loaded ``DatasetData`` instance whose animals to inventory.

    Returns:
        A list of dicts carrying ``animal``, ``animal_path``, ``session_count``, and the animal's
        ``surgery_metadata`` artifact entry.
    """
    return [
        {
            "animal": animal.animal,
            "animal_path": str(animal.animal_path),
            "session_count": len(instance.get_sessions_for_animal(animal=animal.animal)),
            # The surgery snapshot is skipped when the animal's latest source session carries none, so its absence
            # describes the source data rather than a defect in the dataset.
            "surgery_metadata": _artifact_entry(
                artifact=RawDataFiles.SURGERY_METADATA.value,
                path=animal.surgery_path,
                required=False,
            ),
        }
        for animal in instance.animals
    ]


def _dataset_session_inventory(instance: DatasetData) -> list[dict[str, Any]]:
    """Returns the resolved path and the artifact inventory of every session in the dataset.

    Args:
        instance: A loaded ``DatasetData`` instance whose sessions to inventory.

    Returns:
        A list of dicts carrying ``animal``, ``session``, ``session_path``, ``directory_present``, and ``artifacts``.
    """
    # The VR snapshot is re-exported for the session types that run the corridor task, so the dataset's own session
    # type decides whether its absence is a defect. The experiment snapshot is gated on the per-session experiment
    # name, which the dataset marker does not carry, so it is reported without being demanded.
    vr_required = SessionTypes(instance.session_type) in SESSION_TYPES_USING_VR_TASK

    return [
        {
            "animal": session.animal,
            "session": session.session,
            "session_path": str(session.session_path),
            "directory_present": session.session_path.is_dir(),
            "artifacts": [
                _artifact_entry(artifact=DatasetFiles.DATA.value, path=session.data_path, required=True),
                _artifact_entry(
                    artifact=RawDataFiles.SESSION_DESCRIPTOR.value,
                    path=session.descriptor_path,
                    required=True,
                ),
                _artifact_entry(
                    artifact=RawDataFiles.VR_CONFIGURATION.value,
                    path=session.vr_configuration_path,
                    required=vr_required,
                ),
                _artifact_entry(
                    artifact=RawDataFiles.EXPERIMENT_CONFIGURATION.value,
                    path=session.experiment_configuration_path,
                    required=False,
                ),
            ],
        }
        for session in instance.sessions
    ]


def _artifact_entry(artifact: str, path: Path, *, required: bool) -> dict[str, Any]:
    """Builds one inventory entry for a dataset artifact.

    Args:
        artifact: The canonical filename of the artifact.
        path: The resolved path the artifact occupies inside the dataset hierarchy.
        required: Determines whether the forging pipeline guarantees the artifact for this dataset.

    Returns:
        A dict with ``artifact``, ``path``, ``present``, and ``required`` keys.
    """
    return {"artifact": artifact, "path": str(path), "present": path.is_file(), "required": required}


def _load_dataset(dataset_path: str) -> tuple[DatasetData | None, dict[str, Any] | None]:
    """Resolves an input dataset path and loads the dataset it points at.

    Args:
        dataset_path: A path that points either at the dataset root or at the dataset's ``dataset.yaml`` marker.

    Returns:
        A tuple of the loaded ``DatasetData`` instance and an error dict. Exactly one element is non-None.
    """
    dataset_root, resolve_error = _resolve_dataset_root(dataset_path=dataset_path)
    if resolve_error is not None or dataset_root is None:
        message = f"Unable to resolve the dataset root from {dataset_path}."
        return None, resolve_error if resolve_error is not None else error_response(message=message)

    try:
        instance = DatasetData.load(dataset_path=dataset_root)
    except Exception as exception:
        message = f"Failed to load DatasetData from {dataset_root}: {exception}"
        return None, error_response(message=message)
    return instance, None


def _resolve_dataset_root(dataset_path: str) -> tuple[Path | None, dict[str, Any] | None]:
    """Resolves an input dataset path to its root directory (the directory holding the ``dataset.yaml`` marker).

    Accepts either the dataset root itself or its marker file and returns the canonical dataset root in both cases.

    Args:
        dataset_path: A path that points either at the dataset root or at the dataset's ``dataset.yaml`` marker.

    Returns:
        A tuple of the resolved dataset root Path and an error dict. Exactly one element is non-None.
    """
    path = Path(dataset_path)

    # Both resolution tests subsume the existence test, since neither can succeed for a path that does not exist. They
    # therefore run first, which resolves a healthy dataset with one metadata query instead of two and leaves the
    # existence query for the failure case, where it only chooses between the two error messages.
    if path.joinpath(DATASET_MARKER_FILENAME).is_file():
        return path, None
    if path.name == DATASET_MARKER_FILENAME and path.is_file():
        return path.parent, None
    if not path.exists():
        message = f"Unable to resolve the dataset root. The path {path} does not exist."
        return None, error_response(message=message)
    message = f"Unable to resolve the dataset root. No {DATASET_MARKER_FILENAME} marker was located under {path}."
    return None, error_response(message=message)
