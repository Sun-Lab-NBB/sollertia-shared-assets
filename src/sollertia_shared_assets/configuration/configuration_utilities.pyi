from enum import StrEnum
from pathlib import Path
from dataclasses import field, dataclass
from collections.abc import Callable

from ataraxis_data_structures import YamlConfig

from .vr_configuration import (
    TriggerType as TriggerType,
    TaskTemplate as TaskTemplate,
)
from .mesoscope_configuration import (
    MesoscopeSystemConfiguration as MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration as MesoscopeExperimentConfiguration,
)
from .experiment_configuration import (
    GasPuffTrial as GasPuffTrial,
    ExperimentState as ExperimentState,
    WaterRewardTrial as WaterRewardTrial,
)

class AcquisitionSystems(StrEnum):
    MESOSCOPE_VR = "mesoscope"

@dataclass
class ServerConfiguration(YamlConfig):
    username: str = ...
    password: str = ...
    host: str = ...
    storage_root: Path = field(default_factory=Path)
    working_root: Path = field(default_factory=Path)
    shared_directory_name: str = ...
    shared_storage_root: Path = field(init=False, default_factory=Path)
    shared_working_root: Path = field(init=False, default_factory=Path)
    user_data_root: Path = field(init=False, default_factory=Path)
    user_working_root: Path = field(init=False, default_factory=Path)
    def __post_init__(self) -> None: ...

type SystemConfiguration = MesoscopeSystemConfiguration
type ExperimentConfigFactory = Callable[
    [TaskTemplate, str, dict[str, WaterRewardTrial | GasPuffTrial], float], MesoscopeExperimentConfiguration
]

_SYSTEM_CONFIG_CLASSES: dict[str, type[SystemConfiguration]]
_CONFIG_FILE_TO_CLASS: dict[str, type[SystemConfiguration]]
_EXPERIMENT_CONFIG_FACTORIES: dict[str, ExperimentConfigFactory]
_DEFAULT_STATE_DURATION_S: int
_DEFAULT_INITIAL_GUIDED_TRIALS: int
_DEFAULT_RECOVERY_FAILED_THRESHOLD: int
_DEFAULT_RECOVERY_GUIDED_TRIALS: int

def set_working_directory(path: Path) -> None: ...
def get_working_directory() -> Path: ...
def create_system_configuration_file(system: AcquisitionSystems | str) -> None: ...
def get_system_configuration_data() -> SystemConfiguration: ...
def create_experiment_configuration(
    template: TaskTemplate,
    system: AcquisitionSystems | str,
    unity_scene_name: str,
    default_reward_size_ul: float = 5.0,
    default_reward_tone_duration_ms: int = 300,
    default_puff_duration_ms: int = 100,
    default_occupancy_duration_ms: int = 1000,
) -> MesoscopeExperimentConfiguration: ...
def populate_default_experiment_states(
    experiment_configuration: MesoscopeExperimentConfiguration, state_count: int
) -> None: ...
def set_google_credentials_path(path: Path) -> None: ...
def get_google_credentials_path() -> Path: ...
def set_task_templates_directory(path: Path) -> None: ...
def get_task_templates_directory() -> Path: ...
def create_server_configuration_file(
    username: str, password: str, host: str, storage_root: Path, working_root: Path, shared_directory_name: str
) -> None: ...
def get_server_configuration() -> ServerConfiguration: ...
def _create_mesoscope_experiment_config(
    template: TaskTemplate,
    unity_scene_name: str,
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial],
    cue_offset_cm: float,
) -> MesoscopeExperimentConfiguration: ...
