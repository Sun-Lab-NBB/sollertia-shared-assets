from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from .vr_configuration import (
    Cue as Cue,
    Segment as Segment,
    VREnvironment as VREnvironment,
)
from .experiment_configuration import (
    GasPuffTrial as GasPuffTrial,
    ExperimentState as ExperimentState,
    WaterRewardTrial as WaterRewardTrial,
)

@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    cues: list[Cue]
    segments: list[Segment]
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial]
    experiment_states: dict[str, ExperimentState]
    vr_environment: VREnvironment
    unity_scene_name: str
    cue_offset_cm: float = ...
    @property
    def _cue_by_name(self) -> dict[str, Cue]: ...
    @property
    def _cue_name_to_code(self) -> dict[str, int]: ...
    @property
    def _segment_by_name(self) -> dict[str, Segment]: ...
    def _get_segment_length_cm(self, segment_name: str) -> float: ...
    def _get_segment_cue_codes(self, segment_name: str) -> list[int]: ...
    def __post_init__(self) -> None: ...
