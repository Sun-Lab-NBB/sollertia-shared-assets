"""Provides assets for maintaining the Sun lab project data hierarchy across all data acquisition and processing
machines.
"""

import copy
from enum import StrEnum
import shutil
from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig
from ataraxis_time.time_helpers import TimestampFormats, get_timestamp

from ..configuration import AcquisitionSystems, get_system_configuration_data


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
    """Provides the paths to the directories and files that store the data acquired and losslessly preprocessed during
    the session's data acquisition runtime.
    """

    raw_data_path: Path = Path()
    """The path to the root directory that stores the session's raw data."""
    camera_data_path: Path = Path()
    """The path to the directory that contains the video camera data acquired during the session's runtime."""
    mesoscope_data_path: Path = Path()
    """The path to the directory that contains the Mesoscope data acquired during the session's runtime."""
    behavior_data_path: Path = Path()
    """The path to the directory that contains the non-video behavior data acquired during the session's runtime."""
    zaber_positions_path: Path = Path()
    """The path to the zaber_positions.yaml file that contains the snapshot of all Zaber motor positions 
    at the end of the session's runtime."""
    session_descriptor_path: Path = Path()
    """The path to the session_descriptor.yaml file that contains session-specific information, such as the specific 
    task parameters and the notes made by the experimenter during the session's runtime."""
    hardware_state_path: Path = Path()
    """The path to the hardware_state.yaml file that contains the partial snapshot of the configuration parameters used 
    by the data acquisition system's hardware modules during the session's runtime."""
    surgery_metadata_path: Path = Path()
    """The path to the surgery_metadata.yaml file that contains the information about the surgical intervention(s) 
    performed on the animal prior to the session's runtime."""
    session_data_path: Path = Path()
    """The path to the session_data.yaml file. This path is used by the SessionData instance to save itself to disk as 
    a .yaml file."""
    experiment_configuration_path: Path = Path()
    """The path to the experiment_configuration.yaml file that contains the snapshot of the experiment's configuration 
    used during the session's runtime. This file is only created for experiment sessions."""
    mesoscope_positions_path: Path = Path()
    """The path to the mesoscope_positions.yaml file that contains the snapshot of the imaging axes positions used
    by the Mesoscope at the end of the session's runtime."""
    window_screenshot_path: Path = Path()
    """The path to the .png screenshot of the ScanImagePC screen that communicates the visual snapshot of the 
    cranial window alignment and cell appearance at the beginning of the session's runtime."""
    system_configuration_path: Path = Path()
    """The path to the system_configuration.yaml file that contains the exact snapshot of the data acquisition system 
    configuration parameters used to acquire the session's data."""
    checksum_path: Path = Path()
    """The path to the ax_checksum.txt file that stores the xxHash-128 checksum of the data used to verify its 
    integrity during transmission."""
    nk_path: Path = Path()
    """The path to the nk.bin file used by the sl-experiment library to mark sessions undergoing runtime initialization.
    """

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        Args:
            root_directory_path: The path to the top-level raw data directory of the session's data hierarchy.
        """
        # Generates the managed paths
        self.raw_data_path = root_directory_path
        self.camera_data_path = self.raw_data_path.joinpath("camera_data")
        self.mesoscope_data_path = self.raw_data_path.joinpath("mesoscope_data")
        self.behavior_data_path = self.raw_data_path.joinpath("behavior_data")
        self.zaber_positions_path = self.raw_data_path.joinpath("zaber_positions.yaml")
        self.session_descriptor_path = self.raw_data_path.joinpath("session_descriptor.yaml")
        self.hardware_state_path = self.raw_data_path.joinpath("hardware_state.yaml")
        self.surgery_metadata_path = self.raw_data_path.joinpath("surgery_metadata.yaml")
        self.session_data_path = self.raw_data_path.joinpath("session_data.yaml")
        self.experiment_configuration_path = self.raw_data_path.joinpath("experiment_configuration.yaml")
        self.mesoscope_positions_path = self.raw_data_path.joinpath("mesoscope_positions.yaml")
        self.window_screenshot_path = self.raw_data_path.joinpath("window_screenshot.png")
        self.checksum_path = self.raw_data_path.joinpath("ax_checksum.txt")
        self.system_configuration_path = self.raw_data_path.joinpath("system_configuration.yaml")
        self.nk_path = self.raw_data_path.joinpath("nk.bin")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories."""
        ensure_directory_exists(self.raw_data_path)
        ensure_directory_exists(self.camera_data_path)
        ensure_directory_exists(self.mesoscope_data_path)
        ensure_directory_exists(self.behavior_data_path)


