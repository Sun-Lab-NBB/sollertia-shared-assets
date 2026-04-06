"""Provides assets for maintaining the Sun lab project data hierarchy across all data acquisition and processing
machines.
"""

import copy
from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from ..configuration import AcquisitionSystems


class SessionTypes(StrEnum):
    """Defines the data acquisition session types supported by all data acquisition systems used in the Sun lab."""

    LICK_TRAINING = "lick training"
    """Teaches animals to use the water delivery port while being head-fixed on the Mesoscope-VR system."""
    RUN_TRAINING = "run training"
    """Teaches animals to run on the treadmill while being head-fixed on the Mesoscope-VR system."""
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    """Runs virtual reality tasks using Unity game engine and collects brain activity data using the 2-Photon Random
    Access Mesoscope (2P-RAM)."""
    WINDOW_CHECKING = "window checking"
    """Evaluates the quality of the cranial window implantation procedure and the suitability of the animal for
    experiment sessions using the Mesoscope."""


@dataclass
class RawData:
    """Provides the paths to the root directory and shared metadata files that store the data acquired during the
    session's data acquisition runtime.

    Notes:
        Only paths to files consumed by multiple sl libraries are exposed as fields. Internal files (session_data.yaml,
        nk.bin, system_configuration.yaml) and data subdirectories (camera_data, mesoscope_data, behavior_data) are
        resolved at runtime by the libraries that own them.
    """

    raw_data_path: Path = Path()
    """The path to the root directory that stores the session's raw data."""
    session_descriptor_path: Path = Path()
    """The path to the session_descriptor.yaml file that contains session-specific information, such as the specific
    task parameters and the notes made by the experimenter during the session's runtime."""
    hardware_state_path: Path = Path()
    """The path to the hardware_state.yaml file that contains the partial snapshot of the configuration parameters used
    by the data acquisition system's hardware modules during the session's runtime."""
    surgery_metadata_path: Path = Path()
    """The path to the surgery_metadata.yaml file that contains the information about the surgical intervention(s)
    performed on the animal prior to the session's runtime."""
    experiment_configuration_path: Path = Path()
    """The path to the experiment_configuration.yaml file that contains the snapshot of the experiment's configuration
    used during the session's runtime. This file is only created for experiment sessions."""
    window_screenshot_path: Path = Path()
    """The path to the .png screenshot of the ScanImagePC screen that communicates the visual snapshot of the
    cranial window alignment and cell appearance at the beginning of the session's runtime."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        Args:
            root_directory_path: The path to the top-level raw data directory of the session's data hierarchy.
        """
        self.raw_data_path = root_directory_path
        self.session_descriptor_path = self.raw_data_path.joinpath("session_descriptor.yaml")
        self.hardware_state_path = self.raw_data_path.joinpath("hardware_state.yaml")
        self.surgery_metadata_path = self.raw_data_path.joinpath("surgery_metadata.yaml")
        self.experiment_configuration_path = self.raw_data_path.joinpath("experiment_configuration.yaml")
        self.window_screenshot_path = self.raw_data_path.joinpath("window_screenshot.png")

    def make_directories(self) -> None:
        """Ensures that the root raw data directory exists, creating it if missing."""
        ensure_directory_exists(self.raw_data_path)


@dataclass
class ProcessedData:
    """Provides the path to the root directory that stores the session's processed data.

    Notes:
        Each data processing library (axvs, axci, cindra) creates its own output subdirectory under this root at
        runtime. The specific subdirectory layout is owned by the processing libraries.
    """

    processed_data_path: Path = Path()
    """The path to the root directory that stores the session's processed data."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves the processed data root path.

        Args:
            root_directory_path: The path to the top-level processed data directory of the session's data hierarchy.
        """
        self.processed_data_path = root_directory_path


