"""Provides system-agnostic experiment configuration building blocks.

This module contains the ``ExperimentState`` dataclass that defines experiment phases independent of the specific
data acquisition system. System-specific experiment configurations compose it into their own schema alongside the
runtime trial classes each acquisition system defines in its own subpackage.
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
