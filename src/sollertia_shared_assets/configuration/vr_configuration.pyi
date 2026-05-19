import re
from enum import StrEnum
from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

_UINT8_MAX: int
_PROBABILITY_SUM_TOLERANCE: float
_TRIAL_NAME_PATTERN: re.Pattern[str]

class TriggerType(StrEnum):
    LICK = "lick"
    OCCUPANCY = "occupancy"

@dataclass(slots=True)
class Cue:
    name: str
    code: int
    length_cm: float
    texture: str = ...
    def __post_init__(self) -> None: ...

@dataclass(slots=True)
class VREnvironment:
    corridor_spacing_cm: float
    segments_per_corridor: int
    padding_prefab_name: str
    cm_per_unity_unit: float
    cue_offset_cm: float

@dataclass(slots=True)
class TrialStructure:
    cue_sequence: list[str]
    stimulus_trigger_zone_start_cm: float
    stimulus_trigger_zone_end_cm: float
    stimulus_location_cm: float
    show_stimulus_collision_boundary: bool
    trigger_type: str | TriggerType
    transitions: dict[str, float] | None = ...
    def __post_init__(self) -> None: ...

@dataclass
class TaskTemplate(YamlConfig):
    cues: list[Cue]
    vr_environment: VREnvironment
    trial_structures: dict[str, TrialStructure]
    def __post_init__(self) -> None: ...
    @property
    def _cue_by_name(self) -> dict[str, Cue]: ...
    @property
    def _cue_name_to_code(self) -> dict[str, int]: ...
    def _get_trial_length_cm(self, trial_name: str) -> float: ...
    def _get_trial_cue_codes(self, trial_name: str) -> list[int]: ...
    @staticmethod
    def _validate_zone_positions(trial_name: str, trial_structure: TrialStructure, trial_length_cm: float) -> None: ...