@dataclass
class SessionData(YamlConfig):
    """Defines the structure and the metadata of a data acquisition session.

    This class encapsulates the information necessary to access the session's data stored on disk and functions as the
    entry point for all interactions with the session's data.

    Notes:
        Do not initialize this class directly. Instead, use the create() method when starting new data acquisition
        sessions or the load() method when accessing data for an existing session.

        When this class is used to create a new session, it generates the new session's name using the current UTC
        timestamp, accurate to microseconds. This ensures that each session 'name' is unique and preserves the overall
        session order.
    """

    project_name: str
    """The name of the project for which the session was acquired."""
    animal_id: str
    """The unique identifier of the animal that participates in the session."""
    session_name: str
    """The unique identifier (name) of the session."""
    session_type: str | SessionTypes
    """The type of the session."""
    acquisition_system: str | AcquisitionSystems = AcquisitionSystems.MESOSCOPE_VR
    """The name of the data acquisition system used to acquire the session's data"""
    experiment_name: str | None = None
    """The name of the experiment performed during the session or Null (None), if the session is not an experiment 
    session."""
    python_version: str = "3.11.13"
    """The Python version used to acquire session's data."""
    sl_experiment_version: str = "3.0.0"
    """The sl-experiment library version used to acquire the session's data."""
    raw_data: RawData = field(default_factory=lambda: RawData())
    """Defines the session's raw data hierarchy."""
    processed_data: ProcessedData = field(default_factory=lambda: ProcessedData())
    """Defines the session's processed data hierarchy."""

    def __post_init__(self) -> None:
        """Ensures that all instances used to define the session's data hierarchy are properly initialized."""
        if not isinstance(self.raw_data, RawData):
            self.raw_data = RawData()  # pragma: no cover

        if not isinstance(self.processed_data, ProcessedData):
            self.processed_data = ProcessedData()  # pragma: no cover

    @classmethod
    def create(
        cls,
        project_name: str,
        animal_id: str,
        session_type: SessionTypes | str,
        python_version: str,
        sl_experiment_version: str,
        experiment_name: str | None = None,
    ) -> SessionData:
        """Initializes a new data acquisition session and creates its data structure on the host-machine's filesystem.

        Notes:
            This method has been moved to sl-experiment. It depends on get_system_configuration_data() which is now
            owned by sl-experiment. Use the sl-experiment session creation interface instead.

        Raises:
            NotImplementedError: Always. This method must be reimplemented in sl-experiment.
        """
        message = (
            "SessionData.create() has been moved to sl-experiment. This method depends on "
            "get_system_configuration_data() which is now owned by sl-experiment."
        )
        raise NotImplementedError(message)

    @classmethod
    def load(cls, session_path: Path) -> SessionData:
        """Loads the target session's data from the specified session_data.yaml file.

        Notes:
            To create a new session, use the create() method.

        Args:
            session_path: The path to the directory where to search for the session_data.yaml file. Typically, this
                is the path to the root session's directory, e.g.: root/project/animal/session.

        Returns:
            An initialized SessionData instance that stores the loaded session's data.

        Raises:
            FileNotFoundError: If multiple or no 'session_data.yaml' file instances are found under the input directory.
        """
        # To properly initialize the SessionData instance, the provided path should contain a single session_data.yaml
        # file at any hierarchy level.
        session_data_files = list(session_path.rglob("session_data.yaml"))
        if len(session_data_files) != 1:
            message = (
                f"Unable to load the target session's data. Expected a single session_data.yaml file to be located "
                f"under the directory tree specified by the input path: {session_path}. Instead, encountered "
                f"{len(session_data_files)} candidate files. This indicates that the input path does not point to a "
                f"valid session data hierarchy."
            )
            console.error(message=message, error=FileNotFoundError)

        # If a single candidate is found (as expected), extracts it from the list and uses it to resolve the
        # session data hierarchy.
        session_data_path = session_data_files.pop()

        # Loads the session's data from the.yaml file
        instance: SessionData = cls.from_yaml(file_path=session_data_path)

        # The method assumes that the 'donor' YAML file is always stored inside the raw_data directory of the session
        # to be processed. Uses this heuristic to get the path to the root session's directory.
        local_root = session_data_path.parents[1]

        # RAW DATA
        instance.raw_data.resolve_paths(root_directory_path=local_root.joinpath(local_root, "raw_data"))

        # PROCESSED DATA
        instance.processed_data.resolve_paths(root_directory_path=local_root.joinpath(local_root, "processed_data"))

        # Returns the initialized SessionData instance to caller
        return instance

    def runtime_initialized(self) -> None:
        """Ensures that the 'nk.bin' marker file is removed from the session's raw_data directory.

        Notes:
            This service method is used by the sl-experiment library to acquire the session's data. Do not call this
            method manually.
        """
        self.raw_data.raw_data_path.joinpath("nk.bin").unlink(missing_ok=True)

    def save(self) -> None:
        """Caches the instance's data to the session's 'raw_data' directory as a 'session_data.yaml' file."""
        # Generates a copy of the original class to avoid modifying the instance that will be used for further
        # processing.
        origin = copy.deepcopy(self)

        # Resets all path fields to Null (None) before saving the instance to disk.
        origin.raw_data = None  # type: ignore[assignment]
        origin.processed_data = None  # type: ignore[assignment]

        # Converts StringEnum instances to strings.
        origin.session_type = str(origin.session_type)
        origin.acquisition_system = str(origin.acquisition_system)

        # Saves instance data as a .YAML file.
        origin.to_yaml(file_path=self.raw_data.raw_data_path.joinpath("session_data.yaml"))
