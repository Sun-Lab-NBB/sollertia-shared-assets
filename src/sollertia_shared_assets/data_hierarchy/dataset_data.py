"""Provides the system-agnostic forged-dataset data hierarchy shared across all Sollertia platform machines."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from contextlib import suppress
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
    """The assembled per-session data feather written by the forging pipeline. The file is loadable by polars
    regardless of which columns it contains, which keeps the dataset system-agnostic at the data layer."""
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
        """Returns the path to the session's ``vr_configuration.yaml`` file within the dataset hierarchy, which only
        sessions that use VR carry, so callers should check ``.is_file()`` before reading.
        """
        return self.session_path.joinpath(RawDataFiles.VR_CONFIGURATION)

    @property
    def experiment_configuration_path(self) -> Path:
        """Returns the path to the session's ``experiment_configuration.yaml`` file within the dataset hierarchy,
        which only experiment session types carry, so callers should check ``.is_file()`` before reading.
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
    animals by the same acquisition system.

    Notes:
        Do not initialize this class directly. Instead, use the create() method when creating new datasets or the
        load() method when accessing data for an existing dataset.

        Datasets are created using a pre-filtered set of session + animal pairs, typically obtained through the session
        filtering functionality in sollertia-forgery. The dataset stores the assembled data together with the raw-data
        snapshots re-exported alongside it, leaving the sessions' ``raw_data`` and ``processed_data`` trees in place,
        because a dataset carries the forged output rather than a copy of its sources. Each created dataset carries a
        per-dataset ``data_descriptions.feather`` describing the meaning of every column its acquisition system can
        emit. Use column_descriptions() and get_column_description() to read it.
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
        """Resolves the session type and the acquisition system identifiers into their typed enumeration members.

        Notes:
            The conversion is unconditional, because ``SessionTypes`` and ``AcquisitionSystems`` are ``StrEnum``
            subclasses whose members are themselves strings and whose constructors accept an existing member. It is
            the only vocabulary gate for an instance rehydrated by ``load``, since no other method re-resolves either
            field. ``create`` screens both identifiers itself, before it creates any directory.

        Raises:
            ValueError: If the session type or the acquisition system falls outside the platform vocabulary.
        """
        self.session_type = SessionTypes(self.session_type)
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

            The creation is transactional. Every screen runs before the first directory is created, and any failure
            that lands between the first created directory and the marker write, an interrupt included, removes the
            dataset directory this call has built before the failure propagates. The dataset name therefore stays
            available for a corrected retry, instead of being held by a markerless tree that load() cannot read and
            that create() refuses as an already-existing dataset. The datasets root itself is left in place, since a
            caller that points at a missing root asks for that root to be created.

        Args:
            name: The unique name for the dataset. Must name a single directory under the datasets root.
            project: The name of the project from which the dataset's sessions originate.
            session_type: The type of data acquisition sessions included in the dataset.
            acquisition_system: The name of the data acquisition system used to acquire all sessions included in the
                dataset.
            sessions: The set of DatasetSession instances that identify the sessions whose data should be included in
                the dataset. The session_path attribute of each input instance is ignored and replaced with the
                resolved path inside the dataset hierarchy.
            datasets_root: The path to the root directory in which to create the dataset's hierarchy.
            column_descriptions: The mapping from each column name the dataset's acquisition system can emit into
                ``data.feather`` to its human-readable description. Written to the dataset root as
                ``data_descriptions.feather`` so consumers can interpret the assembled data. Every entry must bind a
                non-empty string column name to a non-empty string description. An empty mapping is valid and writes
                an empty companion feather.

        Returns:
            An initialized DatasetData instance that stores the structure and the metadata of the created dataset.

        Raises:
            ValueError: If the specified name does not name a single directory, or if the specified session_type or
                acquisition_system is not a valid enumeration member. Also raised if no sessions are provided, if the
                same animal and session pair is named more than once in the provided collection, or if any animal or
                session identifier does not name a single directory. Finally, raised if any column_descriptions entry
                binds a column name or a description that is not a non-empty string.
            FileExistsError: If a dataset with the same name already exists.
            OSError: If the dataset hierarchy cannot be materialized on disk. The part of the hierarchy this call has
                already built is removed before the error propagates.
            RuntimeError: If the hierarchy a failed creation has built cannot be removed from disk, since the dataset
                name then stays held by a tree no consumer can load.
        """
        # Screens the dataset name before it is joined onto the datasets root, since a name that carries a path
        # separator places the dataset somewhere other than directly under that root. Such a name also leaves the
        # intermediate directories behind when the rollback below removes the dataset directory alone.
        if not _is_path_component(value=name):
            message = (
                f"Unable to create a forged dataset. The name must be a non-empty string naming a single directory, "
                f"but got {name!r}."
            )
            console.error(message=message, error=ValueError)
        # Screens both vocabulary identifiers ahead of every other step, since the constructor call below resolves
        # them into enumeration members only after the dataset root and every per-session directory are already on
        # disk. Rejecting them here keeps an out-of-vocabulary request from leaking a hierarchy that then fails the
        # corrected retry as an already-existing dataset.
        if session_type not in SessionTypes:
            message = (
                f"Unable to create the '{name}' forged dataset. The session_type must be one of the SessionTypes "
                f"enumeration members, but got '{session_type}'."
            )
            console.error(message=message, error=ValueError)

        if acquisition_system not in AcquisitionSystems:
            message = (
                f"Unable to create the '{name}' forged dataset. The acquisition_system must be one of the "
                f"AcquisitionSystems enumeration members, but got '{acquisition_system}'."
            )
            console.error(message=message, error=ValueError)

        # Materializes the request before any screen reads it. A lazily evaluated iterable is truthy even when it
        # yields nothing, so it clears the emptiness guard below and is drained by the duplicate screen. The
        # materialization loop is then left with nothing to create, persisting a dataset that holds no session at all.
        # A tuple input pays nothing for the guarantee, since tuple() returns an existing tuple unchanged.
        sessions = tuple(sessions)

        if not sessions:
            message = (
                f"Unable to create the '{name}' forged dataset. The 'sessions' argument must contain at least one "
                f"DatasetSession instance, but got an empty collection."
            )
            console.error(message=message, error=ValueError)

        # Screens the request before touching the filesystem, so a rejected request leaves no dataset directory behind.
        # A set input does not dedupe on its own, since DatasetSession carries session_path into its hash.
        _screen_duplicate_sessions(
            sessions=sessions,
            existing_sessions=(),
            action=f"create the '{name}' forged dataset",
        )

        # Screens every identifier the hierarchy turns into a directory name, since an identifier that carries a path
        # separator or names the parent directory places its directory outside the dataset root. The rollback below
        # cannot reach such a directory, and remove_animal() would later delete whatever the joined path names.
        _screen_session_identifiers(sessions=sessions, action=f"create the '{name}' forged dataset")

        # Screens every description binding while the request is still pure, since the mapping becomes the dataset's
        # permanent interpretation contract that no later call repairs, and the writer below pins both feather columns
        # to pl.String. A non-string description reaches that writer as a raw polars error, while None is accepted
        # outright and persisted as a null no consumer can interpret. An empty name or description identifies no
        # column and describes nothing, and an empty mapping carries no entry to violate the rule, so it stays valid.
        invalid_descriptions = sorted(
            repr(column)
            for column, description in column_descriptions.items()
            if not isinstance(column, str) or not column or not isinstance(description, str) or not description
        )
        if invalid_descriptions:
            message = (
                f"Unable to create the '{name}' forged dataset. Every column_descriptions entry must bind a "
                f"non-empty string column name to a non-empty string description, but the following entries violate "
                f"this: {', '.join(invalid_descriptions)}."
            )
            console.error(message=message, error=ValueError)

        dataset_path = datasets_root.joinpath(name)

        # Prevents overwriting existing datasets.
        if dataset_path.exists():
            message = (
                f"Unable to create the '{name}' forged dataset. The destination directory must not exist, but a "
                f"dataset already exists at {dataset_path}."
            )
            console.error(message=message, error=FileExistsError)

        # Materializes the whole hierarchy under a single rollback, so the request either reaches its marker or
        # releases the dataset name it claimed. Only the mutations belong inside the block, since every screen above
        # runs against a destination this call does not own yet and a rejected request must never delete the
        # dataset with which it collided.
        try:
            # Creates the dataset root directory. Downstream consumers populate it with their own files. The kind of
            # the target is stated explicitly, since a dataset whose name carries a dot would otherwise be read as a
            # file path and only its parent would be created.
            ensure_directory_exists(path=dataset_path, is_file=False)

            resolved_sessions: list[DatasetSession] = []
            for session in sessions:
                session_path = dataset_path.joinpath(session.animal, session.session)
                ensure_directory_exists(path=session_path, is_file=False)
                resolved_sessions.append(
                    DatasetSession(session=session.session, animal=session.animal, session_path=session_path)
                )

            instance = cls(
                name=name,
                project=project,
                session_type=session_type,
                acquisition_system=acquisition_system,
                sessions=tuple(resolved_sessions),
                dataset_data_path=dataset_path.joinpath(DATASET_MARKER_FILENAME),
            )

            # Writes the per-dataset column-description binding so every consumer can interpret the assembled
            # feathers without depending on the acquisition system that produced them.
            instance._write_column_descriptions(column_descriptions=column_descriptions)

            # Publishes the dataset marker once every companion artifact it vouches for is on disk, so an interrupted
            # creation never leaves a discoverable dataset whose column descriptions are missing.
            instance.save()

        # Catches BaseException rather than Exception, since a Ctrl-C landing between the first directory and the
        # marker write leaves exactly the markerless, un-recreatable tree the rollback exists to prevent. The bare
        # re-raise below hands the interruption straight back to the caller, so nothing is suppressed.
        except BaseException:
            # The destination is this call's own to remove, since the screen above rejected the request when anything
            # occupied the path. A dangling symlink is the one occupant that screen admits, and is_dir() reports it as
            # absent in turn, so it survives the rollback instead of being unlinked. The same check skips the rollback
            # when the root directory never came to be.
            if dataset_path.is_dir():
                # Discards an OSError raised by the removal itself, so the caller still meets the failure that
                # interrupted the creation rather than a rollback-internal one. Both of delete_directory's failure
                # modes are then judged by the state of the destination below instead of by which one it took.
                with suppress(OSError):
                    delete_directory(directory_path=dataset_path)

                # Verifies the removal, since delete_directory reports an exhausted removal as a warning and returns
                # with the directory in place. A surviving hierarchy breaks the transactional guarantee this method
                # documents, and the console that warning goes to is disabled by default, so it is raised instead.
                if dataset_path.exists():
                    message = (
                        f"Unable to create the '{name}' forged dataset. The partially created hierarchy must be "
                        f"removed once the creation fails, but it is still present at {dataset_path}. Remove it "
                        f"manually before retrying, since create() refuses an existing destination directory."
                    )
                    console.error(message=message, error=RuntimeError)
            raise

        return instance

    @classmethod
    def load(cls, dataset_path: Path) -> DatasetData:
        """Loads the target dataset's data from the specified dataset.yaml file.

        Notes:
            To create a new dataset, use the create() method.

        Args:
            dataset_path: The path to the directory in which to search for the dataset.yaml file. Typically, this
                is the path to the root dataset directory.

        Returns:
            An initialized DatasetData instance that stores the loaded dataset's data.

        Raises:
            FileNotFoundError: If multiple or no 'dataset.yaml' file instances are found under the input directory.
            OSError: If the fallback scan encounters a directory it cannot read.
            ValueError: If the loaded marker carries a session type or an acquisition system outside the platform
                vocabulary.
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
            the updated dataset marker is written to disk, so the hierarchy and the marker stay consistent. A failure
            that lands before the marker write, an interrupt included, removes the directories this call created and
            restores the instance's session list to the state the marker on disk still describes. The identical call
            can therefore be retried once the cause of the failure is resolved. The session_path attribute of each input
            instance is ignored and replaced with the resolved path inside the dataset hierarchy, matching how
            create() treats its input.

            The method enforces the dataset's structural invariants alone. Deciding whether a session belongs in a
            given dataset, such as verifying its session type or its acquisition system, is left to the caller.

        Args:
            sessions: The DatasetSession instances that identify the sessions to add to the dataset.

        Returns:
            The added DatasetSession instances, each carrying its resolved path inside the dataset hierarchy.

        Raises:
            ValueError: If no sessions are provided, if any provided session is already part of the dataset or is
                repeated within the provided collection, or if any animal or session identifier does not name a
                single directory.
            OSError: If a session directory cannot be materialized on disk, or if the dataset marker cannot be
                written. The directories this call created are removed before the error propagates.
        """
        # Materializes the request before any screen reads it, the same guarantee create() makes. A lazily evaluated
        # iterable is truthy even when it yields nothing, so it clears the emptiness guard below and turns the call
        # into a silent no-op that still rewrites the dataset marker.
        sessions = tuple(sessions)

        if not sessions:
            message = (
                f"Unable to add sessions to the '{self.name}' forged dataset. The 'sessions' argument must contain "
                f"at least one DatasetSession instance, but got an empty collection."
            )
            console.error(message=message, error=ValueError)

        _screen_duplicate_sessions(
            sessions=sessions,
            existing_sessions=self.sessions,
            action=f"add sessions to the '{self.name}' forged dataset",
        )

        _screen_session_identifiers(
            sessions=sessions,
            action=f"add sessions to the '{self.name}' forged dataset",
        )

        dataset_path = self.dataset_data_path.parent
        added: list[DatasetSession] = []
        created_paths: list[Path] = []
        try:
            for session in sessions:
                session_path = dataset_path.joinpath(session.animal, session.session)

                # Records the directories this call has to create, so the rollback below removes exactly what this
                # call added and leaves an animal directory that already holds other sessions in place.
                created_paths.extend(path for path in (session_path.parent, session_path) if not path.exists())
                ensure_directory_exists(path=session_path, is_file=False)
                added.append(DatasetSession(session=session.session, animal=session.animal, session_path=session_path))

            self._commit_sessions(sessions=(*self.sessions, *added))

        # Catches BaseException rather than Exception, since a Ctrl-C landing inside the loop or inside the marker
        # write leaves the same directories behind that a failure does.
        except BaseException:
            # Removes the directories this call created, innermost first, so an abandoned request does not leave a
            # session directory the marker never comes to describe. A removal that fails is left alone, since the
            # directories are empty and the identical retry reclaims them.
            for path in reversed(created_paths):
                with suppress(OSError):
                    delete_directory(directory_path=path)
            raise

        return tuple(added)

    def remove_animal(self, animal: str) -> tuple[DatasetSession, ...]:
        """Removes the specified animal and every session it performed from the dataset.

        Notes:
            The removal counterpart to create(), which materializes the per-animal directories this method deletes.
            The animal's directory is removed from the dataset tree together with everything under it, including the
            assembled data of every session it holds and the per-animal artifacts co-located there. The updated dataset
            marker is written to disk once the directory is confirmed to be gone. An animal directory that is a symlink
            is unlinked in place, so the tree at which it points stays whole and only the dataset's reference to it is
            dropped. Pairing this method with add_sessions() rebuilds one animal while every other animal in the dataset
            keeps its data. A failed marker write restores the instance's session list to the state the marker on disk
            still describes, so the identical call can be retried once the cause of the failure is resolved.

        Args:
            animal: The unique identifier of the animal to remove from the dataset.

        Returns:
            The DatasetSession instances removed from the dataset.

        Raises:
            ValueError: If the specified animal is not part of the dataset, or if its identifier does not name a
                single directory.
            RuntimeError: If the animal's directory survives the removal attempt, since dropping the animal from the
                marker would stop the dataset from describing data that is still on disk.
            OSError: If the animal's directory tree cannot be read or removed, or if the dataset marker cannot be
                written. The instance's session list is restored to the state the marker on disk describes before the
                error propagates.
        """
        removed = self.get_sessions_for_animal(animal=animal)
        if not removed:
            message = (
                f"Unable to remove the animal '{animal}' from the '{self.name}' forged dataset. The animal must be "
                f"part of the dataset, but no sessions belonging to it were found."
            )
            console.error(message=message, error=ValueError)

        # Screens the identifier before it is joined onto the dataset root, since a marker written by a version that
        # predates the creation-time screen can still carry an identifier that resolves outside the animal's own
        # directory. The removal below deletes whatever the joined path names.
        if not _is_path_component(value=animal):
            message = (
                f"Unable to remove the animal '{animal}' from the '{self.name}' forged dataset. The animal "
                f"identifier must be a non-empty string naming a single directory, but got {animal!r}."
            )
            console.error(message=message, error=ValueError)

        # Clears the animal's directory before rewriting the marker, so an interrupted removal leaves a marker that
        # still describes the data present on disk. A symlink is tested for alongside the existence check, since
        # exists() follows the link and reports a link whose target is gone as an absent directory.
        animal_path = self.get_animal(animal=animal).animal_path
        if animal_path.exists() or animal_path.is_symlink():
            delete_directory(directory_path=animal_path)

        # Verifies the removal outside the guard above, since delete_directory reports an exhausted removal as a
        # warning and returns with the directory in place. A path the guard skips while it still holds an entry would
        # otherwise be dropped from the marker unexamined. Aborting before the marker is rewritten is what keeps the
        # marker describing the tree that is still on disk, and it leaves the call retryable.
        if animal_path.exists() or animal_path.is_symlink():
            message = (
                f"Unable to remove the animal '{animal}' from the '{self.name}' forged dataset. The animal's "
                f"directory must no longer exist once it is deleted, but it is still present at {animal_path}."
            )
            console.error(message=message, error=RuntimeError)

        self._commit_sessions(sessions=tuple(session for session in self.sessions if session.animal != animal))

        return removed

    @property
    def descriptions_path(self) -> Path:
        """Returns the path to this dataset's ``data_descriptions.feather`` file at the dataset root, resolved against
        the ``dataset.yaml`` file's filesystem location so the path remains portable across processing machines.
        """
        return self.dataset_data_path.parent.joinpath(DatasetFiles.DESCRIPTIONS)

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

        descriptions = pl.read_ipc(source=descriptions_path)
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
            Intended to run once the dataset is fully composed (every session's ``data.feather`` written), so an
            acquisition system that emits an undescribed column fails rather than producing a dataset whose assembled
            data cannot be fully interpreted.

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
            for column in pl.read_ipc_schema(source=data_path):
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
        """Returns one DatasetAnimal per unique animal in the dataset, each anchored on the ``dataset.yaml`` file's
        filesystem location so the result remains portable across processing machines.
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

    def _write_column_descriptions(self, column_descriptions: dict[str, str]) -> None:
        """Writes the per-dataset ``data_descriptions.feather`` mapping column names to descriptions.

        Notes:
            Assumes the mapping is already screened. The method's only caller is create(), which rejects a column name
            or a description that is not a non-empty string before the dataset directory exists, so the explicit
            pl.String schema below never receives a value it cannot store.

        Args:
            column_descriptions: The mapping from each column name to its human-readable description.
        """
        pl.DataFrame(
            data={"column": list(column_descriptions), "description": list(column_descriptions.values())},
            schema={"column": pl.String, "description": pl.String},
        ).write_ipc(file=self.descriptions_path)

    def _commit_sessions(self, sessions: tuple[DatasetSession, ...]) -> None:
        """Writes the provided session set to the dataset marker and keeps it only once the write succeeds.

        Notes:
            The mutator counterpart of save(). Since save() serializes the live instance, the new session set has to
            be installed before the marker is written, and the rollback below restores the previous set when the write
            fails. Without it, a failed write leaves the instance describing more or fewer sessions than the marker
            does, and the identical call is then refused, as a duplicate session by add_sessions() and as an unknown
            animal by remove_animal().

        Args:
            sessions: The DatasetSession instances the dataset holds once the marker write succeeds.
        """
        previous_sessions = self.sessions
        self.sessions = sessions
        try:
            self.save()

        # Catches BaseException rather than Exception, since a Ctrl-C landing inside the marker write leaves the same
        # divergence a failed write does. The bare re-raise hands the interruption straight back to the caller.
        except BaseException:
            self.sessions = previous_sessions
            raise


