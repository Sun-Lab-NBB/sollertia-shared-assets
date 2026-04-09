"""Provides VR environment configuration classes for Unity task templates and experiment configurations.

These classes define the schema for task template YAML files that Unity uses for prefab generation and runtime.
System-agnostic and system-specific configuration classes in this library inherit from these base classes to add
experiment-specific parameters.
"""

from enum import StrEnum
from dataclasses import dataclass

from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig

_UINT8_MAX: int = 255
"""Maximum value for uint8 cue codes."""

_PROBABILITY_SUM_TOLERANCE: float = 0.001
"""Tolerance for validating that segment transition probabilities sum to 1.0."""


class TriggerType(StrEnum):
    """Defines the supported stimulus trigger zone activators for experiment trials.

    Notes:
        All Sollertia platform acquisition systems share these core trial types. LICK corresponds to GuidanceZone in
        Unity and OCCUPANCY corresponds to OccupancyZone in Unity.
    """

    LICK = "lick"
    """Indicates a lick-triggered trial where the animal must lick inside the stimulus trigger zone to elicit stimulus
    delivery."""
    OCCUPANCY = "occupancy"
    """Indicates an occupancy-triggered trial where the animal must occupy the trigger zone for a specified duration to
    disable the stimulus delivery."""


@dataclass
class Cue:
    """Defines a single visual cue used in the experiment task's Virtual Reality (VR) environment.

    Notes:
        Each cue has a unique name (used in the Unity segment (prefab) definitions) and a unique uint8 code (used during
        MQTT communication and analysis). Cues are not loaded as individual prefabs - they are baked into segment
        prefabs.
    """

    name: str
    """The visual identifier for the cue (e.g., 'A', 'B', 'Gray'). Used to reference the cue in segment definitions."""
    code: int
    """The unique uint8 code (0-255) that identifies the cue during MQTT communication and data analysis."""
    length_cm: float
    """The length of the cue in centimeters."""
    texture: str = ""
    """The texture filename (e.g., ``Cue 016 - 4x1.png``) located in the Unity project's
    ``Assets/InfiniteCorridorTask/Textures/`` directory. Applied 1:1 to the cue wall panels during prefab generation.
    Defaults to an empty string for backwards compatibility with templates that predate this field."""

    def __post_init__(self) -> None:
        """Validates cue definition parameters."""
        if not 0 <= self.code <= _UINT8_MAX:
            message = (
                f"Unable to initialize Cue '{self.name}'. The code must be a uint8 value in range [0, 255], but got "
                f"{self.code}."
            )
            console.error(message=message, error=ValueError)
        if self.length_cm <= 0:
            message = (
                f"Unable to initialize Cue '{self.name}'. The length_cm must be greater than 0, but got "
                f"{self.length_cm} cm."
            )
            console.error(message=message, error=ValueError)


@dataclass
class Segment:
    """Defines a visual segment (sequence of cues) used in the experiment task's Virtual Reality (VR) environment.

    Notes:
        Segments are the building blocks of the infinite corridor, each containing a sequence of visual cues
        and optional transition probabilities for segment-to-segment transitions.
    """

    name: str
    """The unique identifier of the segment's Unity prefab file."""
    cue_sequence: list[str]
    """The ordered sequence of cue names that comprise this segment."""
    transition_probabilities: list[float] | None
    """Transition probabilities to other segments that make up the task's corridor environment. If provided, must sum
    to 1.0. Set to null in the YAML file if not used."""

    def __post_init__(self) -> None:
        """Validates segment definition parameters."""
        if not self.cue_sequence:
            message = (
                f"Unable to initialize Segment '{self.name}'. The cue_sequence must contain at least one cue, but "
                f"got an empty sequence."
            )
            console.error(message=message, error=ValueError)

        if self.transition_probabilities:
            probability_sum = sum(self.transition_probabilities)
            if abs(probability_sum - 1.0) > _PROBABILITY_SUM_TOLERANCE:
                message = (
                    f"Unable to initialize Segment '{self.name}'. The transition_probabilities must sum to 1.0, but "
                    f"got {probability_sum}."
                )
                console.error(message=message, error=ValueError)


