"""Provides system-agnostic experiment configuration classes.

This module contains dataclasses for defining experiment states and trial structures that are independent of
the specific data acquisition system. These classes serve as the foundation for system-specific experiment
configurations.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    reinforcing_initial_guided_trials: int = 0
    """The number of reinforcing trials after the onset of the experiment state that use the guidance mode."""
    reinforcing_recovery_failed_threshold: int = 0
    """The number of sequentially failed reinforcing trials after which to enable the recovery guidance mode."""
    reinforcing_recovery_guided_trials: int = 0
    """The number of guided reinforcing trials to use in the recovery guidance mode."""
    aversive_initial_guided_trials: int = 0
    """The number of aversive trials after the onset of the experiment state that use the guidance mode."""
    aversive_recovery_failed_threshold: int = 0
    """The number of sequentially failed aversive trials after which to enable the recovery guidance mode."""
    aversive_recovery_guided_trials: int = 0
    """The number of guided aversive trials to use in the recovery guidance mode."""


@dataclass(slots=True)
class WaterRewardTrial:
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
class GasPuffTrial:
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
