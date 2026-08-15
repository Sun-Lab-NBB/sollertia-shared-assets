"""Contains tests for the VR configuration dataclasses provided by the ``configuration.vr_configuration`` module."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import pytest

from sollertia_shared_assets.configuration import (
    Cue,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
)

if TYPE_CHECKING:
    from pathlib import Path


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


def _create_vr_environment(
    corridor_spacing_cm: float = 100.0,
    segments_per_corridor: float = 3,
    cm_per_unity_unit: float = 10.0,
    cue_offset_cm: float = 0.0,
) -> VREnvironment:
    """Builds a VREnvironment with valid defaults so a test overrides only the field it exercises."""
    return VREnvironment(
        corridor_spacing_cm=corridor_spacing_cm,
        segments_per_corridor=segments_per_corridor,
        padding_prefab_name="Padding",
        cm_per_unity_unit=cm_per_unity_unit,
        cue_offset_cm=cue_offset_cm,
    )


def test_trigger_type_values() -> None:
    """Verifies the supported TriggerType enumeration values."""
    assert TriggerType.INTERACTION == "interaction"
    assert TriggerType.COLLISION == "collision"
    assert TriggerType.OCCUPANCY_DISARM == "occupancy_disarm"
    assert TriggerType.OCCUPANCY_ARM == "occupancy_arm"
    assert TriggerType.OCCUPANCY_TRIGGER == "occupancy_trigger"


def test_trigger_type_is_string_enum() -> None:
    """Verifies that TriggerType inherits from StrEnum."""
    assert isinstance(TriggerType.INTERACTION, str)
    assert isinstance(TriggerType.COLLISION, str)
    assert isinstance(TriggerType.OCCUPANCY_DISARM, str)
    assert isinstance(TriggerType.OCCUPANCY_ARM, str)
    assert isinstance(TriggerType.OCCUPANCY_TRIGGER, str)


def test_cue_empty_name_raises_error() -> None:
    """Verifies that a Cue with an empty name raises ValueError."""
    with pytest.raises(ValueError, match=r"name must be a non-empty string"):
        Cue(name="", code=1, length_cm=50.0)


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
    with pytest.raises(ValueError, match=r"length_cm must be a positive, finite value"):
        Cue(name="X", code=1, length_cm=0.0)


def test_cue_length_negative_raises_error() -> None:
    """Verifies that a Cue with negative length_cm raises ValueError."""
    with pytest.raises(ValueError, match=r"length_cm must be a positive, finite value"):
        Cue(name="X", code=1, length_cm=-10.0)


def test_cue_nan_length_raises_error() -> None:
    """Verifies that a Cue with a NaN length_cm raises ValueError."""
    with pytest.raises(ValueError, match=r"length_cm must be a positive, finite value"):
        Cue(name="X", code=1, length_cm=float("nan"))


def test_cue_infinite_length_raises_error() -> None:
    """Verifies that a Cue with an infinite length_cm raises ValueError."""
    with pytest.raises(ValueError, match=r"length_cm must be a positive, finite value"):
        Cue(name="X", code=1, length_cm=float("inf"))


def test_cue_name_with_space_raises_error() -> None:
    """Verifies that a Cue name carrying a space raises ValueError."""
    with pytest.raises(ValueError, match=r"name must contain only ASCII letters, digits, and underscores"):
        Cue(name="A B", code=1, length_cm=50.0)


def test_cue_name_with_hyphen_raises_error() -> None:
    """Verifies that a Cue name carrying a hyphen raises ValueError."""
    with pytest.raises(ValueError, match=r"name must contain only ASCII letters, digits, and underscores"):
        Cue(name="A-B", code=1, length_cm=50.0)


def test_cue_name_with_underscores_and_digits() -> None:
    """Verifies that a Cue name of ASCII letters, digits, and underscores is accepted."""
    cue = Cue(name="Cue_01", code=1, length_cm=50.0)

    assert cue.name == "Cue_01"


def test_trial_structure_empty_cue_sequence_raises_error() -> None:
    """Verifies that a TrialStructure with an empty cue_sequence raises ValueError."""
    with pytest.raises(ValueError, match=r"must contain at least one cue"):
        TrialStructure(
            cue_sequence=[],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
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
            trigger_type=TriggerType.INTERACTION,
            transitions={"trial1": 0.3, "trial2": 0.3},
        )


def test_trial_structure_negative_transition_probability_raises_error() -> None:
    """Verifies that a negative transition probability raises ValueError even when the set sums to 1.0."""
    with pytest.raises(ValueError, match=r"transition probability for 'trial1'"):
        TrialStructure(
            cue_sequence=["A"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
            transitions={"trial1": -0.5, "trial2": 1.5},
        )


def test_trial_structure_non_finite_transition_probability_raises_error() -> None:
    """Verifies that a non-finite transition probability raises ValueError."""
    with pytest.raises(ValueError, match=r"transition probability for 'trial1'"):
        TrialStructure(
            cue_sequence=["A"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
            transitions={"trial1": math.nan},
        )


def test_trial_structure_valid_transitions() -> None:
    """Verifies that a TrialStructure with transitions summing to 1.0 initializes correctly."""
    trial = TrialStructure(
        cue_sequence=["A", "B"],
        stimulus_trigger_zone_start_cm=0.0,
        stimulus_trigger_zone_end_cm=20.0,
        stimulus_location_cm=15.0,
        show_stimulus_collision_boundary=False,
        trigger_type=TriggerType.INTERACTION,
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
        trigger_type=TriggerType.INTERACTION,
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


def test_vr_environment_zero_segments_per_corridor_raises_error() -> None:
    """Verifies that a VREnvironment with fewer than one segment per corridor raises ValueError."""
    with pytest.raises(ValueError, match=r"segments_per_corridor must be an integer of at least 1"):
        _create_vr_environment(segments_per_corridor=0)


def test_vr_environment_nan_segments_per_corridor_raises_error() -> None:
    """Verifies that a VREnvironment with a NaN segments_per_corridor raises ValueError."""
    with pytest.raises(ValueError, match=r"segments_per_corridor must be an integer of at least 1"):
        _create_vr_environment(segments_per_corridor=math.nan)


def test_vr_environment_infinite_segments_per_corridor_raises_error() -> None:
    """Verifies that a VREnvironment with an infinite segments_per_corridor raises ValueError."""
    with pytest.raises(ValueError, match=r"segments_per_corridor must be an integer of at least 1"):
        _create_vr_environment(segments_per_corridor=math.inf)


def test_vr_environment_fractional_segments_per_corridor_raises_error() -> None:
    """Verifies that a VREnvironment with a non-integral segments_per_corridor raises ValueError."""
    with pytest.raises(ValueError, match=r"segments_per_corridor must be an integer of at least 1"):
        _create_vr_environment(segments_per_corridor=1.5)


def test_vr_environment_zero_cm_per_unity_unit_raises_error() -> None:
    """Verifies that a VREnvironment with a non-positive cm_per_unity_unit raises ValueError."""
    with pytest.raises(ValueError, match=r"cm_per_unity_unit must be a positive, finite value"):
        _create_vr_environment(cm_per_unity_unit=0.0)


def test_vr_environment_non_finite_cm_per_unity_unit_raises_error() -> None:
    """Verifies that a VREnvironment with a non-finite cm_per_unity_unit raises ValueError."""
    with pytest.raises(ValueError, match=r"cm_per_unity_unit must be a positive, finite value"):
        _create_vr_environment(cm_per_unity_unit=math.inf)


def test_vr_environment_negative_corridor_spacing_raises_error() -> None:
    """Verifies that a VREnvironment with a non-positive corridor_spacing_cm raises ValueError."""
    with pytest.raises(ValueError, match=r"corridor_spacing_cm must be a positive, finite value"):
        _create_vr_environment(corridor_spacing_cm=-20.0)


def test_vr_environment_non_finite_corridor_spacing_raises_error() -> None:
    """Verifies that a VREnvironment with a non-finite corridor_spacing_cm raises ValueError."""
    with pytest.raises(ValueError, match=r"corridor_spacing_cm must be a positive, finite value"):
        _create_vr_environment(corridor_spacing_cm=math.nan)


def test_vr_environment_non_finite_cue_offset_raises_error() -> None:
    """Verifies that a VREnvironment with a non-finite cue_offset_cm raises ValueError."""
    with pytest.raises(ValueError, match=r"cue_offset_cm must be a finite value"):
        _create_vr_environment(cue_offset_cm=math.nan)


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
            trigger_type=TriggerType.INTERACTION,
        ),
    }
    with pytest.raises(ValueError, match=r"references unknown cue.*Z"):
        _create_base_task_template(cues=cues, trial_structures=trial_structures)


def test_task_template_invalid_trial_name_raises_error() -> None:
    """Verifies that a trial name with characters outside [A-Za-z0-9_] raises ValueError.

    Trial names are embedded verbatim in Unity-side ``<template>_<trial>.prefab`` segment filenames,
    so any character that is unsafe in a filesystem path must be rejected at template load.
    """
    trial_structures = {
        "bad name!": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
        ),
    }
    with pytest.raises(ValueError, match=r"Trial name.*invalid"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_valid_trial_name_with_underscores_and_digits() -> None:
    """Verifies that trial names containing letters, digits, and underscores are accepted."""
    trial_structures = {
        "ABC_123": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
        ),
    }
    template = _create_base_task_template(trial_structures=trial_structures)
    assert "ABC_123" in template.trial_structures


def test_task_template_transition_references_unknown_trial_raises_error() -> None:
    """Verifies that a transition to an unknown trial raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=20.0,
            stimulus_location_cm=15.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
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
    assert trial.trigger_type == TriggerType.INTERACTION


