"""Provides VR environment configuration classes for Unity task templates and experiment configurations. These classes
define the schema for the task template YAML files Unity uses for prefab generation and runtime.
"""

from __future__ import annotations

import re
from enum import StrEnum
import math
from dataclasses import dataclass

from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig

_UINT8_MAX: int = 255
"""Maximum value for uint8 cue codes."""

_PROBABILITY_SUM_TOLERANCE: float = 0.001
"""Tolerance for validating that trial transition probabilities sum to 1.0."""

NAME_COMPONENT_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z0-9_]+$")
"""The pattern the trial and cue names must match to be safe to embed in Unity asset filenames.

Restricts both names to ASCII letters, digits, and underscores so the ``TemplateName-TrialName`` segment naming scheme
and the ``Cue_Name_LengthCm`` cue naming scheme used by ``sollertia-virtual-reality`` cannot be corrupted by path
separators, whitespace, or punctuation introduced in a template. Excluding the hyphen from both halves of a segment name
is what lets a segment filename split back to exactly one owning template. Barring whitespace from a cue name also keeps
the space-joined cue sequence signature unambiguous, since Unity compares trials on that signature. ``ConfigLoader.cs``
compiles the same pattern and applies it independently to the template filename stem, to each cue name, and to each
trial name. This module applies it to cue names and trial names only, because a ``TaskTemplate`` instance carries no
filename of its own. The filename stem is checked at the authoring boundary instead, by ``write_template_tool``, so a
template this library writes cannot carry a stem that ``ConfigLoader.cs`` would later refuse to load.
"""


class TriggerType(StrEnum):
    """Defines the supported stimulus trigger zone activators for experiment trials.

    Notes:
        These are the platform-wide trigger mechanisms. Each acquisition system supports the subset it can resolve
        to its own stimuli (Mesoscope-VR supports INTERACTION and OCCUPANCY_DISARM, and leaves the rest unmapped).
        INTERACTION maps to the StimulusTriggerZone prefab (GuidanceZone child) and the three occupancy types to the
        OccupancyTriggerZone prefab (OccupancyZone + OccupancyGuidanceZone children) in Unity. COLLISION reuses the
        StimulusTriggerZone prefab as a bare boundary wall.
    """

    INTERACTION = "interaction"
    """An interaction-triggered trial where the animal must engage an interaction sensor (lick port, button,
    lever, pressure plate) inside the stimulus trigger zone to elicit stimulus delivery."""
    COLLISION = "collision"
    """A collision-triggered trial where crossing the invisible boundary wall elicits stimulus delivery
    unconditionally, with no sensor or occupancy requirement."""
    OCCUPANCY_DISARM = "occupancy_disarm"
    """An occupancy-disarm trial where occupying the zone disarms the boundary. Colliding with the still-armed
    boundary (occupancy not met) elicits stimulus delivery."""
    OCCUPANCY_ARM = "occupancy_arm"
    """An occupancy-arm trial where occupying the zone arms the boundary. Colliding with the now-armed
    boundary (occupancy met) elicits stimulus delivery."""
    OCCUPANCY_TRIGGER = "occupancy_trigger"
    """An occupancy-trigger trial where occupying the zone for the required duration elicits stimulus
    delivery immediately, with no boundary collision."""


