from pathlib import Path
from dataclasses import field, dataclass

from ataraxis_data_structures import YamlConfig

from .session_data import SessionTypes as SessionTypes
from ..configuration import AcquisitionSystems as AcquisitionSystems

@dataclass(frozen=True, slots=True)
class DatasetSession:
    session: str
    animal: str
    session_path: Path = ...

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
    ) -> DatasetData: ...
    @classmethod
    def load(cls, dataset_path: Path) -> DatasetData: ...
    def save(self) -> None: ...
    @property
    def animals(self) -> tuple[str, ...]: ...
    def get_sessions_for_animal(self, animal: str) -> tuple[DatasetSession, ...]: ...
    def get_session(self, animal: str, session: str) -> DatasetSession: ...
