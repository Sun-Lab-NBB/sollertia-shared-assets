from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from .experiment_configuration import (
    GasPuffTrial as GasPuffTrial,
    ExperimentState as ExperimentState,
    WaterRewardTrial as WaterRewardTrial,
)

@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial]
    experiment_states: dict[str, ExperimentState]
    unity_scene_name: str
