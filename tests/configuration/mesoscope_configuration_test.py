"""Contains tests for the Mesoscope-VR experiment configuration provided by the
``configuration.mesoscope_configuration`` module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sollertia_shared_assets.configuration import (
    GasPuffTrial,
    ExperimentState,
    WaterRewardTrial,
    MesoscopeExperimentConfiguration,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_mesoscope_experiment_configuration_initialization(
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies basic initialization of MesoscopeExperimentConfiguration."""
    assert sample_experiment_config.unity_scene_name == "TestScene"
    assert "state1" in sample_experiment_config.experiment_states
    assert "trial1" in sample_experiment_config.trial_structures


def test_mesoscope_experiment_configuration_nested_structures(
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies nested dataclass structures in MesoscopeExperimentConfiguration."""
    state = sample_experiment_config.experiment_states["state1"]
    assert isinstance(state, ExperimentState)
    assert state.experiment_state_code == 1

    trial = sample_experiment_config.trial_structures["trial1"]
    assert isinstance(trial, WaterRewardTrial)
    assert trial.reward_size_ul == 5.0


def test_mesoscope_experiment_configuration_yaml_serialization(
    tmp_path: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies that MesoscopeExperimentConfiguration can be saved as YAML."""
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    assert yaml_path.exists()
    content = yaml_path.read_text()

    assert "unity_scene_name:" in content
    assert "TestScene" in content
    assert "trial_structures:" in content


def test_mesoscope_experiment_configuration_yaml_deserialization(
    tmp_path: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies that MesoscopeExperimentConfiguration round-trips through YAML."""
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    loaded_config = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    assert loaded_config.unity_scene_name == sample_experiment_config.unity_scene_name
    assert list(loaded_config.trial_structures.keys()) == list(sample_experiment_config.trial_structures.keys())
    assert list(loaded_config.experiment_states.keys()) == list(sample_experiment_config.experiment_states.keys())


def test_mesoscope_experiment_configuration_carries_water_and_puff_trials() -> None:
    """Verifies that MesoscopeExperimentConfiguration accepts mixed WaterReward and GasPuff trials."""
    config = MesoscopeExperimentConfiguration(
        trial_structures={
            "reward": WaterRewardTrial(reward_size_ul=4.0, reward_tone_duration_ms=200),
            "puff": GasPuffTrial(puff_duration_ms=150, occupancy_duration_ms=2000),
        },
        experiment_states={
            "state1": ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=60.0),
        },
        unity_scene_name="MixedScene",
    )

    assert isinstance(config.trial_structures["reward"], WaterRewardTrial)
    assert isinstance(config.trial_structures["puff"], GasPuffTrial)
    assert config.trial_structures["reward"].reward_size_ul == 4.0
    assert config.trial_structures["puff"].puff_duration_ms == 150
