"""Provides assets for maintaining the Sollertia platform project data hierarchy across all data acquisition and
processing machines.
"""

from __future__ import annotations

from enum import StrEnum
import shutil
from pathlib import Path
from dataclasses import dataclass

from ataraxis_time import TimestampFormats, get_timestamp
from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from ..configuration import AcquisitionSystems


class RawDataFiles(StrEnum):
    """Enumerates the canonical filenames at the root of a session's ``raw_data`` directory."""

    SESSION_DATA = "session_data.yaml"
    """The session marker YAML serialized from SessionData itself."""
    SESSION_DESCRIPTOR = "session_descriptor.yaml"
    """The session-embedded descriptor YAML written by the acquisition runtime. The concrete descriptor class
    is determined by the session's session_type, but the filename is flat across all session types."""
    SURGERY_METADATA = "surgery_metadata.yaml"
    """The per-animal surgery metadata YAML cached into the session's raw_data at acquisition time."""
    HARDWARE_STATE = "hardware_state.yaml"
    """The hardware state snapshot YAML written at the start of acquisition."""
    EXPERIMENT_CONFIGURATION = "experiment_configuration.yaml"
    """The experiment configuration YAML copied into the session for experiment sessions only."""
    SYSTEM_CONFIGURATION = "system_configuration.yaml"
    """The system configuration YAML copied into the session by the acquisition runtime."""
    CHECKSUM = "ax_checksum.txt"
    """The ataraxis data integrity checksum for the session's raw_data directory."""
    CHECKSUM_TRACKER = "checksum_processing_tracker.yaml"
    """The ProcessingTracker YAML for the checksum verification job."""


class Directories(StrEnum):
    """Enumerates the canonical subdirectory names found under a session's ``raw_data`` or ``processed_data``."""

    BEHAVIOR_DATA = "behavior_data"
    """Behavior data directory. Contains raw DataLogger NPZ archives under ``raw_data`` and processed
    behavior feather files under ``processed_data``."""
    CAMERA_DATA = "camera_data"
    """Camera data directory. Contains raw video files under ``raw_data`` and video processing pipeline
    outputs under ``processed_data``."""
    CAMERA_TIMESTAMPS = "camera_timestamps"
    """Camera timestamps directory under ``processed_data``; stores the ataraxis-video-system processed camera timestamp
    feather files."""
    CINDRA = "cindra"
    """Cindra output directory under ``processed_data``; root of cindra's single-recording and multi-recording
    outputs."""
    MESOSCOPE_DATA = "mesoscope_data"
    """Persistent mesoscope data directory under ``raw_data``; stores LERC-compressed TIFF stacks and
    acquisition metadata written by sollertia-experiment's preprocessing."""
    MICROCONTROLLER_DATA = "microcontroller_data"
    """Microcontroller data directory. Contains raw microcontroller logs under ``raw_data`` and processed
    microcontroller event feathers under ``processed_data``."""
    MULTI_RECORDING = "multi_recording"
    """Multi-recording subdirectory inside cindra's output directory; each child is a dataset-named directory
    holding cindra's multi-day analysis output."""


class ProcessingTrackers(StrEnum):
    """Enumerates canonical ProcessingTracker filenames placed inside each pipeline's output directory."""

    BEHAVIOR = "behavior_processing_tracker.yaml"
    """Tracker for the behavior processing pipeline; lives inside ``processed_data/behavior_data/``."""
    CAMERA = "camera_processing_tracker.yaml"
    """Tracker for the ataraxis-video-system camera timestamp processing pipeline; lives inside
    ``processed_data/camera_timestamps/``."""
    VIDEO = "video_processing_tracker.yaml"
    """Tracker for the forthcoming video processing pipeline; lives inside ``processed_data/camera_data/``."""
    MICROCONTROLLER = "microcontroller_processing_tracker.yaml"
    """Tracker for the ataraxis-communication-interface microcontroller log processing pipeline; lives inside
    ``processed_data/microcontroller_data/``."""
    CINDRA_SINGLE_RECORDING = "single_recording_tracker.yaml"
    """Tracker for cindra's single-recording pipeline; lives at the root of ``processed_data/cindra/``."""


