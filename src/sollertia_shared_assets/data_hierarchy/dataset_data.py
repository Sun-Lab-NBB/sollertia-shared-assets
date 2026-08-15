"""Provides the system-agnostic forged-dataset data hierarchy shared across all Sollertia platform machines.

A forged dataset aggregates multiple data acquisition sessions of the same type, recorded across different animals
by the same acquisition system, into a single system-agnostic self-contained hierarchy. The dataset is system-agnostic
at the data layer: every session's assembled ``data.feather`` can be loaded by polars regardless of which columns it
contains.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass

import polars as pl
from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import (
    YAML_EXCLUDE_METADATA,
    YamlConfig,
    delete_directory,
    discover_marker_files,
)

from ..enums import SessionTypes, AcquisitionSystems
from .session_data import RawDataFiles
from .project_hierarchy import DATASET_MARKER_FILENAME


class DatasetFiles(StrEnum):
    """Enumerates the canonical, system-agnostic filenames written into a forged dataset hierarchy.

    Notes:
        Centralizes the dataset filenames so new artifacts can be added in one place and referenced symbolically
        from path-resolution properties on DatasetData, DatasetSession, and DatasetAnimal. Two universal output
        contracts live here: every system's forged session writes a per-session ``data.feather``, and every forged
        dataset carries a single per-dataset ``data_descriptions.feather`` mapping each emittable column name to its
        human-readable description. Shared raw-data assets re-exported alongside the data keep their canonical
        ``RawDataFiles`` names: the session descriptor, VR configuration, and experiment configuration at session
        granularity, and the per-animal surgery metadata at animal granularity. The session descriptor is universal,
        but the VR and experiment configurations are present only for the session types that carry them (sessions that
        use VR and experiment sessions, respectively), so a forged session exposes whichever subset it actually holds.
    """

    DATA = "data.feather"
    """The assembled per-session data feather written by the forging pipeline."""
    DESCRIPTIONS = "data_descriptions.feather"
    """The per-dataset companion feather mapping each column name in ``data.feather`` to its description. Written once
    at the dataset root, since every session in a dataset shares the same data format."""


@dataclass(frozen=True, slots=True)
class DatasetSession:
    """Defines a single session included in a forged dataset.

    Combines the session identity metadata with the resolved path to the session's directory within the dataset
    hierarchy.
    """

    session: str
    """The unique identifier of the session. Session names follow the format 'YYYY-MM-DD-HH-MM-SS-microseconds' and
    encode the session's acquisition timestamp.
    """
    animal: str
    """The unique identifier of the animal that participated in the session."""
    session_path: Path = field(default=Path(), metadata=YAML_EXCLUDE_METADATA)
    """The path to the session's directory within the dataset hierarchy (dataset/animal/session). Kept out of the
    written marker, since ``DatasetData.load`` re-resolves it from the marker's own on-disk location."""

    @property
    def data_path(self) -> Path:
        """Returns the path to the session's assembled ``data.feather`` file within the dataset hierarchy."""
        return self.session_path.joinpath(DatasetFiles.DATA)

    @property
    def descriptor_path(self) -> Path:
        """Returns the path to the session's ``session_descriptor.yaml`` file within the dataset hierarchy."""
        return self.session_path.joinpath(RawDataFiles.SESSION_DESCRIPTOR)

    @property
    def vr_configuration_path(self) -> Path:
        """Returns the path to the session's ``vr_configuration.yaml`` file within the dataset hierarchy.

        Only sessions that use VR carry this asset, so callers should check ``.is_file()`` before reading.
        """
        return self.session_path.joinpath(RawDataFiles.VR_CONFIGURATION)

    @property
    def experiment_configuration_path(self) -> Path:
        """Returns the path to the session's ``experiment_configuration.yaml`` file within the dataset hierarchy.

        Only experiment session types carry this asset, so callers should check ``.is_file()`` before reading.
        """
        return self.session_path.joinpath(RawDataFiles.EXPERIMENT_CONFIGURATION)


