"""Contains tests for the system-agnostic experiment configuration dataclasses provided by the
``configuration.experiment_configuration`` module.
"""

from __future__ import annotations

from sollertia_shared_assets.configuration import (
    GasPuffTrial,
    ExperimentState,
    WaterRewardTrial,
)


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
    assert state.supports_trials is True
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


def test_water_reward_trial_defaults() -> None:
    """Verifies that WaterRewardTrial fields default to documented values."""
    trial = WaterRewardTrial()
    assert trial.reward_size_ul == 5.0
    assert trial.reward_tone_duration_ms == 300


def test_water_reward_trial_initialization() -> None:
    """Verifies basic initialization of WaterRewardTrial."""
    trial = WaterRewardTrial(reward_size_ul=4.5, reward_tone_duration_ms=250)
    assert trial.reward_size_ul == 4.5
    assert trial.reward_tone_duration_ms == 250


def test_gas_puff_trial_defaults() -> None:
    """Verifies that GasPuffTrial fields default to documented values."""
    trial = GasPuffTrial()
    assert trial.puff_duration_ms == 100
    assert trial.occupancy_duration_ms == 1000


def test_gas_puff_trial_initialization() -> None:
    """Verifies basic initialization of GasPuffTrial."""
    trial = GasPuffTrial(puff_duration_ms=150, occupancy_duration_ms=1500)
    assert trial.puff_duration_ms == 150
    assert trial.occupancy_duration_ms == 1500


def test_trial_field_types() -> None:
    """Verifies the data types of trial fields for both water and gas puff trials."""
    water_trial = WaterRewardTrial(reward_size_ul=5.0, reward_tone_duration_ms=300)
    assert isinstance(water_trial.reward_size_ul, float)
    assert isinstance(water_trial.reward_tone_duration_ms, int)

    gas_trial = GasPuffTrial(puff_duration_ms=100, occupancy_duration_ms=1000)
    assert isinstance(gas_trial.puff_duration_ms, int)
    assert isinstance(gas_trial.occupancy_duration_ms, int)
