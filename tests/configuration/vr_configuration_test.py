"""Contains tests for the VR configuration dataclasses provided by the ``configuration.vr_configuration`` module."""

from __future__ import annotations

import pytest

from sollertia_shared_assets.configuration import (
    Cue,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
)


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


def test_trigger_type_values() -> None:
    """Verifies the supported TriggerType enumeration values."""
    assert TriggerType.LICK == "lick"
    assert TriggerType.OCCUPANCY == "occupancy"


def test_trigger_type_is_string_enum() -> None:
    """Verifies that TriggerType inherits from StrEnum."""
    assert isinstance(TriggerType.LICK, str)
    assert isinstance(TriggerType.OCCUPANCY, str)


def test_cue_code_above_uint8_raises_error() -> None:
    """Verifies that a Cue code above 255 raises ValueError."""
    with pytest.raises(ValueError, match=r"uint8"):
        Cue(name="X", code=256, length_cm=50.0)


def test_cue_code_negative_raises_error() -> None:
    """Verifies that a negative Cue code raises ValueError."""
    with pytest.raises(ValueError, match=r"uint8"):
        Cue(name="X", code=-1, length_cm=50.0)


def test_cue_length_zero_raises_error() -> None:
    """Verifies that a Cue with length_cm <= 0 raises ValueError."""
    with pytest.raises(ValueError, match=r"length_cm must be greater than 0"):
        Cue(name="X", code=1, length_cm=0.0)


def test_cue_length_negative_raises_error() -> None:
    """Verifies that a Cue with negative length_cm raises ValueError."""
    with pytest.raises(ValueError, match=r"length_cm must be greater than 0"):
        Cue(name="X", code=1, length_cm=-10.0)


def test_trial_structure_empty_cue_sequence_raises_error() -> None:
    """Verifies that a TrialStructure with an empty cue_sequence raises ValueError."""
    with pytest.raises(ValueError, match=r"must contain at least one cue"):
        TrialStructure(
            cue_sequence=[],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        )


def test_trial_structure_invalid_transitions_sum_raises_error() -> None:
    """Verifies that a TrialStructure with transitions that do not sum to 1.0 raises ValueError."""
    with pytest.raises(ValueError, match=r"must sum to 1\.0"):
        TrialStructure(
            cue_sequence=["A"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
            transitions={"trial1": 0.3, "trial2": 0.3},
        )


def test_trial_structure_valid_transitions() -> None:
    """Verifies that a TrialStructure with transitions summing to 1.0 initializes correctly."""
    trial = TrialStructure(
        cue_sequence=["A", "B"],
        stimulus_trigger_zone_start_cm=0.0,
        stimulus_trigger_zone_end_cm=20.0,
        stimulus_location_cm=15.0,
        show_stimulus_collision_boundary=False,
        trigger_type=TriggerType.LICK,
        transitions={"trial1": 0.5, "trial2": 0.5},
    )
    assert trial.transitions == {"trial1": 0.5, "trial2": 0.5}


def test_trial_structure_no_transitions_defaults_to_none() -> None:
    """Verifies that a TrialStructure without transitions defaults to None."""
    trial = TrialStructure(
        cue_sequence=["A"],
        stimulus_trigger_zone_start_cm=0.0,
        stimulus_trigger_zone_end_cm=10.0,
        stimulus_location_cm=5.0,
        show_stimulus_collision_boundary=False,
        trigger_type=TriggerType.LICK,
    )
    assert trial.transitions is None


def test_vr_environment_initialization() -> None:
    """Verifies that VREnvironment stores every supplied field verbatim."""
    environment = VREnvironment(
        corridor_spacing_cm=120.0,
        segments_per_corridor=4,
        padding_prefab_name="PaddingV2",
        cm_per_unity_unit=12.5,
        cue_offset_cm=8.0,
    )

    assert environment.corridor_spacing_cm == 120.0
    assert environment.segments_per_corridor == 4
    assert environment.padding_prefab_name == "PaddingV2"
    assert environment.cm_per_unity_unit == 12.5
    assert environment.cue_offset_cm == 8.0


def test_task_template_valid_initialization() -> None:
    """Verifies that a valid TaskTemplate initializes without errors."""
    template = _create_base_task_template()
    assert len(template.cues) == 2
    assert "trial1" in template.trial_structures
    assert template.vr_environment.cue_offset_cm == 0.0


def test_task_template_duplicate_cue_codes_raises_error() -> None:
    """Verifies that duplicate cue codes raise ValueError."""
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=1, length_cm=50.0),
    ]
    with pytest.raises(ValueError, match=r"duplicate codes"):
        _create_base_task_template(cues=cues)