@dataclass(frozen=True, slots=True)
class Cue:
    """Defines a single visual cue used in the experiment task's Virtual Reality (VR) environment.

    Notes:
        Cues are baked into segment prefabs.
    """

    name: str
    """The visual identifier for the cue (e.g., 'A', 'B', 'Gray'). Used to reference the cue in trial cue sequences."""
    code: int
    """The unique uint8 code (0-255) that identifies the cue during MQTT communication and data analysis."""
    length_cm: float
    """The length of the cue in centimeters."""
    texture: str
    """The texture filename (e.g., ``Cue 016 - 4x1.png``) located in the Unity project's
    ``Assets/InfiniteCorridorTask/Textures/`` directory. Applied 1:1 to the cue wall panels during prefab generation."""

    def __post_init__(self) -> None:
        """Validates cue definition parameters."""
        if not self.name:
            message = "Unable to initialize Cue. The name must be a non-empty string, but got an empty value."
            console.error(message=message, error=ValueError)
        if not NAME_COMPONENT_PATTERN.match(self.name):
            message = (
                f"Unable to initialize Cue '{self.name}'. The name must contain only ASCII letters, digits, and "
                f"underscores, because it is embedded in the generated cue asset filename and in the cue sequence "
                f"signature that identifies a trial."
            )
            console.error(message=message, error=ValueError)
        if not 0 <= self.code <= _UINT8_MAX:
            message = (
                f"Unable to initialize Cue '{self.name}'. The code must be a uint8 value in range [0, 255], but got "
                f"{self.code}."
            )
            console.error(message=message, error=ValueError)
        # A non-finite length passes every ordered comparison, so it would otherwise reach Unity and produce an
        # infinite segment. The same guard covers every VREnvironment scalar below.
        if not math.isfinite(self.length_cm) or self.length_cm <= 0:
            message = (
                f"Unable to initialize Cue '{self.name}'. The length_cm must be a positive, finite value, but got "
                f"{self.length_cm} cm."
            )
            console.error(message=message, error=ValueError)
        # Unity resolves this filename against its own Textures directory and refuses a cue that names none, so the
        # same requirement is enforced here, where the template is authored.
        if not self.texture:
            message = (
                f"Unable to initialize Cue '{self.name}'. The texture must be a non-empty filename naming a texture "
                f"in the Unity project's Textures directory, but got an empty value."
            )
            console.error(message=message, error=ValueError)


@dataclass(frozen=True, slots=True)
class VREnvironment:
    """Defines the Unity Virtual Reality (VR) corridor system configuration.

    Notes:
        Every numeric field divides or sizes downstream corridor geometry, so the validation below rejects a value
        that would leave Unity with an infinite segment length, a zero-depth corridor, or a maze generation loop that
        never terminates. The ``padding_prefab_name`` field names a Unity prefab and carries no geometric validation.

        Each default matches the one the Unity ``VREnvironment`` class declares for the same field, so a template that
        omits the key loads here with the geometry Unity would apply to it.
    """

    corridor_spacing_cm: float = 20.0
    """The horizontal spacing between corridor instances in centimeters."""
    segments_per_corridor: int = 3
    """The number of segments visible in each corridor instance (corridor depth)."""
    padding_prefab_name: str = "Padding"
    """The name of the Unity prefab used for corridor padding."""
    cm_per_unity_unit: float = 10.0
    """The conversion factor from centimeters to Unity units."""
    cue_offset_cm: float = 0.0
    """The offset of the animal's starting position relative to the Virtual Reality (VR) environment's cue sequence
    origin, in centimeters."""

    def __post_init__(self) -> None:
        """Validates corridor geometry parameters."""
        # The YAML loader does not enforce the field annotation, so a float depth reaches this check. NaN and positive
        # infinity compare False against the lower bound, and a fractional depth has no meaning to the maze generator.
        # A bool would also pass an isinstance check as an int, so the depth must be exactly an integer.
        if type(self.segments_per_corridor) is not int or self.segments_per_corridor < 1:
            message = (
                "Unable to initialize VREnvironment. The segments_per_corridor must be an integer of at least 1, but "
                f"got {self.segments_per_corridor}."
            )
            console.error(message=message, error=ValueError)
        if not math.isfinite(self.cm_per_unity_unit) or self.cm_per_unity_unit <= 0:
            message = (
                "Unable to initialize VREnvironment. The cm_per_unity_unit must be a positive, finite value, but got "
                f"{self.cm_per_unity_unit}."
            )
            console.error(message=message, error=ValueError)
        if not math.isfinite(self.corridor_spacing_cm) or self.corridor_spacing_cm <= 0:
            message = (
                "Unable to initialize VREnvironment. The corridor_spacing_cm must be a positive, finite value, but "
                f"got {self.corridor_spacing_cm}."
            )
            console.error(message=message, error=ValueError)
        if not math.isfinite(self.cue_offset_cm):
            message = (
                "Unable to initialize VREnvironment. The cue_offset_cm must be a finite value, but got "
                f"{self.cue_offset_cm}."
            )
            console.error(message=message, error=ValueError)


