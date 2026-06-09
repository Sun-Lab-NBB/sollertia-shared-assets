"""Contains tests for the Mesoscope-VR experiment configuration provided by the
``configuration.mesoscope_configuration`` module.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from sollertia_shared_assets.configuration import (
    Cue,
    TriggerType,
    GasPuffTrial,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
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


def test_from_task_template_maps_lick_trial_to_water_reward() -> None:
    """Verifies that from_task_template maps a LICK trigger trial to a WaterRewardTrial."""
    template = _create_base_task_template()

    config = MesoscopeExperimentConfiguration.from_task_template(template=template, unity_scene_name="TestScene")

    assert config.unity_scene_name == "TestScene"
    assert len(config.trial_structures) == 1
    trial = config.trial_structures["trial1"]
    assert isinstance(trial, WaterRewardTrial)
    assert trial.reward_size_ul == 5.0


def test_from_task_template_maps_occupancy_trial_to_gas_puff() -> None:
    """Verifies that from_task_template maps an OCCUPANCY trigger trial to a GasPuffTrial."""
    template = _create_base_task_template(
        trial_structures={
            "occ_trial": TrialStructure(
                cue_sequence=["A", "B"],
                stimulus_trigger_zone_start_cm=80.0,
                stimulus_trigger_zone_end_cm=100.0,
                stimulus_location_cm=90.0,
                show_stimulus_collision_boundary=False,
                trigger_type=TriggerType.OCCUPANCY,
            ),
        }
    )

    config = MesoscopeExperimentConfiguration.from_task_template(
        template=template,
        unity_scene_name="OccScene",
        default_puff_duration_ms=200,
        default_occupancy_duration_ms=2000,
    )

    trial = config.trial_structures["occ_trial"]
    assert isinstance(trial, GasPuffTrial)
    assert trial.puff_duration_ms == 200
    assert trial.occupancy_duration_ms == 2000


def test_from_task_template_seeds_water_reward_guided_states() -> None:
    """Verifies that from_task_template seeds reinforcing guidance for water-reward trials."""
    template = _create_base_task_template()

    config = MesoscopeExperimentConfiguration.from_task_template(
        template=template, unity_scene_name="TestScene", state_count=3
    )

    assert set(config.experiment_states) == {"state_1", "state_2", "state_3"}
    state_1 = config.experiment_states["state_1"]
    assert state_1.experiment_state_code == 1
    assert state_1.state_duration_s == 60
    assert state_1.supports_trials is True
    assert state_1.reinforcing_initial_guided_trials == 3
    assert state_1.aversive_initial_guided_trials == 0


def test_from_task_template_seeds_gas_puff_guided_states() -> None:
    """Verifies that from_task_template seeds aversive guidance for gas-puff trials."""
    template = _create_base_task_template(
        trial_structures={
            "occ_trial": TrialStructure(
                cue_sequence=["A", "B"],
                stimulus_trigger_zone_start_cm=80.0,
                stimulus_trigger_zone_end_cm=100.0,
                stimulus_location_cm=90.0,
                show_stimulus_collision_boundary=False,
                trigger_type=TriggerType.OCCUPANCY,
            ),
        }
    )

    config = MesoscopeExperimentConfiguration.from_task_template(
        template=template, unity_scene_name="OccScene", state_count=2
    )

    state_1 = config.experiment_states["state_1"]
    assert state_1.reinforcing_initial_guided_trials == 0
    assert state_1.aversive_initial_guided_trials == 3
    assert state_1.aversive_recovery_failed_threshold == 9
    assert state_1.aversive_recovery_guided_trials == 3


def test_from_task_template_maps_every_trigger_type() -> None:
    """Verifies that from_task_template produces a runtime trial for every TriggerType a template can carry."""
    for trigger_type in TriggerType:
        template = _create_base_task_template(
            trial_structures={
                "trial": TrialStructure(
                    cue_sequence=["A", "B"],
                    stimulus_trigger_zone_start_cm=80.0,
                    stimulus_trigger_zone_end_cm=100.0,
                    stimulus_location_cm=90.0,
                    show_stimulus_collision_boundary=False,
                    trigger_type=trigger_type,
                ),
            }
        )

        config = MesoscopeExperimentConfiguration.from_task_template(template=template, unity_scene_name="Scene")

        assert "trial" in config.trial_structures


def test_from_task_template_raises_on_unmapped_trigger() -> None:
    """Verifies that from_task_template raises when a trial uses a trigger type with no runtime-trial mapping."""
    unmapped_template = SimpleNamespace(trial_structures={"weird": SimpleNamespace(trigger_type="unmapped")})

    with pytest.raises(ValueError, match=r"not mapped to a runtime trial class"):
        # noinspection PyTypeChecker
        MesoscopeExperimentConfiguration.from_task_template(template=unmapped_template, unity_scene_name="Scene")


def _create_base_task_template(
    cues: list[Cue] | None = None,
    trial_structures: dict[str, TrialStructure] | None = None,
) -> TaskTemplate:
    """Builds a TaskTemplate populated with defaults suitable for tests."""
    if cues is None:
        cues = [
            Cue(name="A", code=1, length_cm=50.0),
            Cue(name="B", code=2, length_cm=50.0),
        ]
    if trial_structures is None:
        trial_structures = {
            "trial1": TrialStructure(
                cue_sequence=["A", "B"],
                stimulus_trigger_zone_start_cm=80.0,
                stimulus_trigger_zone_end_cm=100.0,
                stimulus_location_cm=90.0,
                show_stimulus_collision_boundary=False,
                trigger_type=TriggerType.LICK,
            ),
        }
    return TaskTemplate(
        cues=cues,
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
            cue_offset_cm=0.0,
        ),
        trial_structures=trial_structures,
    )
