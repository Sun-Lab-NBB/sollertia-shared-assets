"""Contains tests for the descriptor and hardware-state dataclasses in ``mesoscope_vr.runtime_data``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sollertia_shared_assets.mesoscope_vr import (
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_mesoscope_hardware_state_defaults_to_none() -> None:
    """Verifies that MesoscopeHardwareState fields default to None to mark unused hardware modules."""
    state = MesoscopeHardwareState()

    assert state.cm_per_pulse is None
    assert state.maximum_brake_strength is None
    assert state.minimum_brake_strength is None
    assert state.lick_threshold is None
    assert state.valve_scale_coefficient is None
    assert state.valve_nonlinearity_exponent is None
    assert state.torque_per_adc_unit is None
    assert state.screens_initially_on is None
    assert state.recorded_mesoscope_ttl is None
    assert state.delivered_gas_puffs is None
    assert state.system_state_codes is None


def test_mesoscope_hardware_state_yaml_round_trip(tmp_path: Path) -> None:
    """Verifies that MesoscopeHardwareState round-trips through YAML with every field preserved."""
    state = MesoscopeHardwareState(
        cm_per_pulse=0.0625,
        maximum_brake_strength=10.0,
        minimum_brake_strength=0.5,
        lick_threshold=2048,
        valve_scale_coefficient=1.25,
        valve_nonlinearity_exponent=0.85,
        torque_per_adc_unit=0.005,
        screens_initially_on=True,
        recorded_mesoscope_ttl=True,
        delivered_gas_puffs=False,
        system_state_codes={"idle": 0, "running": 1, "rewarded": 2},
    )

    yaml_path = tmp_path / "hardware_state.yaml"
    state.to_yaml(file_path=yaml_path)
    loaded = MesoscopeHardwareState.from_yaml(file_path=yaml_path)

    assert loaded == state


def test_lick_training_descriptor_yaml_round_trip(tmp_path: Path) -> None:
    """Verifies that LickTrainingDescriptor round-trips through YAML with every field preserved."""
    descriptor = LickTrainingDescriptor(
        experimenter="ik",
        animal_weight_g=24.5,
        minimum_reward_delay_s=4,
        maximum_reward_delay_s=12,
        maximum_water_volume_ml=1.2,
        maximum_training_time_min=15,
        maximum_unconsumed_rewards=2,
        water_reward_size_ul=4.5,
        reward_tone_duration_ms=250,
        dispensed_water_volume_ml=0.5,
        pause_dispensed_water_volume_ml=0.05,
        experimenter_given_water_volume_ml=0.1,
        preferred_session_water_volume_ml=1.0,
        incomplete=False,
        experimenter_notes="Animal performed well; consider increasing reward delay.",
    )

    yaml_path = tmp_path / "lick_training_descriptor.yaml"
    descriptor.to_yaml(file_path=yaml_path)
    loaded = LickTrainingDescriptor.from_yaml(file_path=yaml_path)

    assert loaded == descriptor


def test_run_training_descriptor_yaml_round_trip(tmp_path: Path) -> None:
    """Verifies that RunTrainingDescriptor round-trips through YAML with every field preserved."""
    descriptor = RunTrainingDescriptor(
        experimenter="ik",
        animal_weight_g=23.7,
        final_run_speed_threshold_cm_s=2.0,
        final_run_duration_threshold_s=2.5,
        initial_run_speed_threshold_cm_s=0.5,
        initial_run_duration_threshold_s=1.0,
        increase_threshold_ml=0.05,
        run_speed_increase_step_cm_s=0.1,
        run_duration_increase_step_s=0.2,
        maximum_water_volume_ml=1.5,
        maximum_training_time_min=30,
        maximum_unconsumed_rewards=3,
        maximum_idle_time_s=0.5,
        water_reward_size_ul=5.0,
        reward_tone_duration_ms=300,
        dispensed_water_volume_ml=0.8,
        pause_dispensed_water_volume_ml=0.02,
        experimenter_given_water_volume_ml=0.0,
        preferred_session_water_volume_ml=1.5,
        incomplete=False,
        experimenter_notes="Steady progression across all guidance steps.",
    )

    yaml_path = tmp_path / "run_training_descriptor.yaml"
    descriptor.to_yaml(file_path=yaml_path)
    loaded = RunTrainingDescriptor.from_yaml(file_path=yaml_path)

    assert loaded == descriptor


def test_mesoscope_experiment_descriptor_yaml_round_trip(tmp_path: Path) -> None:
    """Verifies that MesoscopeExperimentDescriptor round-trips through YAML with every field preserved."""
    descriptor = MesoscopeExperimentDescriptor(
        experimenter="ik",
        animal_weight_g=22.0,
        maximum_unconsumed_rewards=2,
        dispensed_water_volume_ml=1.1,
        pause_dispensed_water_volume_ml=0.0,
        experimenter_given_water_volume_ml=0.05,
        preferred_session_water_volume_ml=1.5,
        incomplete=False,
        experimenter_notes="Stable imaging; no motion artifacts.",
    )

    yaml_path = tmp_path / "mesoscope_experiment_descriptor.yaml"
    descriptor.to_yaml(file_path=yaml_path)
    loaded = MesoscopeExperimentDescriptor.from_yaml(file_path=yaml_path)

    assert loaded == descriptor


def test_window_checking_descriptor_yaml_round_trip(tmp_path: Path) -> None:
    """Verifies that WindowCheckingDescriptor round-trips through YAML with every field preserved."""
    descriptor = WindowCheckingDescriptor(
        experimenter="ik",
        surgery_quality=2,
        incomplete=False,
        experimenter_notes="Window is clear; vasculature is well visible.",
    )

    yaml_path = tmp_path / "window_checking_descriptor.yaml"
    descriptor.to_yaml(file_path=yaml_path)
    loaded = WindowCheckingDescriptor.from_yaml(file_path=yaml_path)

    assert loaded == descriptor


def test_descriptor_defaults_mark_session_incomplete() -> None:
    """Verifies that every descriptor defaults to ``incomplete=True`` so unfinished sessions are obvious."""
    lick = LickTrainingDescriptor(experimenter="ik", animal_weight_g=24.0)
    run = RunTrainingDescriptor(experimenter="ik", animal_weight_g=24.0)
    experiment = MesoscopeExperimentDescriptor(experimenter="ik", animal_weight_g=24.0)
    window = WindowCheckingDescriptor(experimenter="ik")

    assert lick.incomplete is True
    assert run.incomplete is True
    assert experiment.incomplete is True
    assert window.incomplete is True
