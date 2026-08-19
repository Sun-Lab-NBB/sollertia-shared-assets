from enum import StrEnum
from typing import Any
from pathlib import Path
from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from ..configuration import (
    TriggerType as TriggerType,
    TaskTemplate as TaskTemplate,
    ExperimentState as ExperimentState,
)

_DEFAULT_STATE_DURATION_S: int
_DEFAULT_INITIAL_GUIDED_TRIALS: int
_DEFAULT_RECOVERY_FAILED_THRESHOLD: int
_DEFAULT_RECOVERY_GUIDED_TRIALS: int
_DISCRIMINATOR_FIELD: str

class TrialKind(StrEnum):
    WATER = "water"
    PUFF = "puff"

@dataclass(frozen=True, slots=True)
class MesoscopeWaterRewardTrial:
    reward_size_ul: float = ...
    reward_tone_duration_ms: int = ...
    trial_kind: TrialKind = ...
    def __post_init__(self) -> None: ...

@dataclass(frozen=True, slots=True)
class MesoscopeGasPuffTrial:
    puff_duration_ms: int = ...
    trial_kind: TrialKind = ...
    def __post_init__(self) -> None: ...

@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    trial_structures: dict[str, MesoscopeWaterRewardTrial | MesoscopeGasPuffTrial]
    experiment_states: dict[str, ExperimentState]
    unity_scene_name: str
    def __post_init__(self) -> None: ...
    @classmethod
    def from_task_template(
        cls,
        template: TaskTemplate,
        unity_scene_name: str,
        state_count: int = 1,
        default_reward_size_ul: float = 5.0,
        default_reward_tone_duration_ms: int = 300,
        default_puff_duration_ms: int = 100,
    ) -> MesoscopeExperimentConfiguration: ...
    @classmethod
    def restore_excluded_fields(cls, data: dict[Any, Any], file_path: Path) -> dict[Any, Any]: ...

_TRIAL_CLASSES: tuple[tuple[TrialKind, type], ...]

def _restore_trial_kind(trial_name: str, trial: Any) -> Any: ...
def _unique_trial_fields() -> dict[TrialKind, frozenset[str]]: ...
