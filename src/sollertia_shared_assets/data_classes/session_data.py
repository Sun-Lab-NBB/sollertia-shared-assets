"""Provides assets for maintaining the Sollertia platform project data hierarchy across all data acquisition and
processing machines.
"""

from __future__ import annotations

from enum import StrEnum
import shutil
from typing import TYPE_CHECKING, Any, Protocol
from pathlib import Path
from dataclasses import dataclass

from ataraxis_time import TimestampFormats, get_timestamp
from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from ..configuration import (
    EXPERIMENT_CONFIGURATION_REGISTRY,
    AcquisitionSystems,
    get_task_templates_directory,
)

if TYPE_CHECKING:
    from .project_hierarchy import AnimalData

RAW_DATA_DIRECTORY: str = "raw_data"
"""Canonical name of the per-session raw data directory under each session root."""

PROCESSED_DATA_DIRECTORY: str = "processed_data"
"""Canonical name of the per-session processed data directory under each session root."""


class RawDataFiles(StrEnum):
    """Enumerates the canonical filenames at the root of a session's ``raw_data`` directory that are written by every
    acquisition system on the platform.
    """

    SESSION_DATA = "session_data.yaml"
    """The session marker YAML serialized from SessionData itself."""
    SESSION_DESCRIPTOR = "session_descriptor.yaml"
    """The session-embedded descriptor YAML written by the acquisition runtime. The concrete descriptor class is
    determined by the session's session_type, but the filename is flat across all session types."""
    SURGERY_METADATA = "surgery_metadata.yaml"
    """The per-animal surgery metadata YAML cached into the session's raw_data at acquisition time."""
    HARDWARE_STATE = "hardware_state.yaml"
    """The hardware state snapshot YAML written at the start of acquisition."""
    EXPERIMENT_CONFIGURATION = "experiment_configuration.yaml"
    """The experiment configuration YAML copied into the session for experiment sessions only."""
    VR_CONFIGURATION = "vr_configuration.yaml"
    """The Virtual Reality (VR) task template YAML cached into the session at acquisition time. Records the Unity task
    template (cues, VR environment, trial structures) that was active when the session was acquired."""
    SYSTEM_CONFIGURATION = "system_configuration.yaml"
    """The system configuration YAML copied into the session by the acquisition runtime."""
    CHECKSUM = "ax_checksum.txt"
    """The ataraxis data integrity checksum for the session's raw_data directory."""
    NK_MARKER = "nk.bin"
    """The 'uninitialized session' marker present in raw_data while the acquisition runtime has not yet finished
    creating snapshots and initializing instruments. Removed by mark_runtime_initialized() once initialization
    completes."""


class Directories(StrEnum):
    """Enumerates the canonical names of subdirectories found under a session's ``raw_data`` or ``processed_data``
    that are shared across all acquisition systems on the platform.
    """

    BEHAVIOR_DATA = "behavior_data"
    """Behavior data directory. Contains raw DataLogger NPZ archives under ``raw_data`` and processed behavior feather
    files under ``processed_data``."""
    CAMERA_DATA = "camera_data"
    """Camera data directory. Stores the raw camera recordings under ``raw_data`` and the outputs of the
    sollertia-forgery video-processing pipeline (DeepLabCut pose estimation followed by re-packaging) under
    ``processed_data``."""
    CAMERA_TIMESTAMPS = "camera_timestamps"
    """Camera timestamps directory under ``processed_data``. Stores the per-frame timing data extracted by the
    ataraxis-video-system log-processing pipeline."""
    MICROCONTROLLER_DATA = "microcontroller_data"
    """Microcontroller data directory under ``processed_data``. Stores the extracted microcontroller data produced by
    the ataraxis-communication-interface log-processing pipeline. Microcontroller raw data is bundled into the
    DataLogger archives under ``raw_data/behavior_data`` rather than living in a dedicated raw-side directory."""
    CINDRA = "cindra"
    """Cindra output directory under ``processed_data``. The root of cindra's single-recording and multi-recording
    outputs. Cindra is reusable by any photometry-data-generating acquisition system."""
    MULTI_RECORDING = "multi_recording"
    """Multi-recording subdirectory inside cindra's output directory. Each child is a dataset-named directory holding
    cindra's multi-day analysis output."""