class SessionTypes(StrEnum):
    """Defines the data acquisition session types supported by all data acquisition systems in the Sollertia
    platform.
    """

    LICK_TRAINING = "lick training"
    """Teaches animals to use the water delivery port while being head-fixed on the Mesoscope-VR system."""
    RUN_TRAINING = "run training"
    """Teaches animals to run on the treadmill while being head-fixed on the Mesoscope-VR system."""
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    """Runs virtual reality tasks using Unity game engine and collects brain activity data using the 2-Photon
    Random Access Mesoscope (2P-RAM)."""
    WINDOW_CHECKING = "window checking"
    """Evaluates the quality of the cranial window implantation procedure and the suitability of the animal for
    experiment sessions using the Mesoscope."""


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
    """The name of the data acquisition system used to acquire the session's data."""
    experiment_name: str | None = None
    """The name of the experiment performed during the session or Null (None), if the session is not an
    experiment session."""
    python_version: str = "3.14.4"
    """The Python version used to acquire session's data."""
    sollertia_experiment_version: str = "5.0.0"
    """The sollertia-experiment library version used to acquire the session's data."""
    raw_data_path: Path = Path()
    """The path to the root directory that stores the session's raw data."""
    processed_data_path: Path = Path()
    """The path to the root directory that stores the session's processed data."""

    def __post_init__(self) -> None:
        """Ensures that all fields used to define the session are properly initialized."""
        # Converts string values loaded from YAML to proper enum types.
        if isinstance(self.session_type, str):
            self.session_type = SessionTypes(self.session_type)
        if isinstance(self.acquisition_system, str):
            self.acquisition_system = AcquisitionSystems(self.acquisition_system)

    @property
    def session_data_path(self) -> Path:
        """Returns the path to the session's ``session_data.yaml`` marker file."""
        return self.raw_data_path.joinpath(RawDataFiles.SESSION_DATA)

    @property
    def session_descriptor_path(self) -> Path:
        """Returns the path to the session's ``session_descriptor.yaml`` file."""
        return self.raw_data_path.joinpath(RawDataFiles.SESSION_DESCRIPTOR)

    @property
    def surgery_metadata_path(self) -> Path:
        """Returns the path to the session's ``surgery_metadata.yaml`` file."""
        return self.raw_data_path.joinpath(RawDataFiles.SURGERY_METADATA)

    @property
    def hardware_state_path(self) -> Path:
        """Returns the path to the session's ``hardware_state.yaml`` file."""
        return self.raw_data_path.joinpath(RawDataFiles.HARDWARE_STATE)

    @property
    def experiment_configuration_path(self) -> Path:
        """Returns the path to the session's ``experiment_configuration.yaml`` file.

        Only populated for experiment sessions. Callers should check existence via ``.exists()``.
        """
        return self.raw_data_path.joinpath(RawDataFiles.EXPERIMENT_CONFIGURATION)

    @property
    def system_configuration_path(self) -> Path:
        """Returns the path to the session's ``system_configuration.yaml`` file."""
        return self.raw_data_path.joinpath(RawDataFiles.SYSTEM_CONFIGURATION)

    @property
    def checksum_path(self) -> Path:
        """Returns the path to the session's ``ax_checksum.txt`` data integrity checksum file."""
        return self.raw_data_path.joinpath(RawDataFiles.CHECKSUM)

    @property
    def checksum_tracker_path(self) -> Path:
        """Returns the path to the session's checksum ProcessingTracker YAML."""
        return self.raw_data_path.joinpath(RawDataFiles.CHECKSUM_TRACKER)

    @property
    def raw_camera_data_path(self) -> Path:
        """Returns the path to the session's ``raw_data/camera_data`` directory holding ataraxis-video-system raw
        videos.
        """
        return self.raw_data_path.joinpath(Directories.CAMERA_DATA)

    @property
    def raw_behavior_data_path(self) -> Path:
        """Returns the path to the session's ``raw_data/behavior_data`` directory holding DataLogger NPZ
        archives for the behavior instance.
        """
        return self.raw_data_path.joinpath(Directories.BEHAVIOR_DATA)

    @property
    def raw_microcontroller_data_path(self) -> Path:
        """Returns the path to the session's ``raw_data/microcontroller_data`` directory holding raw
        microcontroller logs.
        """
        return self.raw_data_path.joinpath(Directories.MICROCONTROLLER_DATA)

    @property
    def raw_mesoscope_data_path(self) -> Path:
        """Returns the path to the session's ``raw_data/mesoscope_data`` directory holding the persistent
        LERC-compressed TIFF stacks and acquisition metadata.
        """
        return self.raw_data_path.joinpath(Directories.MESOSCOPE_DATA)

    @property
    def behavior_data_path(self) -> Path:
        """Returns the path to the session's ``processed_data/behavior_data`` directory holding processed
        behavior feather files.
        """
        return self.processed_data_path.joinpath(Directories.BEHAVIOR_DATA)

    @property
    def cindra_data_path(self) -> Path:
        """Returns the path to the session's ``processed_data/cindra`` directory; the root of Cindra's
        single-recording and multi-recording outputs.
        """
        return self.processed_data_path.joinpath(Directories.CINDRA)

    @property
    def camera_timestamps_path(self) -> Path:
        """Returns the path to the session's ``processed_data/camera_timestamps`` directory holding
        ataraxis-video-system processed camera timestamp feather files.
        """
        return self.processed_data_path.joinpath(Directories.CAMERA_TIMESTAMPS)

    @property
    def camera_data_path(self) -> Path:
        """Returns the path to the session's ``processed_data/camera_data`` directory holding video
        processing pipeline outputs (forthcoming; not yet populated by the current pipeline).
        """
        return self.processed_data_path.joinpath(Directories.CAMERA_DATA)

    @property
    def microcontroller_data_path(self) -> Path:
        """Returns the path to the session's ``processed_data/microcontroller_data`` directory holding
        processed microcontroller event feathers.
        """
        return self.processed_data_path.joinpath(Directories.MICROCONTROLLER_DATA)

    @property
    def behavior_tracker_path(self) -> Path:
        """Returns the path to the behavior processing ProcessingTracker YAML inside ``behavior_data/``."""
        return self.behavior_data_path.joinpath(ProcessingTrackers.BEHAVIOR)

    @property
    def camera_tracker_path(self) -> Path:
        """Returns the path to the ataraxis-video-system camera processing ProcessingTracker YAML inside
        ``camera_timestamps/``.
        """
        return self.camera_timestamps_path.joinpath(ProcessingTrackers.CAMERA)

    @property
    def video_tracker_path(self) -> Path:
        """Returns the path to the video processing ProcessingTracker YAML inside ``camera_data/``
        (forthcoming pipeline; not yet populated).
        """
        return self.camera_data_path.joinpath(ProcessingTrackers.VIDEO)

    @property
    def microcontroller_tracker_path(self) -> Path:
        """Returns the path to the ataraxis-communication-interface microcontroller processing ProcessingTracker YAML
        inside ``microcontroller_data/``.
        """
        return self.microcontroller_data_path.joinpath(ProcessingTrackers.MICROCONTROLLER)

    @property
    def cindra_single_recording_tracker_path(self) -> Path:
        """Returns the path to cindra's single-recording ProcessingTracker YAML at the root of ``cindra/``."""
        return self.cindra_data_path.joinpath(ProcessingTrackers.CINDRA_SINGLE_RECORDING)

    @property
    def cindra_multi_recording_path(self) -> Path:
        """Returns the path to cindra's ``multi_recording`` subdirectory; each child is a dataset-named
        directory holding cindra's multi-day analysis output.
        """
        return self.cindra_data_path.joinpath(Directories.MULTI_RECORDING)

    @classmethod
    def create(
        cls,
        project_name: str,
        animal_id: str,
        session_type: str | SessionTypes,
        python_version: str,
        sollertia_experiment_version: str,
        acquisition_system: str | AcquisitionSystems,
        root_directory: Path,
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
            sollertia_experiment_version: The sollertia-experiment library version used to acquire the session's data.
            acquisition_system: The acquisition system that will run the session. Accepts an ``AcquisitionSystems``
                enumeration member or its string value.
            root_directory: The root directory of the acquisition system's project hierarchy on the local machine
                (PC). The session is created under ``root_directory / project_name / animal_id / <session_name>``.
            experiment_name: The name of the experiment performed during the session or None, if the session is
                not an experiment session.

        Returns:
            An initialized SessionData instance that stores the structure and the metadata of the created session.

        Raises:
            ValueError: If the specified session_type or acquisition_system is not a valid enumeration member.
            FileNotFoundError: If the project does not exist on the local machine (PC).
        """
        if session_type not in SessionTypes:
            message = (
                f"Unable to initialize a new data acquisition session. The session_type must be one of the "
                f"SessionTypes enumeration members, but got '{session_type}'."
            )
            console.error(message=message, error=ValueError)

        if acquisition_system not in AcquisitionSystems:
            message = (
                f"Unable to initialize a new data acquisition session. The acquisition_system must be one of the "
                f"AcquisitionSystems enumeration members, but got '{acquisition_system}'."
            )
            console.error(message=message, error=ValueError)
        acquisition_system = AcquisitionSystems(acquisition_system)

        # Acquires the UTC timestamp to use as the session name.
        session_name = str(get_timestamp(time_separator="-", output_format=TimestampFormats.STRING))

        # Constructs the root session directory path from the caller-provided root directory.
        session_path = root_directory.joinpath(project_name, animal_id, session_name)

        # Prevents creating new sessions for non-existent projects.
        if not root_directory.joinpath(project_name).exists():
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
        raw_data_path = session_path.joinpath("raw_data")
        ensure_directory_exists(path=raw_data_path)

        # Generates the SessionData instance. processed_data_path is left at the default Path() because the data
        # acquisition machine does not own the processed data hierarchy.
        instance = cls(
            project_name=project_name,
            animal_id=animal_id,
            session_name=session_name,
            session_type=session_type,
            acquisition_system=acquisition_system,
            experiment_name=experiment_name,
            python_version=python_version,
            sollertia_experiment_version=sollertia_experiment_version,
            raw_data_path=raw_data_path,
        )

        # Saves the configured instance data to the session's directory so that it can be reused during processing or
        # preprocessing.
        instance.save()

        if experiment_name is not None:
            # Copies the experiment_configuration.yaml file to the session's directory.
            experiment_configuration_path = root_directory.joinpath(
                project_name, "configuration", f"{experiment_name}.yaml"
            )
            shutil.copy2(
                src=experiment_configuration_path,
                dst=instance.experiment_configuration_path,
            )

        # All newly created sessions are marked with the 'nk.bin' file. If the marker is not removed during runtime,
        # the session becomes a valid target for deletion (purging) runtimes operating from the main acquisition
        # machine of any data acquisition system.
        instance.raw_data_path.joinpath("nk.bin").touch()

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
        session_data_files = list(session_path.rglob(RawDataFiles.SESSION_DATA))
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

        # Loads the session's data from the .yaml file.
        instance: SessionData = cls.from_yaml(file_path=session_data_path)

        # The method assumes that the 'donor' YAML file is always stored inside the raw_data directory of the session
        # to be processed. Uses this heuristic to get the path to the root session's directory and re-resolves the
        # raw and processed data root paths against the local filesystem layout so the session remains portable.
        local_root = session_data_path.parents[1]
        instance.raw_data_path = local_root.joinpath("raw_data")
        instance.processed_data_path = local_root.joinpath("processed_data")

        return instance

    def mark_runtime_initialized(self) -> None:
        """Removes the 'nk.bin' marker file from the session's raw_data directory to signal that runtime
        initialization has completed.

        Notes:
            This service method is used by the sollertia-experiment library to acquire the session's data. Do not call
            this method manually.
        """
        self.raw_data_path.joinpath("nk.bin").unlink(missing_ok=True)

    def save(self) -> None:
        """Caches the instance's data to the session's 'raw_data' directory as a 'session_data.yaml' file."""
        self.to_yaml(file_path=self.session_data_path)
