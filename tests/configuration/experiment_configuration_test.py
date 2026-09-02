"""Contains tests for the system-agnostic ``ExperimentState`` dataclass provided by the
``configuration.experiment_configuration`` module.
"""

from __future__ import annotations

import math

import pytest

from sollertia_shared_assets.configuration import ExperimentState


def test_experiment_state_initialization() -> None:
    """Verifies basic initialization of ExperimentState."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
        aversive_initial_guided_trials=5,
        aversive_recovery_failed_threshold=3,
        aversive_recovery_guided_trials=2,
    )

    assert state.experiment_state_code == 1
    assert state.system_state_code == 0
    assert state.state_duration_s == 600.0
    assert state.supports_trials
    assert state.reinforcing_initial_guided_trials == 10
    assert state.reinforcing_recovery_failed_threshold == 5
    assert state.reinforcing_recovery_guided_trials == 3
    assert state.aversive_initial_guided_trials == 5
    assert state.aversive_recovery_failed_threshold == 3
    assert state.aversive_recovery_guided_trials == 2


def test_experiment_state_field_types() -> None:
    """Verifies the data types of ExperimentState fields."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
    )

    assert isinstance(state.experiment_state_code, int)
    assert isinstance(state.system_state_code, int)
    assert isinstance(state.state_duration_s, float)
    assert isinstance(state.supports_trials, bool)
    assert isinstance(state.reinforcing_initial_guided_trials, int)
    assert isinstance(state.reinforcing_recovery_failed_threshold, int)
    assert isinstance(state.reinforcing_recovery_guided_trials, int)
    assert isinstance(state.aversive_initial_guided_trials, int)
    assert isinstance(state.aversive_recovery_failed_threshold, int)
    assert isinstance(state.aversive_recovery_guided_trials, int)


def test_experiment_state_minimal_initialization() -> None:
    """Verifies that a positive state_duration_s constructs with the guidance counters left at their defaults."""
    state = ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=0.5)

    assert state.state_duration_s == 0.5
    assert state.reinforcing_initial_guided_trials == 0
    assert state.aversive_recovery_guided_trials == 0


def test_experiment_state_zero_duration_raises_error() -> None:
    """Verifies that a zero state_duration_s raises ValueError."""
    with pytest.raises(ValueError, match=r"state_duration_s must be a positive, finite value"):
        ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=0.0)


def test_experiment_state_negative_duration_raises_error() -> None:
    """Verifies that a negative state_duration_s raises ValueError."""
    with pytest.raises(ValueError, match=r"state_duration_s must be a positive, finite value"):
        ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=-5.0)


def test_experiment_state_infinite_duration_raises_error() -> None:
    """Verifies that an infinite state_duration_s raises ValueError."""
    with pytest.raises(ValueError, match=r"state_duration_s must be a positive, finite value"):
        ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=math.inf)


def test_experiment_state_nan_duration_raises_error() -> None:
    """Verifies that a NaN state_duration_s raises ValueError."""
    with pytest.raises(ValueError, match=r"state_duration_s must be a positive, finite value"):
        ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=math.nan)


@pytest.mark.parametrize(
    "counter_name",
    [
        "reinforcing_initial_guided_trials",
        "reinforcing_recovery_failed_threshold",
        "reinforcing_recovery_guided_trials",
        "aversive_initial_guided_trials",
        "aversive_recovery_failed_threshold",
        "aversive_recovery_guided_trials",
    ],
)
def test_experiment_state_negative_guidance_counter_raises_error(counter_name: str) -> None:
    """Verifies that a negative guidance trial counter raises ValueError."""
    with pytest.raises(ValueError, match=rf"{counter_name} must be a non-negative integer"):
        ExperimentState(
            experiment_state_code=1,
            system_state_code=0,
            state_duration_s=600.0,
            **{counter_name: -1},
        )
