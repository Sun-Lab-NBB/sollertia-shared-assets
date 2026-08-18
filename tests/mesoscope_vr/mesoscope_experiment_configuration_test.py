"""Contains tests for the Mesoscope-VR trial classes and the experiment configuration provided by the
``mesoscope_vr.experiment_configuration`` module.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from sollertia_shared_assets.mesoscope_vr import (
    TrialKind,
    MesoscopeGasPuffTrial,
    MesoscopeWaterRewardTrial,
    MesoscopeExperimentConfiguration,
)
from sollertia_shared_assets.configuration import (
    Cue,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
    ExperimentState,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_water_reward_trial_defaults() -> None:
    """Verifies that MesoscopeWaterRewardTrial fields default to documented values."""
    trial = MesoscopeWaterRewardTrial()
    assert trial.reward_size_ul == 5.0
    assert trial.reward_tone_duration_ms == 300
    assert trial.trial_kind is TrialKind.WATER


def test_water_reward_trial_initialization() -> None:
    """Verifies basic initialization of MesoscopeWaterRewardTrial."""
    trial = MesoscopeWaterRewardTrial(reward_size_ul=4.5, reward_tone_duration_ms=250)
    assert trial.reward_size_ul == 4.5
    assert trial.reward_tone_duration_ms == 250


def test_water_reward_trial_rejects_mismatched_trial_kind() -> None:
    """Verifies that MesoscopeWaterRewardTrial rejects a trial_kind that identifies another trial class."""
    with pytest.raises(ValueError, match=r"The trial_kind must be 'water', but got 'puff'"):
        MesoscopeWaterRewardTrial(trial_kind=TrialKind.PUFF)


def test_gas_puff_trial_defaults() -> None:
    """Verifies that MesoscopeGasPuffTrial fields default to documented values."""
    trial = MesoscopeGasPuffTrial()
    assert trial.puff_duration_ms == 100
    assert trial.trial_kind is TrialKind.PUFF


def test_gas_puff_trial_initialization() -> None:
    """Verifies basic initialization of MesoscopeGasPuffTrial."""
    trial = MesoscopeGasPuffTrial(puff_duration_ms=150)
    assert trial.puff_duration_ms == 150


def test_gas_puff_trial_rejects_mismatched_trial_kind() -> None:
    """Verifies that MesoscopeGasPuffTrial rejects a trial_kind that identifies another trial class."""
    with pytest.raises(ValueError, match=r"The trial_kind must be 'puff', but got 'water'"):
        MesoscopeGasPuffTrial(trial_kind=TrialKind.WATER)


def test_trial_field_types() -> None:
    """Verifies the data types of trial fields for both water and gas puff trials."""
    water_trial = MesoscopeWaterRewardTrial(reward_size_ul=5.0, reward_tone_duration_ms=300)
    assert isinstance(water_trial.reward_size_ul, float)
    assert isinstance(water_trial.reward_tone_duration_ms, int)

    gas_trial = MesoscopeGasPuffTrial(puff_duration_ms=100)
    assert isinstance(gas_trial.puff_duration_ms, int)


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
    assert isinstance(trial, MesoscopeWaterRewardTrial)
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

    loaded_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    assert loaded_configuration.unity_scene_name == sample_experiment_config.unity_scene_name
    assert list(loaded_configuration.trial_structures.keys()) == list(sample_experiment_config.trial_structures.keys())
    assert list(loaded_configuration.experiment_states.keys()) == list(
        sample_experiment_config.experiment_states.keys()
    )


def test_mesoscope_experiment_configuration_loads_trial_without_discriminator(tmp_path: Path) -> None:
    """Verifies that a trial stored without a trial_kind key loads as a MesoscopeWaterRewardTrial."""
    yaml_path = tmp_path / "legacy_config.yaml"
    yaml_path.write_text(
        "trial_structures:\n"
        "  legacy_trial:\n"
        "    reward_size_ul: 7.5\n"
        "    reward_tone_duration_ms: 250\n"
        "experiment_states:\n"
        "  state_1:\n"
        "    experiment_state_code: 1\n"
        "    system_state_code: 0\n"
        "    state_duration_s: 60.0\n"
        "unity_scene_name: LegacyScene\n"
    )

    loaded_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    trial = loaded_configuration.trial_structures["legacy_trial"]
    assert isinstance(trial, MesoscopeWaterRewardTrial)
    assert trial.reward_size_ul == 7.5
    assert trial.reward_tone_duration_ms == 250
    assert trial.trial_kind is TrialKind.WATER


def test_mesoscope_experiment_configuration_loads_gas_puff_trial_without_discriminator(tmp_path: Path) -> None:
    """Verifies that a gas-puff trial authored without a trial_kind key loads as a MesoscopeGasPuffTrial."""
    yaml_path = tmp_path / "authored_config.yaml"
    yaml_path.write_text(
        "trial_structures:\n"
        "  occ:\n"
        "    puff_duration_ms: 250\n"
        "experiment_states:\n"
        "  state_1:\n"
        "    experiment_state_code: 1\n"
        "    system_state_code: 0\n"
        "    state_duration_s: 60.0\n"
        "unity_scene_name: OccScene\n"
    )

    loaded_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    trial = loaded_configuration.trial_structures["occ"]
    assert isinstance(trial, MesoscopeGasPuffTrial)
    assert trial.puff_duration_ms == 250
    assert trial.trial_kind is TrialKind.PUFF


def test_restore_excluded_fields_returns_mapping_without_trial_structures(tmp_path: Path) -> None:
    """Verifies that restore_excluded_fields leaves a mapping carrying no trial_structures key untouched."""
    data = {"unity_scene_name": "Scene"}

    assert MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml") == {
        "unity_scene_name": "Scene"
    }


def test_restore_excluded_fields_leaves_non_mapping_trial_untouched(tmp_path: Path) -> None:
    """Verifies that restore_excluded_fields leaves a stored trial that is not a mapping untouched."""
    data = {"trial_structures": {"broken": None}}

    restored = MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml")

    assert restored["trial_structures"]["broken"] is None


def test_restore_excluded_fields_defaults_trial_carrying_unknown_fields_to_water(tmp_path: Path) -> None:
    """Verifies that a discriminator-less trial carrying fields from a superseded schema resolves to the water kind."""
    data = {
        "trial_structures": {
            "legacy": {
                "reward_size_ul": 5.0,
                "reward_tone_duration_ms": 300,
                "segment_name": "A",
                "trial_length_cm": 100.0,
                "trigger_type": "interaction",
            }
        }
    }

    restored = MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml")

    assert restored["trial_structures"]["legacy"]["trial_kind"] == "water"


def test_restore_excluded_fields_defaults_trial_carrying_no_unique_field_to_water(tmp_path: Path) -> None:
    """Verifies that a discriminator-less trial declaring no field unique to either class resolves to the water kind."""
    data = {"trial_structures": {"defaults": {}}}

    restored = MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml")

    assert restored["trial_structures"]["defaults"]["trial_kind"] == "water"


def test_restore_excluded_fields_rejects_trial_declaring_fields_of_both_classes(tmp_path: Path) -> None:
    """Verifies that a trial declaring fields unique to both runtime trial classes is rejected."""
    data = {"trial_structures": {"mixed": {"reward_size_ul": 5.0, "puff_duration_ms": 100}}}

    with pytest.raises(ValueError, match="fields unique to more than one"):
        MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml")


def test_restore_excluded_fields_rejects_unrecognized_discriminator(tmp_path: Path) -> None:
    """Verifies that a trial declaring a trial_kind outside the TrialKind vocabulary is rejected."""
    data = {"trial_structures": {"odd": {"reward_size_ul": 5.0, "trial_kind": "WATER"}}}

    with pytest.raises(ValueError, match="must be one of"):
        MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml")


def test_restore_excluded_fields_rejects_discriminator_contradicting_fields(tmp_path: Path) -> None:
    """Verifies that a trial whose trial_kind names a class its fields do not belong to is rejected."""
    data = {"trial_structures": {"mislabelled": {"reward_size_ul": 9.9, "trial_kind": "puff"}}}

    with pytest.raises(ValueError, match=r"field names 'puff'"):
        MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml")


def test_restore_excluded_fields_keeps_consistent_discriminator(tmp_path: Path) -> None:
    """Verifies that a trial whose trial_kind agrees with its fields is returned unchanged."""
    data = {"trial_structures": {"puff": {"puff_duration_ms": 150, "trial_kind": "puff"}}}

    restored = MesoscopeExperimentConfiguration.restore_excluded_fields(data=data, file_path=tmp_path / "config.yaml")

    assert restored["trial_structures"]["puff"] == {"puff_duration_ms": 150, "trial_kind": "puff"}


def test_mesoscope_experiment_configuration_rejects_unresolved_trial() -> None:
    """Verifies that a trial left as a mapping by the loader is rejected at construction."""
    with pytest.raises(ValueError, match="must resolve to a Mesoscope-VR runtime trial class"):
        MesoscopeExperimentConfiguration(
            trial_structures={"unresolved": {"reward_size_ul": 5.0}},  # type: ignore[dict-item]
            experiment_states={},
            unity_scene_name="Scene",
        )


def test_mesoscope_experiment_configuration_round_trips_gas_puff_trial(tmp_path: Path) -> None:
    """Verifies that a gas-puff trial survives a MesoscopeExperimentConfiguration YAML round trip."""
    configuration = MesoscopeExperimentConfiguration(
        trial_structures={"puff": MesoscopeGasPuffTrial(puff_duration_ms=150)},
        experiment_states={
            "state1": ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=60.0),
        },
        unity_scene_name="PuffScene",
    )
    yaml_path = tmp_path / "puff_config.yaml"
    configuration.to_yaml(file_path=yaml_path)

    loaded_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    trial = loaded_configuration.trial_structures["puff"]
    assert isinstance(trial, MesoscopeGasPuffTrial)
    assert trial.puff_duration_ms == 150


def test_mesoscope_experiment_configuration_round_trips_mixed_trials(tmp_path: Path) -> None:
    """Verifies that a configuration holding both trial classes restores each trial to its own class."""
    configuration = MesoscopeExperimentConfiguration(
        trial_structures={
            "reward": MesoscopeWaterRewardTrial(reward_size_ul=4.0, reward_tone_duration_ms=200),
            "puff": MesoscopeGasPuffTrial(puff_duration_ms=175),
        },
        experiment_states={
            "state1": ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=60.0),
        },
        unity_scene_name="MixedScene",
    )
    yaml_path = tmp_path / "mixed_config.yaml"
    configuration.to_yaml(file_path=yaml_path)

    loaded_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    reward_trial = loaded_configuration.trial_structures["reward"]
    puff_trial = loaded_configuration.trial_structures["puff"]
    assert isinstance(reward_trial, MesoscopeWaterRewardTrial)
    assert isinstance(puff_trial, MesoscopeGasPuffTrial)
    assert reward_trial.reward_size_ul == 4.0
    assert reward_trial.reward_tone_duration_ms == 200
    assert puff_trial.puff_duration_ms == 175


def test_mesoscope_experiment_configuration_carries_water_and_puff_trials() -> None:
    """Verifies that MesoscopeExperimentConfiguration accepts mixed WaterReward and GasPuff trials."""
    configuration = MesoscopeExperimentConfiguration(
        trial_structures={
            "reward": MesoscopeWaterRewardTrial(reward_size_ul=4.0, reward_tone_duration_ms=200),
            "puff": MesoscopeGasPuffTrial(puff_duration_ms=150),
        },
        experiment_states={
            "state1": ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=60.0),
        },
        unity_scene_name="MixedScene",
    )

    assert isinstance(configuration.trial_structures["reward"], MesoscopeWaterRewardTrial)
    assert isinstance(configuration.trial_structures["puff"], MesoscopeGasPuffTrial)
    assert configuration.trial_structures["reward"].reward_size_ul == 4.0
    assert configuration.trial_structures["puff"].puff_duration_ms == 150


def test_from_task_template_maps_interaction_trial_to_water_reward() -> None:
    """Verifies that from_task_template maps an INTERACTION trigger trial to a MesoscopeWaterRewardTrial."""
    template = _create_base_task_template()

    configuration = MesoscopeExperimentConfiguration.from_task_template(template=template, unity_scene_name="TestScene")

    assert configuration.unity_scene_name == "TestScene"
    assert len(configuration.trial_structures) == 1
    trial = configuration.trial_structures["trial1"]
    assert isinstance(trial, MesoscopeWaterRewardTrial)
    assert trial.reward_size_ul == 5.0


def test_from_task_template_maps_occupancy_trial_to_gas_puff() -> None:
    """Verifies that from_task_template maps an OCCUPANCY_DISARM trigger trial to a MesoscopeGasPuffTrial."""
    template = _create_base_task_template(
        trial_structures={
            "occ_trial": TrialStructure(
                cue_sequence=["A", "B"],
                stimulus_trigger_zone_start_cm=80.0,
                stimulus_trigger_zone_end_cm=100.0,
                stimulus_location_cm=90.0,
                show_stimulus_collision_boundary=False,
                trigger_type=TriggerType.OCCUPANCY_DISARM,
                occupancy_duration_ms=1000.0,
            ),
        }
    )

    configuration = MesoscopeExperimentConfiguration.from_task_template(
        template=template,
        unity_scene_name="OccScene",
        default_puff_duration_ms=200,
    )

    trial = configuration.trial_structures["occ_trial"]
    assert isinstance(trial, MesoscopeGasPuffTrial)
    assert trial.puff_duration_ms == 200


def test_from_task_template_seeds_water_reward_guided_states() -> None:
    """Verifies that from_task_template seeds reinforcing guidance for water-reward trials."""
    template = _create_base_task_template()

    configuration = MesoscopeExperimentConfiguration.from_task_template(
        template=template, unity_scene_name="TestScene", state_count=3
    )

    assert set(configuration.experiment_states) == {"state_1", "state_2", "state_3"}
    state_1 = configuration.experiment_states["state_1"]
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
                trigger_type=TriggerType.OCCUPANCY_DISARM,
                occupancy_duration_ms=1000.0,
            ),
        }
    )

    configuration = MesoscopeExperimentConfiguration.from_task_template(
        template=template, unity_scene_name="OccScene", state_count=2
    )

    state_1 = configuration.experiment_states["state_1"]
    assert state_1.reinforcing_initial_guided_trials == 0
    assert state_1.aversive_initial_guided_trials == 3
    assert state_1.aversive_recovery_failed_threshold == 9
    assert state_1.aversive_recovery_guided_trials == 3


def test_from_task_template_maps_supported_trigger_types() -> None:
    """Verifies from_task_template maps the trigger types Mesoscope-VR supports and rejects the rest as unmapped."""
    supported = {TriggerType.INTERACTION, TriggerType.OCCUPANCY_DISARM}

    for trigger_type in supported:
        template = _create_base_task_template(
            trial_structures={
                "trial": TrialStructure(
                    cue_sequence=["A", "B"],
                    stimulus_trigger_zone_start_cm=80.0,
                    stimulus_trigger_zone_end_cm=100.0,
                    stimulus_location_cm=90.0,
                    show_stimulus_collision_boundary=False,
                    trigger_type=trigger_type,
                    occupancy_duration_ms=1000.0,
                ),
            }
        )
        configuration = MesoscopeExperimentConfiguration.from_task_template(template=template, unity_scene_name="Scene")
        assert "trial" in configuration.trial_structures

    for trigger_type in set(TriggerType) - supported:
        template = _create_base_task_template(
            trial_structures={
                "trial": TrialStructure(
                    cue_sequence=["A", "B"],
                    stimulus_trigger_zone_start_cm=80.0,
                    stimulus_trigger_zone_end_cm=100.0,
                    stimulus_location_cm=90.0,
                    show_stimulus_collision_boundary=False,
                    trigger_type=trigger_type,
                    occupancy_duration_ms=1000.0,
                ),
            }
        )
        with pytest.raises(ValueError, match=r"not mapped to a runtime trial class"):
            MesoscopeExperimentConfiguration.from_task_template(template=template, unity_scene_name="Scene")


def test_from_task_template_rejects_non_positive_state_count() -> None:
    """Verifies that from_task_template rejects a state_count below one."""
    template = _create_base_task_template()

    with pytest.raises(ValueError, match=r"The state_count must be at least 1"):
        MesoscopeExperimentConfiguration.from_task_template(
            template=template, unity_scene_name="TestScene", state_count=0
        )


def test_from_task_template_raises_on_unmapped_trigger() -> None:
    """Verifies that from_task_template raises when a trial uses a trigger type with no runtime-trial mapping."""
    unmapped_template = SimpleNamespace(trial_structures={"weird": SimpleNamespace(trigger_type="unmapped")})

    with pytest.raises(ValueError, match=r"not mapped to a runtime trial class"):
        MesoscopeExperimentConfiguration.from_task_template(template=unmapped_template, unity_scene_name="Scene")


def _create_base_task_template(
    cues: list[Cue] | None = None,
    trial_structures: dict[str, TrialStructure] | None = None,
) -> TaskTemplate:
    """Builds a TaskTemplate populated with defaults suitable for tests."""
    if cues is None:
        cues = [
            Cue(name="A", code=1, length_cm=50.0, texture="Cue.png"),
            Cue(name="B", code=2, length_cm=50.0, texture="Cue.png"),
        ]
    if trial_structures is None:
        trial_structures = {
            "trial1": TrialStructure(
                cue_sequence=["A", "B"],
                stimulus_trigger_zone_start_cm=80.0,
                stimulus_trigger_zone_end_cm=100.0,
                stimulus_location_cm=90.0,
                show_stimulus_collision_boundary=False,
                trigger_type=TriggerType.INTERACTION,
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