@dataclass
class VREnvironment:
    """Defines the Unity Virtual Reality (VR) corridor system configuration.

    Notes:
        This class is primarily used by Unity to configure the task environment. Python parses these values
        from the YAML configuration file but does not use them at runtime.
    """

    corridor_spacing_cm: float
    """The horizontal spacing between corridor instances in centimeters."""
    segments_per_corridor: int
    """The number of segments visible in each corridor instance (corridor depth)."""
    padding_prefab_name: str
    """The name of the Unity prefab used for corridor padding."""
    cm_per_unity_unit: float
    """The conversion factor from centimeters to Unity units."""


@dataclass
class TrialStructure:
    """Defines the spatial configuration of a trial structure for Unity prefabs.

    Notes:
        This base class contains only the spatial data needed by Unity for prefab generation and runtime zone
        configuration. Experiment-specific parameters (reward sizes, puff durations, etc.) are added by subclasses
        in mesoscope_configuration.py.

        The trigger_type field specifies the stimulus trigger zone behavior and determines which experiment trial
        class (WaterRewardTrial or GasPuffTrial) is created when loading this template for experiment configuration.
    """

    segment_name: str
    """The name of the Unity Segment this trial structure is based on."""
    stimulus_trigger_zone_start_cm: float
    """The position of the trial stimulus trigger zone starting boundary, in centimeters."""
    stimulus_trigger_zone_end_cm: float
    """The position of the trial stimulus trigger zone ending boundary, in centimeters."""
    stimulus_location_cm: float
    """The location of the invisible boundary (wall) with which the animal must collide to elicit the stimulus."""
    show_stimulus_collision_boundary: bool
    """Determines whether the stimulus collision boundary is visible to the animal during this trial type. When True,
    the boundary marker is displayed in the Virtual Reality environment at the stimulus location."""
    trigger_type: str | TriggerType
    """Specifies the stimulus trigger zone behavior. Must be one of the valid TriggerType enumeration members."""