@dataclass(frozen=True, slots=True)
class TrialStructure:
    """Defines the spatial configuration of a trial structure for Unity prefabs.

    Notes:
        This class contains only the spatial data needed by Unity for prefab generation and runtime zone
        configuration. Experiment-specific parameters (reward sizes, puff durations, etc.) live on the matching
        runtime trial classes defined by each acquisition system and are joined back by trial name.
    """

    cue_sequence: list[str]
    """The ordered sequence of cue names that comprise the trial's segment."""
    stimulus_trigger_zone_start_cm: float
    """The position of the trial stimulus trigger zone starting boundary, in centimeters."""
    stimulus_trigger_zone_end_cm: float
    """The position of the trial stimulus trigger zone ending boundary, in centimeters."""
    stimulus_location_cm: float
    """The position of the stimulus boundary (invisible wall), in centimeters. The collision, occupancy_disarm, and
    occupancy_arm trigger types elicit the stimulus on collision with this boundary, while the interaction and
    occupancy_trigger types elicit it from the sensor and the occupancy timer instead."""
    show_stimulus_collision_boundary: bool
    """Determines whether the stimulus collision boundary marker is visible to the animal during this trial type.
    When True, Unity enables the MeshRenderer on the trigger zone's root object, so the marker sits wherever the
    trigger type places that root. A collision trial anchors the boundary wall's leading edge on the stimulus
    location, so the root itself sits half the fixed wall depth past it. An interaction trial places the root at the
    trigger-zone midpoint, and an occupancy trial offsets it from the stimulus location by half the zone length."""
    trigger_type: str | TriggerType
    """The stimulus trigger zone behavior. Must be one of the valid TriggerType enumeration members."""
    occupancy_duration_ms: float | None = None
    """The duration in milliseconds the animal must occupy the zone for occupancy trigger modes. Unity enforces this
    value, and the template is its single source of truth: no experiment configuration carries a copy. Set it to None on
    a non-occupancy trial, because None is how a template communicates that the field is unused, while 0 is a real
    duration and is rejected on every trial whatever its trigger type."""
    transitions: dict[str, float] | None = None
    """Transition probabilities to the trials that make up the task's corridor environment. Keys must reference
    trial names defined on the same TaskTemplate, including this trial itself. If provided and non-empty, values must
    sum to 1.0. Set to null in the YAML file if not used."""

    def __post_init__(self) -> None:
        """Validates trial structure definition parameters."""
        if not self.cue_sequence:
            message = (
                "Unable to initialize TrialStructure. The cue_sequence must contain at least one cue, but got an "
                "empty sequence."
            )
            console.error(message=message, error=ValueError)

        if self.transitions:
            for target_name, probability in self.transitions.items():
                # A negative weight lets the set sum to 1.0 while removing its target from the sampled distribution,
                # and a NaN weight compares False against every ordered comparison, so it also slips past the sum
                # tolerance below. The chained form rejects both, along with either infinity.
                if not 0.0 <= probability <= 1.0:
                    message = (
                        f"Unable to initialize TrialStructure. The transition probability for '{target_name}' must be "
                        f"a finite value in range [0.0, 1.0], but got {probability}."
                    )
                    console.error(message=message, error=ValueError)

            probability_sum = sum(self.transitions.values())
            if abs(probability_sum - 1.0) > _PROBABILITY_SUM_TOLERANCE:
                message = (
                    f"Unable to initialize TrialStructure. The transitions must sum to 1.0, but got {probability_sum}."
                )
                console.error(message=message, error=ValueError)

        # None is how a template says the field is unused, so a non-occupancy trial leaves it None rather than 0.
        # A supplied value is a real duration whatever the trigger type, so the positive finite range binds all of them.
        if self.occupancy_duration_ms is not None and (
            not math.isfinite(self.occupancy_duration_ms) or self.occupancy_duration_ms <= 0
        ):
            message = (
                "Unable to initialize TrialStructure. The occupancy_duration_ms must be a positive, finite value, but "
                f"got {self.occupancy_duration_ms}."
            )
            console.error(message=message, error=ValueError)

        # Occupancy trigger modes read occupancy_duration_ms at runtime, so it is required for them. A non-occupancy
        # mode ignores the field at runtime and still carries None rather than a placeholder number. StrEnum members
        # compare equal to their string values, so this covers both a raw string and a coerced TriggerType.
        occupancy_types = (TriggerType.OCCUPANCY_DISARM, TriggerType.OCCUPANCY_ARM, TriggerType.OCCUPANCY_TRIGGER)
        if self.trigger_type in occupancy_types and self.occupancy_duration_ms is None:
            message = (
                f"Unable to initialize TrialStructure. The trigger_type '{self.trigger_type}' is an occupancy mode, "
                "so occupancy_duration_ms is required, but it is unset."
            )
            console.error(message=message, error=ValueError)


