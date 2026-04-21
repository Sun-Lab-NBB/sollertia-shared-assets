from enum import StrEnum
from pathlib import Path
from collections.abc import Callable

from .vr_configuration import (
    TriggerType as TriggerType,
    TaskTemplate as TaskTemplate,
)
from .mesoscope_configuration import MesoscopeExperimentConfiguration as MesoscopeExperimentConfiguration
from .experiment_configuration import (
    GasPuffTrial as GasPuffTrial,
    ExperimentState as ExperimentState,
    WaterRewardTrial as WaterRewardTrial,
)

class AcquisitionSystems(StrEnum):
    MESOSCOPE_VR = "mesoscope"

type ExperimentConfigFactory = Callable[
    [TaskTemplate, str, dict[str, WaterRewardTrial | GasPuffTrial], float], MesoscopeExperimentConfiguration
]

_experiment_config_factory_registry: dict[str, ExperimentConfigFactory]
_DEFAULT_STATE_DURATION_S: int
_DEFAULT_INITIAL_GUIDED_TRIALS: int
_DEFAULT_RECOVERY_FAILED_THRESHOLD: int
_DEFAULT_RECOVERY_GUIDED_TRIALS: int

def set_working_directory(path: Path) -> None: ...
def get_working_directory() -> Path: ...
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
def _create_mesoscope_experiment_config(
    template: TaskTemplate,
    unity_scene_name: str,
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial],
    cue_offset_cm: float,
) -> MesoscopeExperimentConfiguration: ...