class ProcessingTrackers(StrEnum):
    """Enumerates canonical ProcessingTracker filenames written by each data-integrity and processing pipeline shared
    across all acquisition systems on the platform.
    """

    CHECKSUM = "checksum_processing_tracker.yaml"
    """Tracker for the checksum verification pipeline."""
    BEHAVIOR = "behavior_processing_tracker.yaml"
    """Tracker for the behavior processing pipeline."""
    CAMERA = "camera_processing_tracker.yaml"
    """Tracker for the ataraxis-video-system camera timestamp processing pipeline."""
    VIDEO = "video_processing_tracker.yaml"
    """Tracker for the sollertia-forgery video processing pipeline (re-packaging of DeepLabCut outputs)."""
    MICROCONTROLLER = "microcontroller_processing_tracker.yaml"
    """Tracker for the ataraxis-communication-interface microcontroller log processing pipeline."""
    CINDRA_SINGLE_RECORDING = "single_recording_tracker.yaml"
    """Tracker for cindra's single-recording pipeline."""
    CINDRA_MULTI_RECORDING = "multi_recording_tracker.yaml"
    """Tracker for cindra's multi-recording pipeline."""
    FORGING = "forging_tracker.yaml"
    """Tracker for the sollertia-forgery dataset-forging pipeline."""
    ANALYSIS = "analysis_tracker.yaml"
    """Tracker for the sollertia-forgery analysis pipeline."""
    MANIFEST = "manifest_processing_tracker.yaml"
    """Tracker for the project manifest generation pipeline."""
    TRANSFER = "transfer_processing_tracker.yaml"
    """Tracker for batch session transfer and deletion jobs. Location is specified by the caller, since transfer jobs
    are not bound to a single session or dataset."""


class SessionTypes(StrEnum):
    """Defines the data acquisition session types supported by all data acquisition systems in the Sollertia
    platform.
    """

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


class MesoscopeRawDataFiles(StrEnum):
    """Enumerates the canonical filenames at the root of a session's ``raw_data`` directory that are written
    exclusively by the Mesoscope-VR acquisition system.
    """

    ZABER_POSITIONS = "zaber_positions.yaml"
    """The Zaber motor position snapshot written at session start by the Mesoscope-VR acquisition runtime."""
    MESOSCOPE_POSITIONS = "mesoscope_positions.yaml"
    """The Mesoscope objective position snapshot written at session start by the Mesoscope-VR acquisition runtime."""
    WINDOW_SCREENSHOT = "window_screenshot.png"
    """The cranial imaging window screenshot captured at session start by the Mesoscope-VR acquisition runtime."""


class MesoscopeDirectories(StrEnum):
    """Enumerates the canonical names of subdirectories under a session's ``raw_data`` directory that are written
    exclusively by the Mesoscope-VR acquisition system.
    """

    MESOSCOPE_DATA = "mesoscope_data"
    """Persistent mesoscope data directory under ``raw_data``. Stores LERC-compressed TIFF stacks and acquisition
    metadata written by sollertia-experiment's preprocessing."""