@dataclass
class TaskTemplate(YamlConfig):
    """Defines a VR task template used by Unity for prefab generation and runtime configuration.

    Notes:
        Task templates contain only the data Unity needs for prefab generation and runtime. Experiment-specific
        parameters (rewards, guidance, experiment states) are not included here — those are added by system-specific
        experiment configuration classes that use the full trial structure classes inheriting from TrialStructure.

        This dataclass can parse any valid task configuration (template) .yaml file from the sollertia-unity-tasks
        project.
    """

    cues: list[Cue]
    """Defines the Virtual Reality environment wall cues used in the task."""
    segments: list[Segment]
    """Defines the Virtual Reality environment segments (sequences of wall cues) for the Unity corridor system."""
    trial_structures: dict[str, TrialStructure]
    """Defines the spatial configuration for each trial type. Keys are trial names (e.g., 'ABC')."""
    vr_environment: VREnvironment
    """Defines the Virtual Reality corridor configuration."""
    cue_offset_cm: float
    """Specifies the offset of the animal's starting position relative to the Virtual Reality (VR) environment's cue
    sequence origin, in centimeters."""

    @property
    def _cue_by_name(self) -> dict[str, Cue]:
        """Returns the mapping of cue names to their Cue class instances for all VR cues used in the template."""
        return {cue.name: cue for cue in self.cues}

    @property
    def _segment_by_name(self) -> dict[str, Segment]:
        """Returns the mapping of segment names to their Segment class instances for all VR segments used in the
        template.
        """
        return {segment.name: segment for segment in self.segments}

    def _get_segment_length_cm(self, segment_name: str) -> float:
        """Returns the total length of the VR segment in centimeters."""
        segment = self._segment_by_name[segment_name]
        cue_map = self._cue_by_name
        return sum(cue_map[cue_name].length_cm for cue_name in segment.cue_sequence)

    def __post_init__(self) -> None:
        """Validates task template configuration."""
        # Ensures cue codes are unique.
        codes = [cue.code for cue in self.cues]
        if len(codes) != len(set(codes)):
            duplicate_codes = {code for code in codes if codes.count(code) > 1}
            message = (
                f"Unable to initialize TaskTemplate. The cue codes must each be unique, but got duplicate codes "
                f"{duplicate_codes}."
            )
            console.error(message=message, error=ValueError)

        # Ensures cue names are unique.
        names = [cue.name for cue in self.cues]
        if len(names) != len(set(names)):
            duplicate_names = {name for name in names if names.count(name) > 1}
            message = (
                f"Unable to initialize TaskTemplate. The cue names must each be unique, but got duplicate names "
                f"{duplicate_names}."
            )
            console.error(message=message, error=ValueError)

        # Ensures segment cue sequences reference valid cues.
        cue_names = {cue.name for cue in self.cues}
        for segment in self.segments:
            for cue_name in segment.cue_sequence:
                if cue_name not in cue_names:
                    message = (
                        f"Unable to initialize TaskTemplate. Segment '{segment.name}' references unknown cue "
                        f"'{cue_name}'. Available cues: {', '.join(sorted(cue_names))}."
                    )
                    console.error(message=message, error=ValueError)

        # Validates trial structure segment references and trigger types.
        segment_names = {segment.name for segment in self.segments}
        valid_trigger_types = {trigger_type.value for trigger_type in TriggerType}
        for trial_name, trial_structure in self.trial_structures.items():
            if trial_structure.segment_name not in segment_names:
                message = (
                    f"Unable to initialize TaskTemplate. Trial structure '{trial_name}' references unknown segment "
                    f"'{trial_structure.segment_name}'. Available segments: {', '.join(sorted(segment_names))}."
                )
                console.error(message=message, error=ValueError)

            # Validates trigger_type values. Accepts both TriggerType enum and string values for YAML compatibility.
            trigger_value = (
                trial_structure.trigger_type.value
                if isinstance(trial_structure.trigger_type, TriggerType)
                else trial_structure.trigger_type
            )
            if trigger_value not in valid_trigger_types:
                message = (
                    f"Unable to initialize TaskTemplate. Trial structure '{trial_name}' has invalid trigger_type "
                    f"'{trial_structure.trigger_type}'. Valid values: {', '.join(sorted(valid_trigger_types))}."
                )
                console.error(message=message, error=ValueError)

            # Validates zone positions are within segment bounds.
            segment_length = self._get_segment_length_cm(segment_name=trial_structure.segment_name)
            self._validate_zone_positions(
                trial_name=trial_name,
                trial_structure=trial_structure,
                segment_length=segment_length,
            )

    @staticmethod
    def _validate_zone_positions(trial_name: str, trial_structure: TrialStructure, segment_length: float) -> None:
        """Validates that zone positions are within the segment bounds.

        Args:
            trial_name: The name of the trial structure being validated.
            trial_structure: The trial structure to validate.
            segment_length: The total length of the segment in centimeters.
        """
        if trial_structure.stimulus_trigger_zone_end_cm < trial_structure.stimulus_trigger_zone_start_cm:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_trigger_zone_end_cm must "
                f"be greater than or equal to stimulus_trigger_zone_start_cm "
                f"({trial_structure.stimulus_trigger_zone_start_cm}), but got "
                f"{trial_structure.stimulus_trigger_zone_end_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= trial_structure.stimulus_trigger_zone_start_cm <= segment_length:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_trigger_zone_start_cm "
                f"must be within the segment length (0 to {segment_length} cm), but got "
                f"{trial_structure.stimulus_trigger_zone_start_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= trial_structure.stimulus_trigger_zone_end_cm <= segment_length:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_trigger_zone_end_cm must "
                f"be within the segment length (0 to {segment_length} cm), but got "
                f"{trial_structure.stimulus_trigger_zone_end_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= trial_structure.stimulus_location_cm <= segment_length:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_location_cm must be "
                f"within the segment length (0 to {segment_length} cm), but got "
                f"{trial_structure.stimulus_location_cm}."
            )
            console.error(message=message, error=ValueError)

        if trial_structure.stimulus_location_cm < trial_structure.stimulus_trigger_zone_start_cm:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_location_cm must not "
                f"precede the stimulus_trigger_zone_start_cm "
                f"({trial_structure.stimulus_trigger_zone_start_cm}), but got "
                f"{trial_structure.stimulus_location_cm}."
            )
            console.error(message=message, error=ValueError)