def test_task_template_zone_end_less_than_start_raises_error() -> None:
    """Verifies that zone_end < zone_start raises ValueError in TaskTemplate validation."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=90.0,
            stimulus_trigger_zone_end_cm=80.0,
            stimulus_location_cm=85.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
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
            trigger_type=TriggerType.INTERACTION,
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
            trigger_type=TriggerType.INTERACTION,
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
            trigger_type=TriggerType.INTERACTION,
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
            trigger_type=TriggerType.INTERACTION,
        ),
    }
    with pytest.raises(ValueError, match=r"(?s)stimulus_location_cm.*must not precede"):
        _create_base_task_template(trial_structures=trial_structures)


def test_trial_structure_non_positive_occupancy_duration_raises_error() -> None:
    """Verifies that a TrialStructure with a non-positive occupancy_duration_ms raises ValueError."""
    with pytest.raises(ValueError, match=r"occupancy_duration_ms must be a positive, finite value"):
        TrialStructure(
            cue_sequence=["A"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.OCCUPANCY_DISARM,
            occupancy_duration_ms=0.0,
        )


def test_trial_structure_nan_occupancy_duration_raises_error() -> None:
    """Verifies that a TrialStructure with a NaN occupancy_duration_ms raises ValueError."""
    with pytest.raises(ValueError, match=r"occupancy_duration_ms must be a positive, finite value"):
        TrialStructure(
            cue_sequence=["A"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.OCCUPANCY_DISARM,
            occupancy_duration_ms=float("nan"),
        )


def test_trial_structure_occupancy_mode_without_duration_raises_error() -> None:
    """Verifies that an occupancy-mode TrialStructure with an unset occupancy_duration_ms raises ValueError."""
    with pytest.raises(ValueError, match=r"is an occupancy mode"):
        TrialStructure(
            cue_sequence=["A"],
            stimulus_trigger_zone_start_cm=0.0,
            stimulus_trigger_zone_end_cm=10.0,
            stimulus_location_cm=5.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.OCCUPANCY_ARM,
        )


def test_task_template_duplicate_cue_sequence_raises_error() -> None:
    """Verifies that two trials sharing an identical cue sequence raise ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
        ),
        "trial2": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.INTERACTION,
        ),
    }
    with pytest.raises(ValueError, match=r"share an identical cue sequence"):
        _create_base_task_template(trial_structures=trial_structures)


