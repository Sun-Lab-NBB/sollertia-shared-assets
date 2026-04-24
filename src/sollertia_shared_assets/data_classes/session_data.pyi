from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from ..configuration import AcquisitionSystems as AcquisitionSystems

class RawDataFiles(StrEnum):
    SESSION_DATA = "session_data.yaml"
    SESSION_DESCRIPTOR = "session_descriptor.yaml"
    SURGERY_METADATA = "surgery_metadata.yaml"
    HARDWARE_STATE = "hardware_state.yaml"
    EXPERIMENT_CONFIGURATION = "experiment_configuration.yaml"
    SYSTEM_CONFIGURATION = "system_configuration.yaml"
    CHECKSUM = "ax_checksum.txt"
    ZABER_POSITIONS = "zaber_positions.yaml"
    MESOSCOPE_POSITIONS = "mesoscope_positions.yaml"
    WINDOW_SCREENSHOT = "window_screenshot.png"

class Directories(StrEnum):
    BEHAVIOR_DATA = "behavior_data"
    CAMERA_DATA = "camera_data"
    CAMERA_TIMESTAMPS = "camera_timestamps"
    CINDRA = "cindra"
    MESOSCOPE_DATA = "mesoscope_data"
    MICROCONTROLLER_DATA = "microcontroller_data"
    MULTI_RECORDING = "multi_recording"

class ProcessingTrackers(StrEnum):
    CHECKSUM = "checksum_processing_tracker.yaml"
    BEHAVIOR = "behavior_processing_tracker.yaml"
    CAMERA = "camera_processing_tracker.yaml"
    VIDEO = "video_processing_tracker.yaml"
    MICROCONTROLLER = "microcontroller_processing_tracker.yaml"
    CINDRA_SINGLE_RECORDING = "single_recording_tracker.yaml"
    CINDRA_MULTI_RECORDING = "multi_recording_tracker.yaml"
    FORGING = "forging_tracker.yaml"
    MANIFEST = "manifest_processing_tracker.yaml"
    TRANSFER = "transfer_processing_tracker.yaml"

class SessionTypes(StrEnum):
    LICK_TRAINING = "lick training"
    RUN_TRAINING = "run training"
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    WINDOW_CHECKING = "window checking"

@dataclass
class SessionData(YamlConfig):
    project_name: str
    animal_id: str
    session_name: str
    session_type: str | SessionTypes
    acquisition_system: str | AcquisitionSystems = ...
    experiment_name: str | None = ...
    python_version: str = ...
    sollertia_experiment_version: str = ...
    raw_data_path: Path = ...
    processed_data_path: Path = ...
    def __post_init__(self) -> None: ...
    @property
    def session_data_path(self) -> Path: ...
    @property
    def session_descriptor_path(self) -> Path: ...
    @property
    def surgery_metadata_path(self) -> Path: ...
    @property
    def hardware_state_path(self) -> Path: ...
    @property
    def experiment_configuration_path(self) -> Path: ...
    @property
    def system_configuration_path(self) -> Path: ...
    @property
    def checksum_path(self) -> Path: ...
    @property
    def checksum_tracker_path(self) -> Path: ...
    @property
    def zaber_positions_path(self) -> Path: ...
    @property
    def mesoscope_positions_path(self) -> Path: ...
    @property
    def window_screenshot_path(self) -> Path: ...
    @property
    def raw_camera_data_path(self) -> Path: ...
    @property
    def raw_behavior_data_path(self) -> Path: ...
    @property
    def raw_microcontroller_data_path(self) -> Path: ...
    @property
    def raw_mesoscope_data_path(self) -> Path: ...
    @property
    def behavior_data_path(self) -> Path: ...
    @property
    def cindra_data_path(self) -> Path: ...
    @property
    def camera_timestamps_path(self) -> Path: ...
    @property
    def camera_data_path(self) -> Path: ...
    @property
    def microcontroller_data_path(self) -> Path: ...
    @property
    def behavior_tracker_path(self) -> Path: ...
    @property
    def camera_tracker_path(self) -> Path: ...
    @property
    def video_tracker_path(self) -> Path: ...
    @property
    def microcontroller_tracker_path(self) -> Path: ...
    @property
    def cindra_single_recording_tracker_path(self) -> Path: ...
    @property
    def cindra_multi_recording_path(self) -> Path: ...
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
    ) -> SessionData: ...
    @classmethod
    def load(cls, session_path: Path) -> SessionData: ...
    def mark_runtime_initialized(self) -> None: ...
    def save(self) -> None: ...
