"""Provides assets for maintaining the Sollertia platform analysis dataset data hierarchy across all processing
machines.
"""

import copy
from pathlib import Path
from dataclasses import field, dataclass

import polars as pl
from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from .session_data import SessionTypes
from ..configuration import AcquisitionSystems


@dataclass(frozen=True)
class SessionMetadata:
    """Encapsulates the identity metadata for a single data acquisition session.

    This class is used to identify sessions included in an analysis dataset. It provides the minimum information
    necessary to locate and access the session's data within a project's data hierarchy.
    """

    session: str
    """The unique identifier of the session. Session names follow the format 'YYYY-MM-DD-HH-MM-SS-microseconds' and
    encode the session's acquisition timestamp."""
    animal: str
    """The unique identifier of the animal that participated in the session."""


@dataclass
class DatasetSessionData:
    """Provides the paths and access to the assembled data files for a single session within the dataset.

    Notes:
        Each session in the dataset has its own directory containing the forged data and metadata feather files, in
        addition to other supplementary data files.

        As part of loading the data, this class memory-maps the .feather files to Polars dataframes for efficient
        access.
    """

    session_path: Path = Path()
    """The path to the session's directory within the dataset hierarchy (dataset/animal/session)."""
    data_path: Path = Path()
    """The path to the data.feather file containing the assembled and time-aligned session-specific dataset."""
    metadata_path: Path = Path()
    """The path to the metadata.feather file containing session's metadata."""
    data: pl.DataFrame | None = None
    """The Polars dataframe that stores the session's data memory-mapped from the dataset .feather file."""
    metadata: pl.DataFrame | None = None
    """The Polars dataframe that stores the session's metadata memory-mapped from the metadata .feather file."""

    def resolve_paths(self, session_directory: Path) -> None:
        """Resolves all paths managed by the class instance.

        Args:
            session_directory: The path to the session's directory within the dataset hierarchy.
        """
        self.session_path = session_directory
        self.data_path = session_directory.joinpath("data.feather")
        self.metadata_path = session_directory.joinpath("metadata.feather")

    def make_directories(self) -> None:
        """Ensures that the session directory exists, creating it if missing."""
        ensure_directory_exists(self.session_path)

    def load_data(self) -> None:
        """Loads the session's data by memory-mapping its feather files as Polars dataframes."""
        if self.data_path.exists():
            self.data = pl.read_ipc(source=self.data_path, use_pyarrow=True, memory_map=True, rechunk=True)
        if self.metadata_path.exists():
            self.metadata = pl.read_ipc(source=self.metadata_path, use_pyarrow=True, memory_map=True, rechunk=True)

    def release_data(self) -> None:
        """Releases the memory-mapped dataframes by setting them to None."""
        self.data = None
        self.metadata = None


