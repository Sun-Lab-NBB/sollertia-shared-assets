"""Contains tests for the system-agnostic experiment configuration dataclasses provided by the
``configuration.experiment_configuration`` module.
"""

from __future__ import annotations

import pytest

from sollertia_shared_assets.configuration import (
    Cue,
    Segment,
    GasPuffTrial,
    VREnvironment,
    ExperimentState,
    WaterRewardTrial,
    MesoscopeExperimentConfiguration,
)


def _create_test_config_with_trial(trial: WaterRewardTrial | GasPuffTrial) -> MesoscopeExperimentConfiguration:
    """Builds a MesoscopeExperimentConfiguration wrapping a single trial with a 200 cm "TestSegment".

    Trials reference a segment through segment_name; cue_sequence and trial_length_cm are derived fields populated
    by MesoscopeExperimentConfiguration.__post_init__. Zone validation requires trial_length_cm > 0, so tests that
    exercise zone validation must go through the full configuration.
    """
    cues = [
        Cue(name="A", code=1, length_cm=50.0, texture="Cue 016 - 4x1.png"),
        Cue(name="B", code=2, length_cm=50.0, texture="Cue 001 - 4x1.png"),
        Cue(name="C", code=3, length_cm=50.0, texture="Cue 008 - 2x1 repeat.png"),
        Cue(name="D", code=4, length_cm=50.0, texture="Cue 002 - 4x1.png"),
    ]
    segments = [Segment(name="TestSegment", cue_sequence=["A", "B", "C", "D"], transition_probabilities=None)]
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=60.0,
        supports_trials=True,
    )
    return MesoscopeExperimentConfiguration(
        cues=cues,
        segments=segments,
        trial_structures={"test_trial": trial},
        experiment_states={"state1": state},
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
        ),
        unity_scene_name="TestScene",
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


def test_water_reward_trial_initialization() -> None:
    """Verifies basic initialization of WaterRewardTrial after derived fields are populated."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    config = _create_test_config_with_trial(trial)
    populated_trial = config.trial_structures["test_trial"]

    assert populated_trial.segment_name == "TestSegment"
    assert populated_trial.cue_sequence == [1, 2, 3, 4]
    assert populated_trial.trial_length_cm == 200.0
    assert populated_trial.stimulus_trigger_zone_start_cm == 180.0
    assert populated_trial.stimulus_trigger_zone_end_cm == 200.0
    assert populated_trial.stimulus_location_cm == 190.0
    assert populated_trial.show_stimulus_collision_boundary is False
    assert populated_trial.reward_size_ul == 5.0
    assert populated_trial.reward_tone_duration_ms == 300


def test_gas_puff_trial_initialization() -> None:
    """Verifies basic initialization of GasPuffTrial after derived fields are populated."""
    trial = GasPuffTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    config = _create_test_config_with_trial(trial)
    populated_trial = config.trial_structures["test_trial"]

    assert populated_trial.segment_name == "TestSegment"
    assert populated_trial.cue_sequence == [1, 2, 3, 4]
    assert populated_trial.trial_length_cm == 200.0
    assert populated_trial.stimulus_trigger_zone_start_cm == 180.0
    assert populated_trial.stimulus_trigger_zone_end_cm == 200.0
    assert populated_trial.stimulus_location_cm == 190.0
    assert populated_trial.show_stimulus_collision_boundary is False
    assert populated_trial.puff_duration_ms == 100
    assert populated_trial.occupancy_duration_ms == 1000


def test_trial_field_types() -> None:
    """Verifies the data types of trial fields for both water and gas puff trials."""
    water_trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )
    config = _create_test_config_with_trial(water_trial)
    water_trial = config.trial_structures["test_trial"]

    assert isinstance(water_trial.segment_name, str)
    assert isinstance(water_trial.cue_sequence, list)
    assert all(isinstance(cue, int) for cue in water_trial.cue_sequence)
    assert isinstance(water_trial.trial_length_cm, float)
    assert isinstance(water_trial.stimulus_trigger_zone_start_cm, float)
    assert isinstance(water_trial.stimulus_trigger_zone_end_cm, float)
    assert isinstance(water_trial.stimulus_location_cm, float)
    assert isinstance(water_trial.show_stimulus_collision_boundary, bool)
    assert isinstance(water_trial.reward_size_ul, float)
    assert isinstance(water_trial.reward_tone_duration_ms, int)

    gas_trial = GasPuffTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )
    config = _create_test_config_with_trial(gas_trial)
    gas_trial = config.trial_structures["test_trial"]

    assert isinstance(gas_trial.puff_duration_ms, int)
    assert isinstance(gas_trial.occupancy_duration_ms, int)
    assert isinstance(gas_trial.show_stimulus_collision_boundary, bool)


def test_trial_zone_end_less_than_start_raises_error() -> None:
    """Verifies that zone_end < zone_start raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=170.0,
        stimulus_location_cm=175.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match=r"must be greater than or equal to"):
        _create_test_config_with_trial(trial)


def test_trial_zone_start_outside_trial_length_raises_error() -> None:
    """Verifies that zone_start outside trial length raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=250.0,
        stimulus_trigger_zone_end_cm=260.0,
        stimulus_location_cm=255.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match=r"stimulus_trigger_zone_start_cm.*must be within"):
        _create_test_config_with_trial(trial)


def test_trial_zone_end_outside_trial_length_raises_error() -> None:
    """Verifies that zone_end outside trial length raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=250.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match=r"stimulus_trigger_zone_end_cm.*must be within"):
        _create_test_config_with_trial(trial)


def test_trial_stimulus_location_outside_trial_length_raises_error() -> None:
    """Verifies that stimulus_location outside trial length raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=250.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match=r"stimulus_location_cm.*must be within"):
        _create_test_config_with_trial(trial)


def test_trial_stimulus_location_precedes_trigger_zone_raises_error() -> None:
    """Verifies that stimulus_location before trigger zone start raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=170.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match=r"(?s)stimulus_location_cm.*must not precede"):
        _create_test_config_with_trial(trial)


def test_validate_zones_zero_length_raises_error() -> None:
    """Verifies that BaseTrial.validate_zones raises ValueError when trial_length_cm has not been populated."""
    trial = WaterRewardTrial(
        segment_name="Seg",
        stimulus_trigger_zone_start_cm=10.0,
        stimulus_trigger_zone_end_cm=20.0,
        stimulus_location_cm=15.0,
        show_stimulus_collision_boundary=False,
    )

    with pytest.raises(ValueError, match=r"trial_length_cm must be populated"):
        trial.validate_zones()