@dataclass(slots=True)
class RawData:
    """Stores the absolute paths to all generic raw assets of a single data acquisition session.

    Notes:
        Instances are constructed by ``SessionData._build_sub_dataclasses`` after the session's raw data root has been
        finalized. The ``build`` classmethod is the single source of truth for the enum-to-field mapping.
    """

    session_data_path: Path
    """Stores the metadata that identifies the session and resolves the on-disk locations of all of its assets."""
    session_descriptor_path: Path
    """Stores the task parameters and outcome metadata captured during acquisition. The concrete descriptor class is
    determined by the session's session_type and is dispatched via DESCRIPTOR_REGISTRY."""
    surgery_metadata_path: Path
    """Stores a frozen snapshot of the animal's surgical history (procedures, drugs, implants, injections) as it stood
    at the moment the session was acquired."""
    hardware_state_path: Path
    """Records the configuration of every active hardware module on the acquisition system, used to interpret the raw
    data during downstream processing. The concrete parsing class is determined by the session's acquisition_system
    and is dispatched via HARDWARE_STATE_REGISTRY."""
    system_configuration_path: Path
    """Preserves the acquisition-system-level configuration in effect when the session was acquired. The concrete
    parsing class is determined by the session's acquisition_system and is owned by sollertia-experiment."""
    experiment_configuration_path: Path
    """Stores the experiment configuration in effect when the session was acquired. Only populated for experiment
    sessions; callers should check .exists() before reading. The concrete parsing class is determined by the session's
    acquisition_system and is dispatched via EXPERIMENT_CONFIGURATION_REGISTRY."""
    vr_configuration_path: Path
    """Stores the Virtual Reality (VR) task template (cues, VR environment, trial structures) that was active when the
    session was acquired. Populated by ``SessionData.create()`` for experiment sessions by copying the template YAML
    that matches the experiment configuration's ``unity_scene_name`` out of the task templates directory; for non-
    experiment sessions, the acquisition runtime writes this file when a VR task is used. Callers should check
    ``.exists()`` before reading. Parsed via ``TaskTemplate``."""
    checksum_path: Path
    """Stores the ataraxis data-integrity checksum used by the checksum verification pipeline to detect corruption or
    accidental modification of raw assets after acquisition."""
    checksum_tracker_path: Path
    """Tracks the outcome of integrity checks performed by the checksum verification pipeline."""
    nk_path: Path
    """Marks the session as uninitialized while the acquisition runtime is still creating snapshots and initializing
    instruments. Removed by mark_runtime_initialized() once the session is ready to begin acquisition."""
    behavior_data_path: Path
    """Holds the raw behavior data captured during acquisition, including the raw messages emitted by every
    microcontroller managed by ataraxis-communication-interface."""
    camera_data_path: Path
    """Holds the raw camera recordings captured during acquisition."""

    @classmethod
    def build(cls, root: Path) -> RawData:
        """Builds a RawData instance with every field resolved against the input raw data root.

        Args:
            root: The path to the session's ``raw_data`` directory.

        Returns:
            A RawData instance whose fields are absolute paths under the input root.
        """
        return cls(
            session_data_path=root.joinpath(RawDataFiles.SESSION_DATA),
            session_descriptor_path=root.joinpath(RawDataFiles.SESSION_DESCRIPTOR),
            surgery_metadata_path=root.joinpath(RawDataFiles.SURGERY_METADATA),
            hardware_state_path=root.joinpath(RawDataFiles.HARDWARE_STATE),
            system_configuration_path=root.joinpath(RawDataFiles.SYSTEM_CONFIGURATION),
            experiment_configuration_path=root.joinpath(RawDataFiles.EXPERIMENT_CONFIGURATION),
            vr_configuration_path=root.joinpath(RawDataFiles.VR_CONFIGURATION),
            checksum_path=root.joinpath(RawDataFiles.CHECKSUM),
            checksum_tracker_path=root.joinpath(ProcessingTrackers.CHECKSUM),
            nk_path=root.joinpath(RawDataFiles.NK_MARKER),
            behavior_data_path=root.joinpath(Directories.BEHAVIOR_DATA),
            camera_data_path=root.joinpath(Directories.CAMERA_DATA),
        )


