from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_data_structures import YamlConfig

from ..enums import (
    SessionTypes as SessionTypes,
    AcquisitionSystems as AcquisitionSystems,
)
from .session_data import RawDataFiles as RawDataFiles

class DatasetFiles(StrEnum):
    DATA = "data.feather"
    DESCRIPTIONS = "data_descriptions.feather"

@dataclass(frozen=True, slots=True)
class DatasetSession:
    session: str
    animal: str
    session_path: Path = ...
    @property
    def data_path(self) -> Path: ...
    @property
    def descriptor_path(self) -> Path: ...
    @property
    def vr_configuration_path(self) -> Path: ...
    @property
    def experiment_configuration_path(self) -> Path: ...

@dataclass(frozen=True, slots=True)
class DatasetAnimal:
    animal: str
    animal_path: Path = ...
    @property
    def surgery_path(self) -> Path: ...

@dataclass
class DatasetData(YamlConfig):
    name: str
    project: str
    session_type: str | SessionTypes
    acquisition_system: str | AcquisitionSystems
    sessions: tuple[DatasetSession, ...] = field(default_factory=tuple)
    dataset_data_path: Path = ...
    def __post_init__(self) -> None: ...
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
    ) -> DatasetData: ...
    @classmethod
    def load(cls, dataset_path: Path) -> DatasetData: ...
    def save(self) -> None: ...
    @property
    def descriptions_path(self) -> Path: ...
    def _write_column_descriptions(self, column_descriptions: dict[str, str]) -> None: ...
    def column_descriptions(self) -> dict[str, str]: ...
    def get_column_description(self, column: str) -> str: ...
    @property
    def animals(self) -> tuple[DatasetAnimal, ...]: ...
    def get_animal(self, animal: str) -> DatasetAnimal: ...
    def get_sessions_for_animal(self, animal: str) -> tuple[DatasetSession, ...]: ...
    def get_session(self, animal: str, session: str) -> DatasetSession: ...