@dataclass(frozen=True, slots=True)
class DatasetAnimal:
    """Defines a single animal included in a forged dataset.

    Combines the animal identity metadata with the resolved path to the animal's directory within the dataset
    hierarchy. Per-animal artifacts (such as surgery metadata) are co-located in this directory and exposed as derived
    properties.
    """

    animal: str
    """The unique identifier of the animal."""
    animal_path: Path = Path()
    """The path to the animal's directory within the dataset hierarchy (dataset/animal)."""

    @property
    def surgery_path(self) -> Path:
        """Returns the path to the animal's ``surgery_metadata.yaml`` file within the dataset hierarchy."""
        return self.animal_path.joinpath(RawDataFiles.SURGERY_METADATA)


@dataclass
class DatasetData(YamlConfig):
    """Defines the structure and the metadata of a forged dataset.

    A forged dataset aggregates multiple data acquisition sessions of the same type, recorded across different
    animals by the same acquisition system. This class encapsulates the information necessary to access the dataset's
    assembled (forged) data stored on disk and functions as the entry point for all interactions with the dataset.

    Notes:
        Do not initialize this class directly. Instead, use the create() method when creating new datasets or the
        load() method when accessing data for an existing dataset.

        Datasets are created using a pre-filtered set of session + animal pairs, typically obtained through the
        session filtering functionality in sollertia-forgery. The dataset stores only the assembled data, not raw or
        processed data. Each created dataset carries a per-dataset ``data_descriptions.feather`` describing the
        meaning of every column its acquisition system can emit; use column_descriptions() and
        get_column_description() to read it.
    """

    name: str
    """The unique name of the dataset."""
    project: str
    """The name of the project from which the dataset's sessions originate."""
    session_type: str | SessionTypes
    """The type of data acquisition sessions included in the dataset. All sessions in a dataset must be of the
    same type.
    """
    acquisition_system: str | AcquisitionSystems
    """The name of the data acquisition system used to acquire all sessions in the dataset."""
    sessions: tuple[DatasetSession, ...] = field(default_factory=tuple)
    """The DatasetSession instances that identify and locate each session included in the dataset."""
    dataset_data_path: Path = field(default=Path(), metadata=YAML_EXCLUDE_METADATA)
    """The resolved path to this dataset's ``dataset.yaml`` file. Kept out of the written marker and re-derived from
    the YAML's on-disk location on load, so the dataset remains portable across machines."""

    def __post_init__(self) -> None:
        """Ensures that all fields used to define the dataset are properly initialized."""
        # Converts string values loaded from YAML to proper enum types.
        if isinstance(self.session_type, str):
            self.session_type = SessionTypes(self.session_type)
        if isinstance(self.acquisition_system, str):
            self.acquisition_system = AcquisitionSystems(self.acquisition_system)

    @classmethod
    def create(
        cls,
        name: str,
        project: str,
        session_type: str | SessionTypes,
        acquisition_system: str | AcquisitionSystems,
        sessions: tuple[DatasetSession, ...] | set[DatasetSession],
        datasets_root: Path,
        column_descriptions: dict[str, str],
    ) -> DatasetData:
        """Creates a new forged dataset and initializes its data structure on disk.

        Notes:
            To access the data of an already existing dataset, use the load() method.

        Args:
            name: The unique name for the dataset.
            project: The name of the project from which the dataset's sessions originate.
            session_type: The type of data acquisition sessions included in the dataset.
            acquisition_system: The name of the data acquisition system used to acquire all sessions included in the
                dataset.
            sessions: The set of DatasetSession instances that identify the sessions whose data should be included in
                the dataset. The session_path attribute of each input instance is ignored and replaced with the
                resolved path inside the dataset hierarchy.
            datasets_root: The path to the root directory where to create the dataset's hierarchy.
            column_descriptions: The mapping from each column name the dataset's acquisition system can emit into
                ``data.feather`` to its human-readable description. Written to the dataset root as
                ``data_descriptions.feather`` so consumers can interpret the assembled data.

        Returns:
            An initialized DatasetData instance that stores the structure and the metadata of the created dataset.

        Raises:
            ValueError: If no sessions are provided.
            FileExistsError: If a dataset with the same name already exists.
        """
        # Converts sessions to tuple if provided as set.
        if isinstance(sessions, set):
            sessions = tuple(sessions)

        if not sessions:
            message = (
                f"Unable to create the '{name}' forged dataset. The 'sessions' argument must contain at least one "
                f"DatasetSession instance, but got an empty collection."
            )
            console.error(message=message, error=ValueError)

        # Constructs the dataset root directory path.
        dataset_path = datasets_root.joinpath(name)

        # Prevents overwriting existing datasets.
        if dataset_path.exists():
            message = (
                f"Unable to create the '{name}' forged dataset. The destination directory must not exist, but a "
                f"dataset already exists at {dataset_path}."
            )
            console.error(message=message, error=FileExistsError)

        # Creates the dataset root directory. Downstream consumers populate it with their own files. The kind of the
        # target is stated explicitly, since a dataset whose name carries a dot would otherwise be read as a file
        # path and only its parent would be created.
        ensure_directory_exists(path=dataset_path, is_file=False)

        # Creates animal/session subdirectories and rebuilds each session with its resolved path.
        resolved_sessions: list[DatasetSession] = []
        for session in sessions:
            session_path = dataset_path.joinpath(session.animal, session.session)
            ensure_directory_exists(path=session_path, is_file=False)
            resolved_sessions.append(
                DatasetSession(session=session.session, animal=session.animal, session_path=session_path)
            )

        # Generates the DatasetData instance.
        instance = cls(
            name=name,
            project=project,
            session_type=session_type,
            acquisition_system=acquisition_system,
            sessions=tuple(resolved_sessions),
            dataset_data_path=dataset_path.joinpath(DATASET_MARKER_FILENAME),
        )

        # Saves the configured instance data to disk.
        instance.save()

        # Writes the per-dataset column-description binding alongside the marker so every consumer can interpret the
        # assembled feathers without depending on the acquisition system that produced them.
        instance._write_column_descriptions(column_descriptions=column_descriptions)

        return instance

    @classmethod
    def load(cls, dataset_path: Path) -> DatasetData:
        """Loads the target dataset's data from the specified dataset.yaml file.

        Notes:
            To create a new dataset, use the create() method.

        Args:
            dataset_path: The path to the directory where to search for the dataset.yaml file. Typically, this
                is the path to the root dataset directory.

        Returns:
            An initialized DatasetData instance that stores the loaded dataset's data.

        Raises:
            FileNotFoundError: If multiple or no 'dataset.yaml' file instances are found under the input directory.
            OSError: If the fallback scan encounters a directory it cannot read.
        """
        # Resolves the marker at its canonical location first, so loading a dataset that holds many assembled session
        # feathers costs a single metadata query instead of a recursive walk of the whole dataset tree. The scan below
        # still covers a caller that points at a directory other than the dataset root.
        canonical_marker = dataset_path.joinpath(DATASET_MARKER_FILENAME)
        if canonical_marker.is_file():
            dataset_data_path = canonical_marker
        else:
            candidates = (
                discover_marker_files(directory=dataset_path, marker_name=DATASET_MARKER_FILENAME)
                if dataset_path.is_dir()
                else []
            )
            if len(candidates) != 1:
                message = (
                    f"Unable to load the target dataset's data. Expected a single dataset.yaml file to be located "
                    f"under the directory tree specified by the input path: {dataset_path}. Instead, encountered "
                    f"{len(candidates)} candidate files. This indicates that the input path does not point to a "
                    f"valid dataset data hierarchy."
                )
                console.error(message=message, error=FileNotFoundError)
            dataset_data_path = candidates[0]

        # Loads the dataset's data from the .yaml file.
        instance: DatasetData = cls.from_yaml(file_path=dataset_data_path)

        # Re-resolves the dataset_data_path and each session's session_path against the YAML file's filesystem
        # location so the dataset remains portable across processing machines.
        local_root = dataset_data_path.parent
        instance.dataset_data_path = dataset_data_path
        instance.sessions = tuple(
            DatasetSession(
                session=session.session,
                animal=session.animal,
                session_path=local_root.joinpath(session.animal, session.session),
            )
            for session in instance.sessions
        )

        return instance

    def save(self) -> None:
        """Caches the instance's data to the dataset's root directory as a 'dataset.yaml' file."""
        self.to_yaml(file_path=self.dataset_data_path)

    def add_sessions(self, sessions: tuple[DatasetSession, ...] | set[DatasetSession]) -> tuple[DatasetSession, ...]:
        """Adds the specified sessions to the dataset and materializes their directories in the dataset hierarchy.

        Notes:
            The append counterpart to create(). Each added session's directory is created under the dataset root and
            the updated dataset marker is written to disk, so the hierarchy and the marker stay consistent. The
            session_path attribute of each input instance is ignored and replaced with the resolved path inside the
            dataset hierarchy, matching how create() treats its input.

            The method enforces the dataset's structural invariants alone. Deciding whether a session belongs in a
            given dataset, such as verifying its session type or its acquisition system, is left to the caller.

        Args:
            sessions: The DatasetSession instances that identify the sessions to add to the dataset.

        Returns:
            The added DatasetSession instances, each carrying its resolved path inside the dataset hierarchy.

        Raises:
            ValueError: If no sessions are provided, or if any provided session is already part of the dataset or is
                repeated within the provided collection.
        """
        # Converts sessions to tuple if provided as set.
        if isinstance(sessions, set):
            sessions = tuple(sessions)

        if not sessions:
            message = (
                f"Unable to add sessions to the '{self.name}' forged dataset. The 'sessions' argument must contain "
                f"at least one DatasetSession instance, but got an empty collection."
            )
            console.error(message=message, error=ValueError)

        # Screens the whole request against the dataset's membership before creating any directory, so a rejected
        # request leaves the hierarchy untouched. Each accepted pair joins the set, which also catches a request that
        # names the same animal and session twice.
        known_sessions = {(session.animal, session.session) for session in self.sessions}
        duplicates: list[str] = []
        for session in sessions:
            identity = (session.animal, session.session)
            if identity in known_sessions:
                duplicates.append(f"{session.animal}/{session.session}")
            known_sessions.add(identity)

        if duplicates:
            message = (
                f"Unable to add sessions to the '{self.name}' forged dataset. Every added session must be absent "
                f"from the dataset and named once in the request, but the following violate this: "
                f"{', '.join(sorted(duplicates))}."
            )
            console.error(message=message, error=ValueError)

        # Creates each added session's subdirectory and rebuilds the session with its resolved path.
        dataset_path = self.dataset_data_path.parent
        added: list[DatasetSession] = []
        for session in sessions:
            session_path = dataset_path.joinpath(session.animal, session.session)
            ensure_directory_exists(path=session_path, is_file=False)
            added.append(DatasetSession(session=session.session, animal=session.animal, session_path=session_path))

        self.sessions = (*self.sessions, *added)
        self.save()

        return tuple(added)

    def remove_animal(self, animal: str) -> tuple[DatasetSession, ...]:
        """Removes the specified animal and every session it performed from the dataset.

        Notes:
            The removal counterpart to create(), which materializes the per-animal directories this method deletes.
            The animal's directory is removed together with everything under it, including the assembled data of every
            session it holds and the per-animal artifacts co-located there, and the updated dataset marker is written
            to disk. Pairing this method with add_sessions() rebuilds one animal while every other animal in the
            dataset keeps its data.

        Args:
            animal: The unique identifier of the animal to remove from the dataset.

        Returns:
            The DatasetSession instances removed from the dataset.

        Raises:
            ValueError: If the specified animal is not part of the dataset.
        """
        removed = self.get_sessions_for_animal(animal)
        if not removed:
            message = (
                f"Unable to remove the animal '{animal}' from the '{self.name}' forged dataset. The animal must be "
                f"part of the dataset, but no sessions belonging to it were found."
            )
            console.error(message=message, error=ValueError)

        # Clears the animal's directory before rewriting the marker, so an interrupted removal leaves a marker that
        # still describes the data present on disk.
        animal_path = self.get_animal(animal).animal_path
        if animal_path.is_dir():
            delete_directory(directory_path=animal_path)

        self.sessions = tuple(session for session in self.sessions if session.animal != animal)
        self.save()

        return removed

    @property
    def descriptions_path(self) -> Path:
        """Returns the path to this dataset's ``data_descriptions.feather`` file at the dataset root.

        Resolved against the ``dataset.yaml`` file's filesystem location so the path remains portable across
        processing machines.
        """
        return self.dataset_data_path.parent.joinpath(DatasetFiles.DESCRIPTIONS)

    def _write_column_descriptions(self, column_descriptions: dict[str, str]) -> None:
        """Writes the per-dataset ``data_descriptions.feather`` mapping column names to descriptions.

        Args:
            column_descriptions: The mapping from each column name to its human-readable description.
        """
        pl.DataFrame(
            {"column": list(column_descriptions), "description": list(column_descriptions.values())},
            schema={"column": pl.String, "description": pl.String},
        ).write_ipc(file=self.descriptions_path)

    def column_descriptions(self) -> dict[str, str]:
        """Returns the mapping from each column name in the dataset's ``data.feather`` to its description.

        Reads the per-dataset ``data_descriptions.feather`` companion file written at dataset creation. Every forged
        dataset is required to carry this file, so its absence indicates a malformed or incomplete dataset.

        Returns:
            The ordered mapping from each column name the acquisition system can emit to its human-readable
            description.

        Raises:
            FileNotFoundError: If the dataset's ``data_descriptions.feather`` companion file does not exist.
        """
        descriptions_path = self.descriptions_path
        if not descriptions_path.is_file():
            message = (
                f"Unable to read the column descriptions for the '{self.name}' dataset. Every forged dataset must "
                f"carry a '{DatasetFiles.DESCRIPTIONS}' companion file at its root, but none was found at "
                f"'{descriptions_path}'."
            )
            console.error(message=message, error=FileNotFoundError)

        descriptions = pl.read_ipc(descriptions_path)
        return dict(zip(descriptions["column"], descriptions["description"], strict=True))

    def get_column_description(self, column: str) -> str:
        """Returns the description for a single column in the dataset's ``data.feather``.

        Args:
            column: The name of the column whose description to look up.

        Returns:
            The human-readable description of the specified column.

        Raises:
            FileNotFoundError: If the dataset's ``data_descriptions.feather`` companion file does not exist.
            ValueError: If the specified column has no description recorded for this dataset.
        """
        descriptions = self.column_descriptions()
        if column not in descriptions:
            message = (
                f"Unable to look up the description for the column '{column}'. The column must be described in the "
                f"'{self.name}' dataset's '{DatasetFiles.DESCRIPTIONS}' companion file, but no matching entry was "
                f"found."
            )
            console.error(message=message, error=ValueError)
            # Unreachable: console.error() is NoReturn, but ruff cannot trace NoReturn through method calls (RET503).
            raise ValueError(message)  # pragma: no cover

        return descriptions[column]

    def verify_data_descriptions(self) -> None:
        """Verifies that every column written into any session's ``data.feather`` is described by the dataset.

        Reads the per-dataset ``data_descriptions.feather`` mapping, then scans the schema of every session's
        assembled ``data.feather`` (without loading the data) and confirms each column name appears in the mapping.
        The contract is one-directional: a described column that no session emits is permitted (columns can be
        conditionally emitted), but a column written into a session's feather with no matching description is a
        violation.

        Notes:
            Intended to run once the dataset is fully composed (every session's ``data.feather`` written). The
            forging pipeline invokes it after assembly so an acquisition system that emits an undescribed column
            fails the run rather than producing a dataset whose assembled data cannot be fully interpreted.

        Raises:
            FileNotFoundError: If the dataset's ``data_descriptions.feather`` companion file does not exist, or if
                any session's ``data.feather`` file does not exist.
            ValueError: If any session's ``data.feather`` contains a column with no description recorded for this
                dataset. The error names every undescribed column together with the sessions that emit it.
        """
        described_columns = set(self.column_descriptions())

        # Maps each undescribed column to the sessions that emit it, so a single error reports every offending
        # (column, session) pairing rather than aborting on the first violation.
        undescribed: dict[str, list[str]] = {}
        for session in self.sessions:
            data_path = session.data_path
            if not data_path.is_file():
                message = (
                    f"Unable to verify the column descriptions for the '{self.name}' dataset. The session "
                    f"'{session.session}' (animal '{session.animal}') does not have an assembled "
                    f"'{DatasetFiles.DATA}' file at '{data_path}'."
                )
                console.error(message=message, error=FileNotFoundError)

            # ``read_ipc_schema`` reads only the Arrow IPC schema from the file footer, so the column names are
            # resolved without materializing any of the session's data.
            for column in pl.read_ipc_schema(data_path):
                if column not in described_columns:
                    undescribed.setdefault(column, []).append(session.session)

        if undescribed:
            offenders = "; ".join(
                f"'{column}' (emitted by {', '.join(sorted(sessions))})"
                for column, sessions in sorted(undescribed.items())
            )
            message = (
                f"Unable to verify the column descriptions for the '{self.name}' dataset. Every column written into "
                f"a session's '{DatasetFiles.DATA}' must have a matching description in the dataset's "
                f"'{DatasetFiles.DESCRIPTIONS}' companion file, but the following columns are undescribed: "
                f"{offenders}."
            )
            console.error(message=message, error=ValueError)

    @property
    def animals(self) -> tuple[DatasetAnimal, ...]:
        """Returns a tuple of DatasetAnimal instances, one per unique animal in the dataset.

        Each instance carries the animal identifier and the resolved path to the animal's directory under
        the dataset root, anchored on the ``dataset.yaml`` file's filesystem location so the result remains
        portable across processing machines.
        """
        dataset_root = self.dataset_data_path.parent
        unique_animals = sorted({session.animal for session in self.sessions})
        return tuple(
            DatasetAnimal(animal=animal, animal_path=dataset_root.joinpath(animal)) for animal in unique_animals
        )

    def get_animal(self, animal: str) -> DatasetAnimal:
        """Returns the DatasetAnimal instance for the specified animal identifier.

        Args:
            animal: The unique identifier of the animal to look up.

        Returns:
            The DatasetAnimal instance carrying the animal identity metadata and the path to the animal's
            directory within the dataset hierarchy.

        Raises:
            ValueError: If the specified animal is not found in the dataset.
        """
        # Tests membership against the session list directly and builds the one requested instance, since resolving a
        # single animal through the ``animals`` property would sort every distinct name and construct every other
        # DatasetAnimal only to discard them.
        if any(session.animal == animal for session in self.sessions):
            return DatasetAnimal(animal=animal, animal_path=self.dataset_data_path.parent.joinpath(animal))

        message = (
            f"Unable to look up the animal '{animal}'. The animal must exist in the '{self.name}' dataset, "
            f"but no matching DatasetAnimal was found."
        )
        console.error(message=message, error=ValueError)
        # Unreachable: console.error() is NoReturn, but ruff cannot trace NoReturn through method calls (RET503).
        raise ValueError(message)  # pragma: no cover

    def get_sessions_for_animal(self, animal: str) -> tuple[DatasetSession, ...]:
        """Returns the DatasetSession instances for all sessions performed by the specified animal.

        Args:
            animal: The unique identifier of the animal for which to retrieve the session data.

        Returns:
            A tuple of DatasetSession instances for the specified animal.
        """
        return tuple(session for session in self.sessions if session.animal == animal)

    def get_session(self, animal: str, session: str) -> DatasetSession:
        """Returns the DatasetSession instance for the specified animal and session pair.

        Args:
            animal: The unique identifier of the animal that participated in the session.
            session: The unique identifier of the session to look up.

        Returns:
            The DatasetSession instance containing the session identity metadata and the path to the session's
            directory within the dataset hierarchy.

        Raises:
            ValueError: If the specified animal and session combination is not found in the dataset.
        """
        for candidate in self.sessions:
            if candidate.animal == animal and candidate.session == session:
                return candidate

        message = (
            f"Unable to look up the session '{session}' performed by the animal '{animal}'. The animal and "
            f"session combination must exist in the '{self.name}' dataset, but no matching DatasetSession was found."
        )
        console.error(message=message, error=ValueError)
        # Unreachable: console.error() is NoReturn, but ruff cannot trace NoReturn through method calls (RET503).
        raise ValueError(message)  # pragma: no cover