@dataclass
class DatasetData(YamlConfig):
    """Defines the structure and the metadata of an analysis dataset.

    An analysis dataset aggregates multiple data acquisition sessions of the same type, recorded across different
    animals by the same acquisition system. This class encapsulates the information necessary to access the dataset's
    assembled (forged) data stored on disk and functions as the entry point for all interactions with the dataset.

    Notes:
        Do not initialize this class directly. Instead, use the create() method when creating new datasets or the
        load() method when accessing data for an existing dataset.

        Datasets are created using a pre-filtered set of session + animal pairs, typically obtained through the
        session filtering functionality in sollertia-forgery. The dataset stores only the assembled data, not raw or
        processed data.
    """

    name: str
    """The unique name of the dataset."""
    project: str
    """The name of the project from which the dataset's sessions originate."""
    session_type: str | SessionTypes
    """The type of data acquisition sessions included in the dataset. All sessions in a dataset must be of the
    same type."""
    acquisition_system: str | AcquisitionSystems
    """The name of the data acquisition system used to acquire all sessions in the dataset."""
    sessions: tuple[SessionMetadata, ...] = field(default_factory=tuple)
    """Stores the SessionMetadata instances that define the metadata used to identify each session included in the
    dataset."""
    dataset_data_path: Path = field(default_factory=Path)
    """The path to the dataset.yaml file cached to disk."""
    _session_data_cache: dict[str, DatasetSessionData] = field(default_factory=dict, repr=False)
    """Stores initialized DatasetSessionData instances for each included session, keyed by 'animal/session'. Use
    the get_session_data() method to access session data."""

    def __post_init__(self) -> None:
        """Validates and initializes the dataset configuration."""
        # Ensures enumeration-mapped arguments are stored as proper enumeration types.
        if isinstance(self.session_type, str):
            self.session_type = SessionTypes(self.session_type)
        if isinstance(self.acquisition_system, str):
            self.acquisition_system = AcquisitionSystems(self.acquisition_system)

        # Ensures that the sessions field is a tuple of SessionMetadata instances.
        if self.sessions and not isinstance(self.sessions[0], SessionMetadata):
            # noinspection PyUnresolvedReferences
            self.sessions = tuple(SessionMetadata(session=s["session"], animal=s["animal"]) for s in self.sessions)

    @classmethod
    def create(
        cls,
        name: str,
        project: str,
        session_type: SessionTypes | str,
        acquisition_system: AcquisitionSystems | str,
        sessions: tuple[SessionMetadata, ...] | set[SessionMetadata],
        datasets_root: Path,
    ) -> DatasetData:
        """Creates a new analysis dataset and initializes its data structure on disk.

        Notes:
            To access the data of an already existing dataset, use the load() method.

        Args:
            name: The unique name for the dataset.
            project: The name of the project from which the dataset's sessions originate.
            session_type: The type of data acquisition sessions included in the dataset.
            acquisition_system: The name of the data acquisition system used to acquire all sessions included in the
                dataset.
            sessions: The set of SessionMetadata instances that define the sessions whose data should be included in
                the dataset.
            datasets_root: The path to the root directory where to create the dataset's hierarchy.

        Returns:
            An initialized DatasetData instance that stores the structure and the metadata of the created dataset.

        Raises:
            ValueError: If the session_type or acquisition_system is invalid, or if no sessions are provided.
            FileExistsError: If a dataset with the same name already exists.
        """
        # Validates inputs
        if isinstance(session_type, str):
            session_type = SessionTypes(session_type)
        if isinstance(acquisition_system, str):
            acquisition_system = AcquisitionSystems(acquisition_system)

        # Converts sessions to tuple if provided as set
        if isinstance(sessions, set):
            sessions = tuple(sessions)

        if not sessions:
            message = (
                f"Unable to create the '{name}' analysis dataset, as no sessions were provided to the creation method "
                f"via the 'sessions' argument."
            )
            console.error(message=message, error=ValueError)
            raise ValueError(message)  # Fallback for mypy

        # Constructs the dataset root directory path
        dataset_path = datasets_root.joinpath(name)

        # Prevents overwriting existing datasets
        if dataset_path.exists():
            message = (
                f"Unable to create the '{name}' analysis dataset. A dataset with this name already exists at "
                f"{dataset_path}. Use a different name or delete the existing dataset before creating a new one with "
                f"the same name."
            )
            console.error(message=message, error=FileExistsError)
            raise FileExistsError(message)  # Fallback for mypy

        # Creates the dataset root directory. Processing trackers (.yaml and .lock files) are written directly into
        # this root by downstream forging and multi-day pipelines.
        ensure_directory_exists(dataset_path)

        # Creates animal/session subdirectories and initializes session data instances
        _session_data_cache: dict[str, DatasetSessionData] = {}
        for session_meta in sessions:
            session_dir = dataset_path.joinpath(session_meta.animal, session_meta.session)

            session_data = DatasetSessionData()
            session_data.resolve_paths(session_directory=session_dir)
            session_data.make_directories()

            cache_key = f"{session_meta.animal}/{session_meta.session}"
            _session_data_cache[cache_key] = session_data

        # Generates the DatasetData instance
        instance = cls(
            name=name,
            project=project,
            session_type=session_type,
            acquisition_system=acquisition_system,
            sessions=sessions,
            dataset_data_path=dataset_path.joinpath("dataset.yaml"),
            _session_data_cache=_session_data_cache,
        )

        # Saves the configured instance data to disk
        instance.save()

        return instance

    @classmethod
    def load(cls, dataset_path: Path) -> DatasetData:
        """Loads the target dataset's data from the specified dataset.yaml file.

        Notes:
            To create a new dataset, use the create() method.

            This method memory-maps the data.feather and metadata.feather files for each loaded session as Polars
            dataframes.

        Args:
            dataset_path: The path to the directory where to search for the dataset.yaml file. Typically, this
                is the path to the root dataset directory.

        Returns:
            An initialized DatasetData instance that stores the loaded dataset's data.

        Raises:
            FileNotFoundError: If multiple or no 'dataset.yaml' file instances are found under the input directory.
        """
        # Locates the dataset.yaml file
        dataset_data_files = list(dataset_path.rglob("dataset.yaml"))
        if len(dataset_data_files) != 1:
            message = (
                f"Unable to load the target dataset's data. Expected a single dataset.yaml file to be located "
                f"under the directory tree specified by the input path: {dataset_path}. Instead, encountered "
                f"{len(dataset_data_files)} candidate files. This indicates that the input path does not point to a "
                f"valid dataset data hierarchy."
            )
            console.error(message=message, error=FileNotFoundError)
            raise FileNotFoundError(message)  # Fallback for mypy

        # Loads the dataset's data from the .yaml file
        dataset_data_path = dataset_data_files.pop()
        instance: DatasetData = cls.from_yaml(file_path=dataset_data_path)

        # Initializes the session data cache if it was set to None during save().
        if instance._session_data_cache is None:
            instance._session_data_cache = {}

        # Resolves the dataset root directory (parent of the YAML file)
        local_root = dataset_data_path.parent
        instance.dataset_data_path = dataset_data_path

        # Resolves session data paths and loads data
        for session_meta in instance.sessions:
            session_dir = local_root.joinpath(session_meta.animal, session_meta.session)

            session_data = DatasetSessionData()
            session_data.resolve_paths(session_directory=session_dir)
            session_data.load_data()

            cache_key = f"{session_meta.animal}/{session_meta.session}"
            instance._session_data_cache[cache_key] = session_data

        return instance

    def save(self) -> None:
        """Caches the instance's data to the dataset's root directory as a 'dataset.yaml' file.

        Notes:
            This method releases all memory-mapped dataframes before saving and resets them to None.
        """
        # Releases all memory-mapped dataframes
        for session_data in self._session_data_cache.values():
            session_data.release_data()

        # Generates a copy to avoid modifying the instance
        origin = copy.deepcopy(self)

        # Resets path fields and cache to None before saving
        origin.dataset_data_path = None  # type: ignore[assignment]
        origin._session_data_cache = None  # type: ignore[assignment]  # noqa: SLF001

        # Converts StrEnum instances to strings for YAML serialization
        origin.session_type = str(origin.session_type)
        origin.acquisition_system = str(origin.acquisition_system)

        # Converts SessionMetadata tuples to list of dicts for YAML serialization
        origin.sessions = [  # type: ignore[assignment]
            {"session": s.session, "animal": s.animal} for s in origin.sessions
        ]

        # Saves instance data as a .YAML file
        origin.to_yaml(file_path=self.dataset_data_path)

    @property
    def animals(self) -> tuple[str, ...]:
        """Returns a tuple of unique animal identifiers included in the dataset."""
        return tuple(sorted({s.animal for s in self.sessions}))

    def get_sessions_for_animal(self, animal: str) -> tuple[SessionMetadata, ...]:
        """Returns the identification data for all sessions for the specified animal packaged into SessionMetadata
        instances.

        Args:
            animal: The unique identifier of the animal for which to retrieve the session identification data.

        Returns:
            A tuple of SessionMetadata instances for the specified animal.
        """
        return tuple(s for s in self.sessions if s.animal == animal)

    def get_session_data(self, animal: str, session: str) -> DatasetSessionData:
        """Returns the DatasetSessionData instance for the specified session.

        Args:
            animal: The unique identifier of the animal that participated in the session.
            session: The unique identifier of the session for which to return the data.

        Returns:
            The DatasetSessionData instance containing the paths to the session's data folder and memory-mapped data
            files.

        Raises:
            ValueError: If the specified session is not found in the dataset.
        """
        cache_key = f"{animal}/{session}"
        if cache_key not in self._session_data_cache:
            message = (
                f"Unable to retrieve the data for the session '{session}', performed by the animal '{animal}'. "
                f"The target animal and session combination is not found in the '{self.name}' dataset."
            )
            console.error(message=message, error=ValueError)
            raise ValueError(message)  # Fallback for mypy

        return self._session_data_cache[cache_key]
