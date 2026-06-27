from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from ..enums import (
    SessionTypes as SessionTypes,
    AcquisitionSystems as AcquisitionSystems,
)
from ..registries import (
    SYSTEM_SESSION_TYPES as SYSTEM_SESSION_TYPES,
    SYSTEM_RAW_DATA_REGISTRY as SYSTEM_RAW_DATA_REGISTRY,
    SESSION_TYPES_USING_VR_TASK as SESSION_TYPES_USING_VR_TASK,
    EXPERIMENT_CONFIGURATION_REGISTRY as EXPERIMENT_CONFIGURATION_REGISTRY,
)
from ..configuration import get_task_templates_directory as get_task_templates_directory
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
    RUNTIME_DATA = "runtime_data"
    VIDEO_DATA = "video_data"
    MICROCONTROLLER_DATA = "microcontroller_data"
    CINDRA = "cindra"
    MULTI_RECORDING = "multi_recording"

class ProcessingTrackers(StrEnum):
    CHECKSUM = "checksum_processing_tracker.yaml"
    RUNTIME = "runtime_processing_tracker.yaml"
    MICROCONTROLLER = "microcontroller_processing_tracker.yaml"
    VIDEO = "video_processing_tracker.yaml"
    TWO_PHOTON = "single_recording_tracker.yaml"
    CINDRA_MULTI_RECORDING = "multi_recording_tracker.yaml"
    FORGING = "forging_tracker.yaml"
    MANIFEST = "manifest_processing_tracker.yaml"

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
    runtime_data_path: Path
    runtime_tracker_path: Path
    video_data_path: Path
    video_tracker_path: Path
    microcontroller_data_path: Path
    microcontroller_tracker_path: Path
    cindra_data_path: Path
    two_photon_tracker_path: Path
    cindra_multi_recording_path: Path
    @classmethod
    def build(cls, root: Path) -> ProcessedData: ...

@dataclass
class SessionData(YamlConfig):
    project_name: str
    animal_id: str
    session_name: str
    session_type: str | SessionTypes
    acquisition_system: str | AcquisitionSystems
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
    def required_raw_assets(self) -> list[tuple[str, Path]]: ...
    def mark_runtime_initialized(self) -> None: ...
    def save(self) -> None: ...
