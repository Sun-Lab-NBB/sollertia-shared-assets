from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from ..configuration import AcquisitionSystems as AcquisitionSystems

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