@dataclass
class TaskTemplate(YamlConfig):
    """Defines a VR task template used by Unity for prefab generation and runtime configuration.

    Notes:
        Task templates contain only the data Unity needs for prefab generation and runtime. Experiment-specific
        parameters (rewards, guidance, experiment states) live on the matching runtime trial classes defined by each
        acquisition system. Those classes are joined back to the template by trial name.

        This dataclass can parse any valid task configuration (template) .yaml file from the sollertia-virtual-reality
        project.
    """

    cues: list[Cue]
    """The Virtual Reality environment wall cues used in the task."""
    vr_environment: VREnvironment
    """The Virtual Reality corridor configuration."""
    trial_structures: dict[str, TrialStructure]
    """The spatial configuration for each trial type. Keys are trial names (e.g., 'ABC')."""

    def __post_init__(self) -> None:
        """Validates task template configuration.

        Runs the full cascade of integrity checks against the loaded template. The checks run in this order: cue catalog
        uniqueness (codes and names), trial name pattern, per-trial cue references, transition targets, trigger types,
        zone positions within trial segment bounds, and cue-sequence uniqueness across trials.

        Raises:
            ValueError: If any of the validations above fails. The message identifies the offending field and
                the specific constraint that was violated.
        """
        codes = [cue.code for cue in self.cues]
        if len(codes) != len(set(codes)):
            duplicate_codes = {code for code in codes if codes.count(code) > 1}
            message = (
                f"Unable to initialize TaskTemplate. The cue codes must each be unique, but got duplicate codes "
                f"{duplicate_codes}."
            )
            console.error(message=message, error=ValueError)

        names = [cue.name for cue in self.cues]
        if len(names) != len(set(names)):
            duplicate_names = {name for name in names if names.count(name) > 1}
            message = (
                f"Unable to initialize TaskTemplate. The cue names must each be unique, but got duplicate names "
                f"{duplicate_names}."
            )
            console.error(message=message, error=ValueError)

        cue_names = set(names)
        defined_trial_names = set(self.trial_structures.keys())
        valid_trigger_types = {trigger_type.value for trigger_type in TriggerType}
        for trial_name, trial_structure in self.trial_structures.items():
            # Rejects trial names containing characters other than ASCII letters, digits, and underscores.
            # Trial names are embedded verbatim in Unity segment prefab filenames, so any path separator or
            # whitespace would corrupt the generated filesystem layout.
            if not NAME_COMPONENT_PATTERN.match(trial_name):
                message = (
                    f"Unable to initialize TaskTemplate. Trial name '{trial_name}' is invalid. Trial names "
                    "must contain only ASCII letters, digits, and underscores (used in generated segment "
                    "prefab filenames on the Unity side)."
                )
                console.error(message=message, error=ValueError)

            for cue_name in trial_structure.cue_sequence:
                if cue_name not in cue_names:
                    message = (
                        f"Unable to initialize TaskTemplate. Trial structure '{trial_name}' references unknown cue "
                        f"'{cue_name}'. Available cues: {', '.join(sorted(cue_names))}."
                    )
                    console.error(message=message, error=ValueError)

            if trial_structure.transitions:
                for target_name in trial_structure.transitions:
                    if target_name not in defined_trial_names:
                        message = (
                            f"Unable to initialize TaskTemplate. Trial structure '{trial_name}' has a transition "
                            f"to unknown trial '{target_name}'. Available trials: "
                            f"{', '.join(sorted(defined_trial_names))}."
                        )
                        console.error(message=message, error=ValueError)

            # Accepts both TriggerType enum and string values for YAML compatibility.
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

            trial_length_cm = self._get_trial_length_cm(trial_name=trial_name)
            self._validate_zone_positions(
                trial_name=trial_name,
                trial_structure=trial_structure,
                trial_length_cm=trial_length_cm,
            )

        # Rejects two trials that share an identical cue sequence. Identical cue sequences are indistinguishable to
        # the experiment's cue-stream decomposer, which would silently merge them into a single decoded trial.
        seen_sequences: dict[tuple[str, ...], str] = {}
        for trial_name, trial_structure in self.trial_structures.items():
            signature = tuple(trial_structure.cue_sequence)
            if signature in seen_sequences:
                message = (
                    f"Unable to initialize TaskTemplate. Trials '{seen_sequences[signature]}' and '{trial_name}' "
                    "share an identical cue sequence. Each trial must have a unique cue sequence so the experiment "
                    "can identify it; use distinct cue codes (textures may be shared) to multiplex identical visuals."
                )
                console.error(message=message, error=ValueError)
            seen_sequences[signature] = trial_name

    @property
    def _cue_by_name(self) -> dict[str, Cue]:
        """Indexes the template's cues by their human-readable name for fast lookup during validation."""
        return {cue.name: cue for cue in self.cues}

    def _get_trial_length_cm(self, trial_name: str) -> float:
        """Returns the total length of the VR trial's segment in centimeters.

        Args:
            trial_name: The name of the trial structure whose segment length to compute.

        Returns:
            The combined length of the trial's cue sequence, in centimeters.
        """
        trial = self.trial_structures[trial_name]
        cue_map = self._cue_by_name
        return sum(cue_map[cue_name].length_cm for cue_name in trial.cue_sequence)

    @staticmethod
    def _validate_zone_positions(trial_name: str, trial_structure: TrialStructure, trial_length_cm: float) -> None:
        """Validates the trial's zone positions within its segment bounds, per trigger type.

        Collision trials validate only the boundary location. The occupancy_trigger trials validate only the trigger
        zone. The other trigger types validate the zone, the boundary, and their relative ordering.

        Args:
            trial_name: The name of the trial structure being validated.
            trial_structure: The trial structure to validate.
            trial_length_cm: The total length of the trial's segment in centimeters.
        """
        trigger_value = (
            trial_structure.trigger_type.value
            if isinstance(trial_structure.trigger_type, TriggerType)
            else trial_structure.trigger_type
        )
        validates_zone = trigger_value != TriggerType.COLLISION.value
        validates_boundary = trigger_value != TriggerType.OCCUPANCY_TRIGGER.value

        if validates_zone:
            TaskTemplate._validate_trigger_zone_bounds(
                trial_name=trial_name, trial_structure=trial_structure, trial_length_cm=trial_length_cm
            )
        if validates_boundary:
            TaskTemplate._validate_stimulus_location_bounds(
                trial_name=trial_name, trial_structure=trial_structure, trial_length_cm=trial_length_cm
            )
        if validates_zone and validates_boundary:
            TaskTemplate._validate_location_not_before_zone(trial_name=trial_name, trial_structure=trial_structure)

    @staticmethod
    def _validate_trigger_zone_bounds(trial_name: str, trial_structure: TrialStructure, trial_length_cm: float) -> None:
        """Validates that the trigger zone start and end are ordered and within the trial's segment bounds."""
        if trial_structure.stimulus_trigger_zone_end_cm < trial_structure.stimulus_trigger_zone_start_cm:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_trigger_zone_end_cm must "
                f"be greater than or equal to stimulus_trigger_zone_start_cm "
                f"({trial_structure.stimulus_trigger_zone_start_cm}), but got "
                f"{trial_structure.stimulus_trigger_zone_end_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= trial_structure.stimulus_trigger_zone_start_cm <= trial_length_cm:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_trigger_zone_start_cm "
                f"must be within the trial length (0 to {trial_length_cm} cm), but got "
                f"{trial_structure.stimulus_trigger_zone_start_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= trial_structure.stimulus_trigger_zone_end_cm <= trial_length_cm:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_trigger_zone_end_cm must "
                f"be within the trial length (0 to {trial_length_cm} cm), but got "
                f"{trial_structure.stimulus_trigger_zone_end_cm}."
            )
            console.error(message=message, error=ValueError)

    @staticmethod
    def _validate_stimulus_location_bounds(
        trial_name: str, trial_structure: TrialStructure, trial_length_cm: float
    ) -> None:
        """Validates that the stimulus (boundary) location is within the trial's segment bounds."""
        if not 0 <= trial_structure.stimulus_location_cm <= trial_length_cm:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_location_cm must be "
                f"within the trial length (0 to {trial_length_cm} cm), but got "
                f"{trial_structure.stimulus_location_cm}."
            )
            console.error(message=message, error=ValueError)

    @staticmethod
    def _validate_location_not_before_zone(trial_name: str, trial_structure: TrialStructure) -> None:
        """Validates that the stimulus location does not precede the trigger zone start."""
        if trial_structure.stimulus_location_cm < trial_structure.stimulus_trigger_zone_start_cm:
            message = (
                f"Unable to validate zone positions for trial '{trial_name}'. The stimulus_location_cm must not "
                f"precede the stimulus_trigger_zone_start_cm "
                f"({trial_structure.stimulus_trigger_zone_start_cm}), but got "
                f"{trial_structure.stimulus_location_cm}."
            )
            console.error(message=message, error=ValueError)
