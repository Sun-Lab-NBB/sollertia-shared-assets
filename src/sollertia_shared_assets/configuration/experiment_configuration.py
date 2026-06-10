"""Provides system-agnostic experiment configuration building blocks.

This module contains the ``ExperimentState`` dataclass and the system-agnostic trial classes (``WaterRewardTrial``
and ``GasPuffTrial``) that define experiment phases and trial primitives independent of the specific data acquisition
system. System-specific experiment configurations compose these into their own schema.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class WaterRewardTrial:
    """Defines a trial that delivers a water reward (a reinforcing stimulus) when the animal meets the trial's success
    condition.

    The reward is a configured volume of water accompanied by an auditory tone. The behavioral condition that earns
    the reward is defined by the task and the acquisition system, not by this class.
    """

    reward_size_ul: float = 5.0
    """The volume of water, in microliters, to deliver when the animal successfully completes the trial."""
    reward_tone_duration_ms: int = 300
    """The duration, in milliseconds, to sound the auditory tone when delivering the water reward."""


@dataclass(frozen=True, slots=True)
class GasPuffTrial:
    """Defines a trial that delivers a gas puff (an aversive stimulus) when the animal fails the trial's avoidance
    condition.

    The animal avoids the puff by satisfying the task's occupancy condition; failing to do so delivers a puff of the
    configured duration. The behavioral condition is defined by the task and the acquisition system, not by this class.
    """

    puff_duration_ms: int = 100
    """The duration, in milliseconds, for which to deliver the gas puff when the animal fails the trial."""