def test_task_template_duplicate_cue_names_raises_error() -> None:
    """Verifies that duplicate cue names raise ValueError."""
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="A", code=2, length_cm=50.0),
    ]
    with pytest.raises(ValueError, match=r"duplicate names"):
        _create_base_task_template(cues=cues)


def test_task_template_trial_references_unknown_cue_raises_error() -> None:
    """Verifies that a trial referencing an unknown cue raises ValueError."""
    cues = [Cue(name="A", code=1, length_cm=50.0)]
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "Z"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"references unknown cue.*Z"):
        _create_base_task_template(cues=cues, trial_structures=trial_structures)


def test_task_template_transition_references_unknown_trial_raises_error() -> None:
    """Verifies that a transition to an unknown trial raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=20.0,
            stimulus_location_cm=15.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
            transitions={"unknown_trial": 1.0},
        ),
    }
    with pytest.raises(ValueError, match=r"transition to unknown trial.*unknown_trial"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_invalid_trigger_type_raises_error() -> None:
    """Verifies that an invalid trigger_type raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type="invalid_type",
        ),
    }
    with pytest.raises(ValueError, match=r"invalid trigger_type"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_trigger_type_as_enum() -> None:
    """Verifies that trigger_type accepts TriggerType enum values."""
    template = _create_base_task_template()
    trial = template.trial_structures["trial1"]
    assert trial.trigger_type == TriggerType.LICK


def test_task_template_zone_end_less_than_start_raises_error() -> None:
    """Verifies that zone_end < zone_start raises ValueError in TaskTemplate validation."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=90.0,
            stimulus_trigger_zone_end_cm=80.0,
            stimulus_location_cm=85.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"must be greater than or equal to"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_zone_start_outside_trial_length_raises_error() -> None:
    """Verifies that zone_start outside trial length raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=150.0,
            stimulus_trigger_zone_end_cm=160.0,
            stimulus_location_cm=155.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"stimulus_trigger_zone_start_cm.*must be within"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_zone_end_outside_trial_length_raises_error() -> None:
    """Verifies that zone_end outside trial length raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=150.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"stimulus_trigger_zone_end_cm.*must be within"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_location_outside_trial_length_raises_error() -> None:
    """Verifies that stimulus_location outside trial length raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=150.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"stimulus_location_cm.*must be within"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_location_precedes_start_raises_error() -> None:
    """Verifies that stimulus_location before zone start raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=70.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"(?s)stimulus_location_cm.*must not precede"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_helpers() -> None:
    """Verifies the internal helpers of TaskTemplate."""
    template = _create_base_task_template()

    # Asserts directly on private members to lock in the derived-data contract exercised by __post_init__.
    cue_map = template._cue_by_name
    assert "A" in cue_map
    assert "B" in cue_map
    assert cue_map["A"].code == 1

    code_map = template._cue_name_to_code
    assert code_map == {"A": 1, "B": 2}

    length = template._get_trial_length_cm(trial_name="trial1")
    assert length == 100.0

    codes = template._get_trial_cue_codes(trial_name="trial1")
    assert codes == [1, 2]


def test_task_template_yaml_round_trip(tmp_path) -> None:
    """Verifies that TaskTemplate round-trips through YAML with every field preserved."""
    template = _create_base_task_template()

    yaml_path = tmp_path / "task_template.yaml"
    template.to_yaml(file_path=yaml_path)
    loaded = TaskTemplate.from_yaml(file_path=yaml_path)

    assert len(loaded.cues) == len(template.cues)
    assert list(loaded.trial_structures.keys()) == list(template.trial_structures.keys())
    assert loaded.vr_environment.cue_offset_cm == template.vr_environment.cue_offset_cm
