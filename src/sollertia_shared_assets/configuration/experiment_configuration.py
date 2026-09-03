"""Provides the system-agnostic ``ExperimentState`` dataclass that defines experiment phases independently of the data
acquisition system. Each system-specific experiment configuration composes it into its own schema alongside the runtime
trial classes that system defines.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ataraxis_base_utilities import console


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
    """Determines whether trials are executed during this experiment state. This is a declarative annotation: no
    production code in sollertia-experiment or sollertia-forgery reads it, and a trial-free phase is realized by the
    state's ``system_state_code`` alone."""
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

    def __post_init__(self) -> None:
        """Validates the experiment state's duration and guidance trial counters.

        Raises:
            ValueError: If the ``state_duration_s`` field does not hold a positive, finite value, or if any of the
                guidance trial counter fields holds a negative value.
        """
        # The acquisition runtime maintains the state for as long as the elapsed time stays below this duration, so a
        # non-positive value retires the phase on the first evaluation and skips it without reporting an error. A
        # positive infinity never elapses and a NaN compares False against every bound, so both are barred as well.
        if not math.isfinite(self.state_duration_s) or self.state_duration_s <= 0:
            message = (
                "Unable to initialize ExperimentState. The state_duration_s must be a positive, finite value, but got "
                f"{self.state_duration_s}."
            )
            console.error(message=message, error=ValueError)

        # Each counter counts trials, so zero disables the guidance mode it configures, while a negative count asks the
        # runtime for a trial quantity it is unable to issue.
        guidance_counters = (
            ("reinforcing_initial_guided_trials", self.reinforcing_initial_guided_trials),
            ("reinforcing_recovery_failed_threshold", self.reinforcing_recovery_failed_threshold),
            ("reinforcing_recovery_guided_trials", self.reinforcing_recovery_guided_trials),
            ("aversive_initial_guided_trials", self.aversive_initial_guided_trials),
            ("aversive_recovery_failed_threshold", self.aversive_recovery_failed_threshold),
            ("aversive_recovery_guided_trials", self.aversive_recovery_guided_trials),
        )
        for counter_name, counter_value in guidance_counters:
            if counter_value < 0:
                message = (
                    f"Unable to initialize ExperimentState. The {counter_name} must be a non-negative integer, but "
                    f"got {counter_value}."
                )
                console.error(message=message, error=ValueError)
