"""Contains tests for the Mesoscope-VR experiment configuration provided by the
``configuration.mesoscope_configuration`` module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from sollertia_shared_assets.configuration import (
    Cue,
    Segment,
    VREnvironment,
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
    assert len(sample_experiment_config.cues) == 3
    assert len(sample_experiment_config.segments) == 1
    assert sample_experiment_config.cue_offset_cm == 10.0
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
    assert trial.cue_sequence == [1, 2, 3]


def test_mesoscope_experiment_configuration_yaml_serialization(
    tmp_path: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies that MesoscopeExperimentConfiguration can be saved as YAML."""
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    assert yaml_path.exists()
    content = yaml_path.read_text()

    assert "cues:" in content
    assert "unity_scene_name:" in content
    assert "TestScene" in content


def test_mesoscope_experiment_configuration_yaml_deserialization(
    tmp_path: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies that MesoscopeExperimentConfiguration round-trips through YAML."""
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    loaded_config = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    assert len(loaded_config.cues) == len(sample_experiment_config.cues)
    assert loaded_config.unity_scene_name == sample_experiment_config.unity_scene_name
    assert loaded_config.cue_offset_cm == sample_experiment_config.cue_offset_cm


def test_mesoscope_experiment_configuration_derives_trial_fields() -> None:
    """Verifies that trial cue_sequence and trial_length_cm are derived from the referenced segment."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
    )

    # Defines cues that sum to 175 cm for Segment_abc (50 + 75 + 50).
    cues = [
        Cue(name="A", code=1, length_cm=50.0, texture="Cue 016 - 4x1.png"),
        Cue(name="B", code=2, length_cm=75.0, texture="Cue 001 - 4x1.png"),
        Cue(name="C", code=3, length_cm=50.0, texture="Cue 008 - 2x1 repeat.png"),
    ]
    segments = [Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None)]

    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=150.0,
        stimulus_trigger_zone_end_cm=175.0,
        stimulus_location_cm=160.0,
        show_stimulus_collision_boundary=False,
    )

    config = MesoscopeExperimentConfiguration(
        cues=cues,
        segments=segments,
        trial_structures={"trial1": trial},
        experiment_states={"state1": state},
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
        ),
        unity_scene_name="TestScene",
        cue_offset_cm=10.0,
    )

    assert config.trial_structures["trial1"].cue_sequence == [1, 2, 3]
    assert config.trial_structures["trial1"].trial_length_cm == 175.0


def test_mesoscope_experiment_configuration_invalid_segment_reference_raises_error() -> None:
    """Verifies that a trial referencing an unknown segment raises ValueError."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
    )

    cues = [
        Cue(name="A", code=1, length_cm=50.0, texture="Cue 016 - 4x1.png"),
        Cue(name="B", code=2, length_cm=75.0, texture="Cue 001 - 4x1.png"),
    ]
    segments = [Segment(name="Segment_ab", cue_sequence=["A", "B"], transition_probabilities=None)]

    trial = WaterRewardTrial(
        segment_name="NonexistentSegment",
        stimulus_trigger_zone_start_cm=100.0,
        stimulus_trigger_zone_end_cm=125.0,
        stimulus_location_cm=110.0,
        show_stimulus_collision_boundary=False,
    )

    with pytest.raises(ValueError, match=r"references unknown segment.*NonexistentSegment"):
        MesoscopeExperimentConfiguration(
            cues=cues,
            segments=segments,
            trial_structures={"trial1": trial},
            experiment_states={"state1": state},
            vr_environment=VREnvironment(
                corridor_spacing_cm=100.0,
                segments_per_corridor=3,
                padding_prefab_name="Padding",
                cm_per_unity_unit=10.0,
            ),
            unity_scene_name="TestScene",
        )


def test_mesoscope_experiment_configuration_invalid_cue_in_segment_raises_error() -> None:
    """Verifies that a segment referencing an unknown cue raises ValueError."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
    )

    cues = [
        Cue(name="A", code=1, length_cm=50.0, texture="Cue 016 - 4x1.png"),
        Cue(name="B", code=2, length_cm=75.0, texture="Cue 001 - 4x1.png"),
    ]
    # Segment references cue "C", which is not defined in the cue list.
    segments = [Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None)]

    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=100.0,
        stimulus_trigger_zone_end_cm=125.0,
        stimulus_location_cm=110.0,
        show_stimulus_collision_boundary=False,
    )

    with pytest.raises(ValueError, match=r"references unknown cue.*C"):
        MesoscopeExperimentConfiguration(
            cues=cues,
            segments=segments,
            trial_structures={"trial1": trial},
            experiment_states={"state1": state},
            vr_environment=VREnvironment(
                corridor_spacing_cm=100.0,
                segments_per_corridor=3,
                padding_prefab_name="Padding",
                cm_per_unity_unit=10.0,
            ),
            unity_scene_name="TestScene",
        )


def test_mesoscope_experiment_configuration_duplicate_cue_codes_raises_error() -> None:
    """Verifies that duplicate cue codes in MesoscopeExperimentConfiguration raise ValueError."""
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=1, length_cm=50.0),
    ]
    segments = [Segment(name="Seg", cue_sequence=["A", "B"], transition_probabilities=None)]
    trial = WaterRewardTrial(
        segment_name="Seg",
        stimulus_trigger_zone_start_cm=80.0,
        stimulus_trigger_zone_end_cm=100.0,
        stimulus_location_cm=90.0,
        show_stimulus_collision_boundary=False,
    )
    state = ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=60.0)
    with pytest.raises(ValueError, match=r"duplicate codes"):
        MesoscopeExperimentConfiguration(
            cues=cues,
            segments=segments,
            trial_structures={"trial1": trial},
            experiment_states={"state1": state},
            vr_environment=VREnvironment(
                corridor_spacing_cm=100.0,
                segments_per_corridor=3,
                padding_prefab_name="P",
                cm_per_unity_unit=10.0,
            ),
            unity_scene_name="Test",
        )


def test_mesoscope_experiment_configuration_duplicate_cue_names_raises_error() -> None:
    """Verifies that duplicate cue names in MesoscopeExperimentConfiguration raise ValueError."""
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="A", code=2, length_cm=50.0),
    ]
    segments = [Segment(name="Seg", cue_sequence=["A"], transition_probabilities=None)]
    trial = WaterRewardTrial(
        segment_name="Seg",
        stimulus_trigger_zone_start_cm=30.0,
        stimulus_trigger_zone_end_cm=50.0,
        stimulus_location_cm=40.0,
        show_stimulus_collision_boundary=False,
    )
    state = ExperimentState(experiment_state_code=1, system_state_code=0, state_duration_s=60.0)
    with pytest.raises(ValueError, match=r"duplicate names"):
        MesoscopeExperimentConfiguration(
            cues=cues,
            segments=segments,
            trial_structures={"trial1": trial},
            experiment_states={"state1": state},
            vr_environment=VREnvironment(
                corridor_spacing_cm=100.0,
                segments_per_corridor=3,
                padding_prefab_name="P",
                cm_per_unity_unit=10.0,
            ),
            unity_scene_name="Test",
        )