@dataclass
class ProcessedData:
    """Provides the paths to the directories and files that store the data generated by the processing pipelines from
    the raw data.
    """

    processed_data_path: Path = Path()
    """The path to the root directory that stores the session's processed data."""
    camera_data_path: Path = Path()
    """The path to the directory that contains video tracking data generated by the Sun lab DeepLabCut-based 
    video processing pipeline(s)."""
    mesoscope_data_path: Path = Path()
    """The path to the directory that contains processed brain activity (cell) data generated by sl-suite2p 
    processing pipelines (single-day and multi-day)."""
    behavior_data_path: Path = Path()
    """The path to the directory that contains the non-video behavior data extracted from the .npz log archives by the 
    sl-behavior log processing pipeline."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        Args:
            root_directory_path: The path to the top-level processed data directory of the session's data hierarchy.
        """
        # Generates the managed paths
        self.processed_data_path = root_directory_path
        self.camera_data_path = self.processed_data_path.joinpath("camera_data")
        self.mesoscope_data_path = self.processed_data_path.joinpath("mesoscope_data")
        self.behavior_data_path = self.processed_data_path.joinpath("behavior_data")

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories."""
        ensure_directory_exists(self.processed_data_path)
        ensure_directory_exists(self.camera_data_path)
        ensure_directory_exists(self.behavior_data_path)
        ensure_directory_exists(self.mesoscope_data_path)


@dataclass
class TrackingData:
    """Provides the path to the directory that stores the .yaml and .lock files used by ataraxis_data_structures.ProcessingTracker instances to track the runtime status of the data processing
    pipelines working with the session's data.
    """

    tracking_data_path: Path = Path()
    """The path to the root directory that stores the session's tracking data."""

    def resolve_paths(self, root_directory_path: Path) -> None:
        """Resolves all paths managed by the class instance based on the input root directory path.

        Args:
            root_directory_path: The path to the top-level tracking data directory of the session's data hierarchy.
        """
        # Generates the managed paths
        self.tracking_data_path = root_directory_path

    def make_directories(self) -> None:
        """Ensures that all major subdirectories and the root directory exist, creating any missing directories."""
        ensure_directory_exists(self.tracking_data_path)


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
    tracking_data: TrackingData = field(default_factory=lambda: TrackingData())
    """Defines the session's tracking data hierarchy."""

    def __post_init__(self) -> None:
        """Ensures that all instances used to define the session's data hierarchy are properly initialized."""
        if not isinstance(self.raw_data, RawData):
            self.raw_data = RawData()  # pragma: no cover

        if not isinstance(self.processed_data, ProcessedData):
            self.processed_data = ProcessedData()  # pragma: no cover

        if not isinstance(self.tracking_data, TrackingData):
            self.tracking_data = TrackingData()  # pragma: no cover

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
            To access the data of an already existing session, use the load() method.

        Args:
            project_name: The name of the project for which the session is acquired.
            animal_id: The unique identifier of the animal participating in the session.
            session_type: The type of the session.
            python_version: The Python version used to acquire the session's data.
            sl_experiment_version: The sl-experiment library version used to acquire the session's data.
            experiment_name: The name of the experiment performed during the session or None, if the session is
                not an experiment session.

        Returns:
            An initialized SessionData instance that stores the structure and the metadata of the created session.
        """
        if session_type not in SessionTypes:
            message = (
                f"Invalid session type '{session_type}' encountered when initializing a new data acquisition session. "
                f"Use one of the supported session types from the SessionTypes enumeration."
            )
            console.error(message=message, error=ValueError)

        # Acquires the UTC timestamp to use as the session name
        session_name = str(get_timestamp(time_separator="-", output_format=TimestampFormats.STRING))

        # Resolves the acquisition system configuration. This queries the acquisition system configuration data used
        # by the machine (PC) that calls this method.
        acquisition_system = get_system_configuration_data()

        # Constructs the root session directory path
        session_path = acquisition_system.filesystem.root_directory.joinpath(project_name, animal_id, session_name)

        # Prevents creating new sessions for non-existent projects.
        if not acquisition_system.filesystem.root_directory.joinpath(project_name).exists():
            message = (
                f"Unable to initialize a new data acquisition session {session_name} for the animal '{animal_id}' and "
                f"project '{project_name}'. The project does not exist on the local machine (PC). Use the "
                f"'sl-project create' CLI command to create the project on the local machine before creating new "
                f"sessions."
            )
            console.error(message=message, error=FileNotFoundError)

        # Generates the session's raw data directory. This method assumes that the session is created on the
        # data acquisition machine that only acquires the data and does not create the other session's directories used
        # during data processing.
        raw_data = RawData()
        raw_data.resolve_paths(root_directory_path=session_path.joinpath("raw_data"))
        raw_data.make_directories()  # Generates the local 'raw_data' directory tree

        # Generates the SessionData instance.
        instance = SessionData(
            project_name=project_name,
            animal_id=animal_id,
            session_name=session_name,
            session_type=session_type,
            acquisition_system=acquisition_system.name,
            raw_data=raw_data,
            experiment_name=experiment_name,
            python_version=python_version,
            sl_experiment_version=sl_experiment_version,
        )

        # Saves the configured instance data to the session's directory so that it can be reused during processing or
        # preprocessing.
        instance.save()

        # Dumps the acquisition system's configuration data to the session's directory
        acquisition_system.save(path=instance.raw_data.system_configuration_path)

        if experiment_name is not None:
            # Copies the experiment_configuration.yaml file to the session's directory
            experiment_configuration_path = acquisition_system.filesystem.root_directory.joinpath(
                project_name, "configuration", f"{experiment_name}.yaml"
            )
            shutil.copy2(experiment_configuration_path, instance.raw_data.experiment_configuration_path)

        # All newly created sessions are marked with the 'nk.bin' file. If the marker is not removed during runtime,
        # the session becomes a valid target for deletion (purging) runtimes operating from the main acquisition
        # machine of any data acquisition system.
        instance.raw_data.nk_path.touch()

        # Returns the initialized SessionData instance to caller
        return instance

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
        instance.processed_data.make_directories()  # Ensures that processed data hierarchy exists.

        # TRACKING DATA
        instance.tracking_data.resolve_paths(root_directory_path=local_root.joinpath(local_root, "tracking_data"))
        instance.tracking_data.make_directories()  # Ensures tracking data directories exist

        # Returns the initialized SessionData instance to caller
        return instance

    def runtime_initialized(self) -> None:
        """Ensures that the 'nk.bin' marker file is removed from the session's raw_data directory.

        Notes:
            This service method is used by the sl-experiment library to acquire the session's data. Do not call this
            method manually.
        """
        self.raw_data.nk_path.unlink(missing_ok=True)

    def save(self) -> None:
        """Caches the instance's data to the session's 'raw_data' directory as a 'session_data.yaml' file."""
        # Generates a copy of the original class to avoid modifying the instance that will be used for further
        # processing.
        origin = copy.deepcopy(self)

        # Resets all path fields to Null (None) before saving the instance to disk.
        origin.raw_data = None  # type: ignore[assignment]
        origin.processed_data = None  # type: ignore[assignment]
        origin.tracking_data = None  # type: ignore[assignment]

        # Converts StringEnum instances to strings.
        origin.session_type = str(origin.session_type)
        origin.acquisition_system = str(origin.acquisition_system)

        # Saves instance data as a .YAML file.
        origin.to_yaml(file_path=self.raw_data.session_data_path)