def _is_path_component(value: object) -> bool:
    """Returns True if the provided value is a string the dataset hierarchy can use as a single directory name.

    Notes:
        Every dataset name, animal identifier, and session identifier becomes one directory name under the datasets
        root. A value that is empty, that names the current or the parent directory, or that carries a path separator
        would therefore place its directory somewhere other than where the dataset marker records it. The check is
        delegated to Path, since it recognizes the separators and the drive syntax of the host platform rather than
        the POSIX ones alone. Path drops the current-directory reference from its parts, so only the parent-directory
        reference needs naming here.

    Args:
        value: The identifier to screen.

    Returns:
        True if the value names exactly one directory, False otherwise.
    """
    return isinstance(value, str) and value != ".." and Path(value).parts == (value,)


def _screen_session_identifiers(sessions: tuple[DatasetSession, ...], action: str) -> None:
    """Rejects a request whose animal or session identifier cannot serve as a single directory name.

    Notes:
        Screens the whole request before any directory is created, so a rejected request leaves the filesystem
        untouched. The screen is what keeps every session directory inside the dataset root. That containment is in
        turn what lets create() roll its hierarchy back by removing that one root, and what keeps remove_animal() from
        deleting a path outside the animal's own directory.

    Args:
        sessions: The DatasetSession instances the request adds to the dataset.
        action: The action clause that opens the error message, such as ``create the 'name' forged dataset``.

    Raises:
        ValueError: If any animal or session identifier does not name a single directory.
    """
    invalid_identifiers = sorted(
        {
            repr(identifier)
            for session in sessions
            for identifier in (session.animal, session.session)
            if not _is_path_component(value=identifier)
        }
    )
    if invalid_identifiers:
        message = (
            f"Unable to {action}. Every animal and session identifier must be a non-empty string naming a single "
            f"directory, but the following violate this: {', '.join(invalid_identifiers)}."
        )
        console.error(message=message, error=ValueError)


def _screen_duplicate_sessions(
    sessions: tuple[DatasetSession, ...],
    existing_sessions: tuple[DatasetSession, ...],
    action: str,
) -> None:
    """Rejects a request that names a session the dataset already holds or that repeats a session within itself.

    Notes:
        Screens the whole request before any directory is created, so a rejected request leaves the filesystem
        untouched.

    Args:
        sessions: The DatasetSession instances the request adds to the dataset.
        existing_sessions: The DatasetSession instances the dataset already holds.
        action: The action clause that opens the error message, such as ``create the 'name' forged dataset``.

    Raises:
        ValueError: If any requested session is already part of the dataset or is repeated within the request.
    """
    # Each screened pair joins the set, which also catches a request that names the same animal and session twice.
    known_sessions = {(session.animal, session.session) for session in existing_sessions}
    duplicates: list[str] = []
    for session in sessions:
        identity = (session.animal, session.session)
        if identity in known_sessions:
            duplicates.append(f"{session.animal}/{session.session}")
        known_sessions.add(identity)

    if duplicates:
        message = (
            f"Unable to {action}. Every added session must be absent from the dataset and named once in the request, "
            f"but the following violate this: {', '.join(sorted(duplicates))}."
        )
        console.error(message=message, error=ValueError)
