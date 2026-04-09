"""Provides system-agnostic experiment configuration classes.

This module contains dataclasses for defining experiment states and trial structures that are independent of
the specific data acquisition system. These classes serve as the foundation for system-specific experiment
configurations.
"""

from dataclasses import field, dataclass

from ataraxis_base_utilities import console

from .vr_configuration import TriggerType, TrialStructure


@dataclass(slots=True)
class ExperimentState:
    """Defines the structure and runtime parameters of an experiment state (phase)."""

    experiment_state_code: int
    """The unique identifier code of the experiment state."""
    system_state_code: int
    """The data acquisition system's state (configuration snapshot) code associated with the experiment state."""
    state_duration_s: float
    """The time, in seconds, to maintain the experiment state while executing the experiment."""
    supports_trials: bool = True
    """Determines whether trials are executed during this experiment state. When False, no trial-related processing
    occurs during this phase."""
    # Configures reinforcing (water reward) trial guidance behavior.
    reinforcing_initial_guided_trials: int = 0
    """The number of reinforcing trials after the onset of the experiment state that use the guidance mode."""
    reinforcing_recovery_failed_threshold: int = 0
    """The number of sequentially failed reinforcing trials after which to enable the recovery guidance mode."""
    reinforcing_recovery_guided_trials: int = 0
    """The number of guided reinforcing trials to use in the recovery guidance mode."""
    # Configures aversive (gas puff) trial guidance behavior.
    aversive_initial_guided_trials: int = 0
    """The number of aversive trials after the onset of the experiment state that use the guidance mode."""
    aversive_recovery_failed_threshold: int = 0
    """The number of sequentially failed aversive trials after which to enable the recovery guidance mode."""
    aversive_recovery_guided_trials: int = 0
    """The number of guided aversive trials to use in the recovery guidance mode."""


@dataclass(slots=True)
class BaseTrial(TrialStructure):
    """Extends TrialStructure with experiment runtime fields common to all supported experiment trial types.

    Notes:
        Inherits spatial configuration fields from TrialStructure, including segment mapping and zone positions.

        The trigger_type field is inherited but not used at runtime. Trial behavior is determined by the concrete
        class type (WaterRewardTrial or GasPuffTrial), not the trigger_type value. The field exists only to maintain
        schema compatibility with task templates.
    """

    trigger_type: str | TriggerType = ""
    """Inherited from TrialStructure but not used at runtime. Trial behavior is determined by concrete class type."""
    cue_sequence: list[int] = field(default_factory=list)
    """The sequence of segment wall cue identifiers experienced by the animal when participating in this trial
    type."""
    trial_length_cm: float = 0.0
    """The total length of the trial environment in centimeters."""

    def validate_zones(self) -> None:
        """Validates stimulus zone positions.

        Notes:
            This method must be called after trial_length_cm is populated by the experiment configuration class that
            uses this class.
        """
        if self.trial_length_cm <= 0:
            message = (
                f"Unable to validate zone positions. The trial_length_cm must be populated before validation, "
                f"but got {self.trial_length_cm}."
            )
            console.error(message=message, error=ValueError)

        if self.stimulus_trigger_zone_end_cm < self.stimulus_trigger_zone_start_cm:
            message = (
                f"Unable to validate zone positions. The stimulus_trigger_zone_end_cm must be greater than or "
                f"equal to stimulus_trigger_zone_start_cm ({self.stimulus_trigger_zone_start_cm}), but got "
                f"{self.stimulus_trigger_zone_end_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= self.stimulus_trigger_zone_start_cm <= self.trial_length_cm:
            message = (
                f"Unable to validate zone positions. The stimulus_trigger_zone_start_cm must be within the "
                f"trial length (0 to {self.trial_length_cm} cm), but got {self.stimulus_trigger_zone_start_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= self.stimulus_trigger_zone_end_cm <= self.trial_length_cm:
            message = (
                f"Unable to validate zone positions. The stimulus_trigger_zone_end_cm must be within the "
                f"trial length (0 to {self.trial_length_cm} cm), but got {self.stimulus_trigger_zone_end_cm}."
            )
            console.error(message=message, error=ValueError)

        if not 0 <= self.stimulus_location_cm <= self.trial_length_cm:
            message = (
                f"Unable to validate zone positions. The stimulus_location_cm must be within the trial length "
                f"(0 to {self.trial_length_cm} cm), but got {self.stimulus_location_cm}."
            )
            console.error(message=message, error=ValueError)

        if self.stimulus_location_cm < self.stimulus_trigger_zone_start_cm:
            message = (
                f"Unable to validate zone positions. The stimulus_location_cm must not precede the "
                f"stimulus_trigger_zone_start_cm ({self.stimulus_trigger_zone_start_cm}), but got "
                f"{self.stimulus_location_cm}."
            )
            console.error(message=message, error=ValueError)


@dataclass(slots=True)
class WaterRewardTrial(BaseTrial):
    """Defines a trial that delivers water rewards (reinforcing stimuli) when the animal licks in the trigger zone.

    Notes:
        In trigger mode, the animal must lick while inside the stimulus trigger zone to receive the water
        reward. In guidance mode, the animal receives the reward upon colliding with the stimulus boundary,
        with no lick required.
    """

    reward_size_ul: float = 5.0
    """The volume of water, in microliters, to deliver when the animal successfully completes the trial."""
    reward_tone_duration_ms: int = 300
    """The duration, in milliseconds, to sound the auditory tone when delivering the water reward."""


@dataclass(slots=True)
class GasPuffTrial(BaseTrial):
    """Defines a trial that delivers N2 gas puffs (aversive stimuli) when the animal fails to meet occupancy duration.

    Notes:
        In trigger mode, the animal must occupy the stimulus trigger zone for the specified duration to
        disarm the stimulus boundary and avoid the gas puff. If the animal exits the zone early or collides
        with the boundary before meeting the occupancy threshold, the gas puff is delivered. In guidance
        mode, when the animal exits the zone early, an OccupancyFailed message is emitted, allowing
        sollertia-experiment to block movement and prevent the animal from reaching the armed boundary.
    """

    puff_duration_ms: int = 100
    """The duration, in milliseconds, for which to deliver the N2 gas puff when the animal fails the trial."""
    occupancy_duration_ms: int = 1000
    """The time, in milliseconds, the animal must occupy the trigger zone to disarm the stimulus boundary and avoid
    the gas puff."""