@dataclass(slots=True)
class ProcessedData:
    """Stores the absolute paths to all generic processed assets of a single data acquisition session.

    Notes:
        Cindra fields live here because cindra is reusable by any photometry-data-generating acquisition system, not
        Mesoscope-VR-specific. Future processing tools that apply across acquisition systems get added directly as new
        fields here.
    """

    behavior_data_path: Path
    """Holds the extracted behavior data produced by the sollertia-forgery behavior-processing pipeline."""
    behavior_tracker_path: Path
    """Tracks the outcome of behavior-data extraction performed by the sollertia-forgery behavior-processing
    pipeline."""
    camera_timestamps_path: Path
    """Holds the per-frame camera timing data extracted by the ataraxis-video-system log-processing pipeline, used to
    align the camera recordings with the rest of the session's data."""
    camera_tracker_path: Path
    """Tracks the outcome of camera-timestamp extraction performed by the ataraxis-video-system log-processing
    pipeline."""
    video_data_path: Path
    """Holds the DeepLabCut pose-estimation output re-packaged by the sollertia-forgery video-processing pipeline."""
    video_tracker_path: Path
    """Tracks the outcome of DeepLabCut processing and re-packaging performed by the sollertia-forgery video-processing
    pipeline."""
    microcontroller_data_path: Path
    """Holds the extracted microcontroller data produced by the ataraxis-communication-interface log-processing
    pipeline."""
    microcontroller_tracker_path: Path
    """Tracks the outcome of microcontroller-event extraction performed by the ataraxis-communication-interface
    log-processing pipeline."""
    cindra_data_path: Path
    """Acts as the root for both single-recording and multi-recording cindra outputs. Cindra is reusable by any
    photometry-data-generating acquisition system on the Sollertia platform, which is why these fields live on the
    generic ProcessedData rather than on an acquisition-system-specific dataclass."""
    cindra_single_recording_tracker_path: Path
    """Tracks the outcome of single-recording neural imaging analysis performed by cindra's single-recording
    pipeline."""
    cindra_multi_recording_path: Path
    """Acts as the root for cindra's multi-recording analysis outputs. Each child holds the multi-day analysis output
    produced by cindra's multi-recording pipeline for a particular dataset that this session participates in."""

    @classmethod
    def build(cls, root: Path) -> ProcessedData:
        """Builds a ProcessedData instance with every field resolved against the input processed data root.

        Args:
            root: The path to the session's ``processed_data`` directory.

        Returns:
            A ProcessedData instance whose fields are absolute paths under the input root.
        """
        behavior_data_path = root.joinpath(Directories.BEHAVIOR_DATA)
        camera_timestamps_path = root.joinpath(Directories.CAMERA_TIMESTAMPS)
        video_data_path = root.joinpath(Directories.CAMERA_DATA)
        microcontroller_data_path = root.joinpath(Directories.MICROCONTROLLER_DATA)
        cindra_data_path = root.joinpath(Directories.CINDRA)
        return cls(
            behavior_data_path=behavior_data_path,
            behavior_tracker_path=behavior_data_path.joinpath(ProcessingTrackers.BEHAVIOR),
            camera_timestamps_path=camera_timestamps_path,
            camera_tracker_path=camera_timestamps_path.joinpath(ProcessingTrackers.CAMERA),
            video_data_path=video_data_path,
            video_tracker_path=video_data_path.joinpath(ProcessingTrackers.VIDEO),
            microcontroller_data_path=microcontroller_data_path,
            microcontroller_tracker_path=microcontroller_data_path.joinpath(ProcessingTrackers.MICROCONTROLLER),
            cindra_data_path=cindra_data_path,
            cindra_single_recording_tracker_path=cindra_data_path.joinpath(ProcessingTrackers.CINDRA_SINGLE_RECORDING),
            cindra_multi_recording_path=cindra_data_path.joinpath(Directories.MULTI_RECORDING),
        )


