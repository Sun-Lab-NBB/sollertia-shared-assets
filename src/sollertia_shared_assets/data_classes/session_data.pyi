from enum import StrEnum
from typing import Any, Protocol
from pathlib import Path
from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from ..configuration import (
    EXPERIMENT_CONFIGURATION_REGISTRY as EXPERIMENT_CONFIGURATION_REGISTRY,
    AcquisitionSystems as AcquisitionSystems,
    get_task_templates_directory as get_task_templates_directory,
)
from .project_hierarchy import AnimalData as AnimalData

RAW_DATA_DIRECTORY: str
PROCESSED_DATA_DIRECTORY: str

class RawDataFiles(StrEnum):
    SESSION_DATA = "session_data.yaml"
    SESSION_DESCRIPTOR = "session_descriptor.yaml"
    SURGERY_METADATA = "surgery_metadata.yaml"
    HARDWARE_STATE = "hardware_state.yaml"
    EXPERIMENT_CONFIGURATION = "experiment_configuration.yaml"
    VR_CONFIGURATION = "vr_configuration.yaml"
    SYSTEM_CONFIGURATION = "system_configuration.yaml"
    CHECKSUM = "ax_checksum.txt"
    NK_MARKER = "nk.bin"

class Directories(StrEnum):
    BEHAVIOR_DATA = "behavior_data"
    CAMERA_DATA = "camera_data"
    CAMERA_TIMESTAMPS = "camera_timestamps"
    MICROCONTROLLER_DATA = "microcontroller_data"
    CINDRA = "cindra"
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
    ANALYSIS = "analysis_tracker.yaml"
    MANIFEST = "manifest_processing_tracker.yaml"
    TRANSFER = "transfer_processing_tracker.yaml"

class SessionTypes(StrEnum):
    LICK_TRAINING = "lick training"
    RUN_TRAINING = "run training"
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    WINDOW_CHECKING = "window checking"

class MesoscopeRawDataFiles(StrEnum):
    ZABER_POSITIONS = "zaber_positions.yaml"
    MESOSCOPE_POSITIONS = "mesoscope_positions.yaml"
    WINDOW_SCREENSHOT = "window_screenshot.png"

class MesoscopeDirectories(StrEnum):
    MESOSCOPE_DATA = "mesoscope_data"

@dataclass(slots=True)
class RawData:
    session_data_path: Path
    session_descriptor_path: Path
    surgery_metadata_path: Path
    hardware_state_path: Path
    system_configuration_path: Path
    experiment_configuration_path: Path
    vr_configuration_path: Path
    checksum_path: Path
    checksum_tracker_path: Path
    nk_path: Path
    behavior_data_path: Path
    camera_data_path: Path
    @classmethod
    def build(cls, root: Path) -> RawData: ...

@dataclass(slots=True)
class ProcessedData:
    behavior_data_path: Path
    behavior_tracker_path: Path
    camera_timestamps_path: Path
    camera_tracker_path: Path
    video_data_path: Path
    video_tracker_path: Path
    microcontroller_data_path: Path
    microcontroller_tracker_path: Path
    cindra_data_path: Path
    cindra_single_recording_tracker_path: Path
    cindra_multi_recording_path: Path
    @classmethod
    def build(cls, root: Path) -> ProcessedData: ...

@dataclass(slots=True)
class MesoscopeRawData:
    zaber_positions_path: Path
    mesoscope_positions_path: Path
    window_screenshot_path: Path
    mesoscope_data_path: Path
    @classmethod
    def build(cls, root: Path) -> MesoscopeRawData: ...

class _SystemRawDataBuilder(Protocol):
    @classmethod
    def build(cls, root: Path) -> Any: ...

SYSTEM_RAW_DATA_REGISTRY: dict[AcquisitionSystems, type[_SystemRawDataBuilder]]

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
    raw_data = ...
    processed_data = ...
    system_raw_data = ...
    def _build_sub_dataclasses(self) -> None: ...
    @classmethod
    def create(
        cls,
        animal: AnimalData,
        session_type: str | SessionTypes,
        python_version: str,
        sollertia_experiment_version: str,
        acquisition_system: str | AcquisitionSystems,
        experiment_name: str | None = None,
    ) -> SessionData: ...
    @classmethod
    def load(cls, session_path: Path) -> SessionData: ...
    def mark_runtime_initialized(self) -> None: ...
    def save(self) -> None: ...