def test_collision_trial_skips_trigger_zone_validation() -> None:
    """Verifies that a collision trial ignores trigger-zone bounds but still validates the boundary location."""
    # Reversed zone bounds (end < start) are accepted because collision validates only the boundary location.
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=100.0,
            stimulus_trigger_zone_end_cm=80.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.COLLISION,
        ),
    }
    template = _create_base_task_template(trial_structures=trial_structures)
    assert template.trial_structures["trial1"].trigger_type == TriggerType.COLLISION


def test_collision_trial_validates_boundary_location() -> None:
    """Verifies that a collision trial still rejects a stimulus_location outside the trial bounds."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=150.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.COLLISION,
        ),
    }
    with pytest.raises(ValueError, match=r"stimulus_location_cm.*must be within"):
        _create_base_task_template(trial_structures=trial_structures)


def test_occupancy_trigger_trial_skips_boundary_validation() -> None:
    """Verifies that an occupancy_trigger trial ignores the boundary location but still validates the zone."""
    # An out-of-bounds stimulus_location is accepted because occupancy_trigger fires on occupancy, with no boundary.
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=20.0,
            stimulus_trigger_zone_end_cm=80.0,
            stimulus_location_cm=500.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.OCCUPANCY_TRIGGER,
            occupancy_duration_ms=1000.0,
        ),
    }
    template = _create_base_task_template(trial_structures=trial_structures)
    assert template.trial_structures["trial1"].trigger_type == TriggerType.OCCUPANCY_TRIGGER


def test_occupancy_trigger_trial_validates_zone() -> None:
    """Verifies that an occupancy_trigger trial still rejects a trigger zone outside the trial bounds."""
    trial_structures = {
        "trial1": TrialStructure(
            cue_sequence=["A", "B"],
            stimulus_trigger_zone_start_cm=150.0,
            stimulus_trigger_zone_end_cm=160.0,
            stimulus_location_cm=0.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.OCCUPANCY_TRIGGER,
            occupancy_duration_ms=1000.0,
        ),
    }
    with pytest.raises(ValueError, match=r"stimulus_trigger_zone_start_cm.*must be within"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_helpers() -> None:
    """Verifies the internal helpers of TaskTemplate."""
    template = _create_base_task_template()

    # Asserts directly on private members to lock in the derived-data contract exercised by __post_init__.
    cue_map = template._cue_by_name
    assert "A" in cue_map
    assert "B" in cue_map
    assert cue_map["A"].code == 1

    length = template._get_trial_length_cm(trial_name="trial1")
    assert length == 100.0


def test_task_template_yaml_round_trip(tmp_path: Path) -> None:
    """Verifies that TaskTemplate round-trips through YAML with every field preserved."""
    template = _create_base_task_template()

    yaml_path = tmp_path / "task_template.yaml"
    template.to_yaml(file_path=yaml_path)
    loaded = TaskTemplate.from_yaml(file_path=yaml_path)

    assert len(loaded.cues) == len(template.cues)
    assert list(loaded.trial_structures.keys()) == list(template.trial_structures.keys())
    assert loaded.vr_environment.cue_offset_cm == template.vr_environment.cue_offset_cm