@dataclass(slots=True)
class MesoscopeRawData:
    """Stores the absolute paths to the Mesoscope-VR-specific raw assets of a single data acquisition session.

    Notes:
        Instances are constructed by ``SessionData._build_sub_dataclasses`` when the session's acquisition_system is
        AcquisitionSystems.MESOSCOPE_VR. The ``build`` classmethod is the single source of truth for the
        enum-to-field mapping.
    """

    zaber_positions_path: Path
    """Captures the states of the Zaber motorized stages used by the Mesoscope-VR system at the start of the
    session."""
    mesoscope_positions_path: Path
    """Records the 2-Photon Random Access Mesoscope (2P-RAM) objective position used to image the cranial window
    during the session, allowing the same imaging field of view to be recovered in follow-up sessions."""
    window_screenshot_path: Path
    """Provides a visual reference of the cranial imaging window taken at the start of the session, used for
    downstream registration and quality assessment."""
    mesoscope_data_path: Path
    """Holds the compressed 2-Photon Random Access Mesoscope (2P-RAM) acquisition output and accompanying metadata
    produced by sollertia-experiment's preprocessing, which serves as the input to cindra's neural imaging analysis
    pipelines."""

    @classmethod
    def build(cls, root: Path) -> MesoscopeRawData:
        """Builds a MesoscopeRawData instance with every field resolved against the input raw data root.

        Args:
            root: The path to the session's ``raw_data`` directory.

        Returns:
            A MesoscopeRawData instance whose fields are absolute paths under the input root.
        """
        return cls(
            zaber_positions_path=root.joinpath(MesoscopeRawDataFiles.ZABER_POSITIONS),
            mesoscope_positions_path=root.joinpath(MesoscopeRawDataFiles.MESOSCOPE_POSITIONS),
            window_screenshot_path=root.joinpath(MesoscopeRawDataFiles.WINDOW_SCREENSHOT),
            mesoscope_data_path=root.joinpath(MesoscopeDirectories.MESOSCOPE_DATA),
        )


class _SystemRawDataBuilder(Protocol):
    """Structural type for system-specific raw data dataclasses registered in ``SYSTEM_RAW_DATA_REGISTRY``."""

    @classmethod
    def build(cls, root: Path) -> Any:  # noqa: ANN401
        """Resolves all system-specific raw-asset paths under the session's ``raw_data`` directory.

        Conforming implementations construct and return a dataclass instance whose fields hold absolute paths
        anchored on ``root``. The concrete return type is the implementing class itself (e.g., ``MesoscopeRawData``).

        Args:
            root: The session's ``raw_data`` directory absolute path.

        Returns:
            An instance of the conforming dataclass with every system-specific raw-asset path resolved.
        """
        ...  # pragma: no cover


# noinspection PyTypeChecker
SYSTEM_RAW_DATA_REGISTRY: dict[AcquisitionSystems, type[_SystemRawDataBuilder]] = {
    AcquisitionSystems.MESOSCOPE_VR: MesoscopeRawData,
}
"""Maps each acquisition system to the dataclass that captures its system-specific raw assets. The registered
class must expose a ``build(root: Path) -> Self`` classmethod that resolves all system-specific paths under the
session's ``raw_data`` directory. ``SessionData._build_sub_dataclasses`` consults this registry to dispatch the
``system_raw_data`` sub-dataclass without per-system branching, so future acquisition systems register their
``<System>RawData`` builder here."""


@dataclass
class SessionData(YamlConfig):
    """Defines the structure and the metadata of a data acquisition session.

    This class encapsulates the information necessary to access the session's data stored on disk and functions as the
    entry point for all interactions with the session's data.

    Notes:
        Do not initialize this class directly. Instead, use the create() method when starting new data acquisition
        sessions or the load() method when accessing data for an existing session. Both methods build the runtime-only
        ``raw_data``, ``processed_data``, and ``system_raw_data`` sub-dataclass attributes after the persisted root
        paths have been finalized. Instances constructed via ``from_yaml`` directly (without going through load) do not
        have these attributes populated; access raises AttributeError.

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
    """The name of the experiment performed during the session or Null (None), if the session is not an experiment
    session."""
    python_version: str = "3.14.4"
    """The Python version used to acquire session's data."""
    sollertia_experiment_version: str = "5.0.0"
    """The sollertia-experiment library version used to acquire the session's data."""
    raw_data_path: Path = Path()
    """The path to the root directory that stores the session's raw data."""
    processed_data_path: Path = Path()
    """The path to the root directory that stores the session's processed data."""

    def __post_init__(self) -> None:
        """Coerces the string values loaded from YAML into their typed enum equivalents."""
        if isinstance(self.session_type, str):
            self.session_type = SessionTypes(self.session_type)
        if isinstance(self.acquisition_system, str):
            self.acquisition_system = AcquisitionSystems(self.acquisition_system)

    def _build_sub_dataclasses(self) -> None:
        """Builds the runtime-only ``raw_data``, ``processed_data``, and ``system_raw_data`` sub-dataclass attributes
        from the session's currently configured root paths and acquisition system.

        Raises:
            ValueError: If the session's ``acquisition_system`` is not supported by the platform.
        """
        self.raw_data = RawData.build(root=self.raw_data_path)
        self.processed_data = ProcessedData.build(root=self.processed_data_path)
        builder_cls = SYSTEM_RAW_DATA_REGISTRY.get(AcquisitionSystems(self.acquisition_system))
        if builder_cls is None:
            message = (
                f"Unable to build the system-specific raw data sub-dataclass for the SessionData instance. The "
                f"acquisition system '{self.acquisition_system}' is not supported by the Sollertia platform."
            )
            console.error(message=message, error=ValueError)
        self.system_raw_data = builder_cls.build(root=self.raw_data_path)

    @classmethod
    def create(
        cls,
        animal: AnimalData,
        session_type: str | SessionTypes,
        python_version: str,
        sollertia_experiment_version: str,
        acquisition_system: str | AcquisitionSystems,
        experiment_name: str | None = None,
    ) -> SessionData:
        """Initializes a new data acquisition session and creates its data structure on the host-machine's filesystem.

        Notes:
            To access the data of an already existing session, use the load() method.

        Args:
            animal: The ``AnimalData`` view identifying the data root, project, and animal under which the session
                is created. The session is created under ``animal.session_path(<session_name>)``.
            session_type: The type of the session.
            python_version: The Python version used to acquire the session's data.
            sollertia_experiment_version: The sollertia-experiment library version used to acquire the session's data.
            acquisition_system: The acquisition system that will run the session. Accepts an ``AcquisitionSystems``
                enumeration member or its string value.
            experiment_name: The name of the experiment performed during the session or None, if the session is not
                an experiment session.

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

        # Microsecond UTC timestamps as session names give unique, totally-ordered identifiers across hosts.
        # noinspection PyStringConversionWithoutDunderMethod
        session_name = str(get_timestamp(time_separator="-", output_format=TimestampFormats.STRING))

        # Prevents creating new sessions for non-existent projects.
        if not animal.project.exists():
            message = (
                f"Unable to initialize a new data acquisition session {session_name} for the animal "
                f"'{animal.animal_id}' and project '{animal.project_name}'. The project does not exist on the local "
                f"machine (PC). Use the 'slsa configure project' CLI command to create the project on the local "
                f"machine before creating new sessions."
            )
            console.error(message=message, error=FileNotFoundError)

        # Only the raw_data directory is created here; processed_data is owned by the processing machine and
        # is created later, on a different host, when the session is loaded for processing.
        raw_data_path = animal.session_path(session_name).joinpath(RAW_DATA_DIRECTORY)
        ensure_directory_exists(path=raw_data_path)

        instance = cls(
            project_name=animal.project_name,
            animal_id=animal.animal_id,
            session_name=session_name,
            session_type=session_type,
            acquisition_system=acquisition_system,
            experiment_name=experiment_name,
            python_version=python_version,
            sollertia_experiment_version=sollertia_experiment_version,
            raw_data_path=raw_data_path,
        )

        instance._build_sub_dataclasses()

        # Persisting the marker file here lets future processing or preprocessing reuse this configuration
        # without re-resolving the source paths.
        instance.save()

        if experiment_name is not None:
            experiment_configuration_path = animal.project.configuration_directory.joinpath(f"{experiment_name}.yaml")
            shutil.copy2(
                src=experiment_configuration_path,
                dst=instance.raw_data.experiment_configuration_path,
            )

            # Dispatches the experiment configuration dataclass via EXPERIMENT_CONFIGURATION_REGISTRY so future
            # acquisition systems can plug in their own experiment-configuration schema without modifying this
            # method. Loading from the copied destination avoids re-resolving the source path.
            experiment_configuration_class = EXPERIMENT_CONFIGURATION_REGISTRY[acquisition_system]
            experiment_configuration = experiment_configuration_class.from_yaml(
                file_path=instance.raw_data.experiment_configuration_path,
            )

            # Caches the VR task template that the experiment runs against alongside the experiment configuration,
            # but only when the experiment configuration declares a unity_scene_name. Acquisition systems that do
            # not use Unity-based Virtual Reality omit this field entirely, so the gate below skips template export
            # for non-VR sessions without requiring an explicit per-system branch.
            unity_scene_name = getattr(experiment_configuration, "unity_scene_name", None)
            if unity_scene_name:
                templates_directory = get_task_templates_directory()
                vr_template_path = templates_directory.joinpath(f"{unity_scene_name}.yaml")
                shutil.copy2(
                    src=vr_template_path,
                    dst=instance.raw_data.vr_configuration_path,
                )

        # Marks the session as 'uninitialized' by writing the 'nk.bin' file into raw_data. The acquisition
        # runtime removes this marker once it has finished creating snapshots and initializing instruments
        # (see mark_runtime_initialized). Sessions that still carry the marker hold no data of value and
        # are valid targets for purging. Distinct from the descriptor ``incomplete`` field, which marks
        # initialized sessions that ran into runtime issues but still hold usable data.
        instance.raw_data.nk_path.touch()

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
            FileNotFoundError: If multiple or no 'session_data.yaml' file instances are found under the input
                directory.
        """
        session_data_files = list(session_path.rglob(RawDataFiles.SESSION_DATA))
        if len(session_data_files) != 1:
            message = (
                f"Unable to load the target session's data. Expected a single session_data.yaml file to be located "
                f"under the directory tree specified by the input path: {session_path}. Instead, encountered "
                f"{len(session_data_files)} candidate files. This indicates that the input path does not point to a "
                f"valid session data hierarchy."
            )
            console.error(message=message, error=FileNotFoundError)

        session_data_path = session_data_files.pop()
        instance: SessionData = cls.from_yaml(file_path=session_data_path)

        # The method assumes that the 'donor' YAML file is always stored inside the raw_data directory of the session
        # to be processed. Uses this heuristic to get the path to the root session's directory and re-resolves the
        # raw and processed data root paths against the local filesystem layout so the session remains portable.
        local_root = session_data_path.parents[1]
        instance.raw_data_path = local_root.joinpath(RAW_DATA_DIRECTORY)
        instance.processed_data_path = local_root.joinpath(PROCESSED_DATA_DIRECTORY)

        instance._build_sub_dataclasses()

        return instance

    def mark_runtime_initialized(self) -> None:
        """Removes the 'nk.bin' uninitialized-session marker after acquisition-runtime initialization completes.

        Notes:
            This service method is used by the sollertia-experiment library when it acquires a session's data. Do not
            call it manually. Removal of the marker only changes the ``uninitialized`` signal; the separate descriptor
            ``incomplete`` field is updated independently by the runtime at session end to report whether acquisition
            completed without issues.

            Resolves the marker path directly from ``raw_data_path`` so the method works on instances that have not
            yet been routed through ``_build_sub_dataclasses``.
        """
        self.raw_data_path.joinpath(RawDataFiles.NK_MARKER).unlink(missing_ok=True)

    def save(self) -> None:
        """Caches the instance's data to the session's 'raw_data' directory as a 'session_data.yaml' file.

        Notes:
            Resolves the destination path directly from ``raw_data_path`` so the method works on instances that have
            not yet been routed through ``_build_sub_dataclasses``.
        """
        self.to_yaml(file_path=self.raw_data_path.joinpath(RawDataFiles.SESSION_DATA))
