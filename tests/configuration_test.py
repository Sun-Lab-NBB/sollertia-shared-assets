"""Contains tests for classes and methods provided by the configuration module."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
import platformdirs

if TYPE_CHECKING:
    from pathlib import Path

from sollertia_shared_assets.configuration import (
    Cue,
    Segment,
    TriggerType,
    GasPuffTrial,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
    ExperimentState,
    WaterRewardTrial,
    AcquisitionSystems,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    create_experiment_configuration,
    populate_default_experiment_states,
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


def _create_base_task_template(
    cues: list[Cue] | None = None,
    segments: list[Segment] | None = None,
    trial_structures: dict[str, TrialStructure] | None = None,
) -> TaskTemplate:
    """Builds a TaskTemplate populated with defaults suitable for tests."""
    if cues is None:
        cues = [
            Cue(name="A", code=1, length_cm=50.0),
            Cue(name="B", code=2, length_cm=50.0),
        ]
    if segments is None:
        segments = [Segment(name="Seg_ab", cue_sequence=["A", "B"], transition_probabilities=None)]
    if trial_structures is None:
        trial_structures = {
            "trial1": TrialStructure(
                segment_name="Seg_ab",
                stimulus_trigger_zone_start_cm=80.0,
                stimulus_trigger_zone_end_cm=100.0,
                stimulus_location_cm=90.0,
                show_stimulus_collision_boundary=False,
                trigger_type=TriggerType.LICK,
            ),
        }
    return TaskTemplate(
        cues=cues,
        segments=segments,
        trial_structures=trial_structures,
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
        ),
        cue_offset_cm=0.0,
    )


def test_acquisition_systems_mesoscope_vr() -> None:
    """Verifies the MESOSCOPE_VR acquisition system enumeration value."""
    assert AcquisitionSystems.MESOSCOPE_VR == "mesoscope"
    assert str(AcquisitionSystems.MESOSCOPE_VR) == "mesoscope"


def test_acquisition_systems_is_string_enum() -> None:
    """Verifies that AcquisitionSystems inherits from StrEnum."""
    assert isinstance(AcquisitionSystems.MESOSCOPE_VR, str)


def test_mesoscope_experiment_state_initialization() -> None:
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


def test_mesoscope_experiment_state_types() -> None:
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
    """Verifies basic initialization of WaterRewardTrial."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    # Builds the configuration so that derived fields are populated.
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
    """Verifies basic initialization of GasPuffTrial."""
    trial = GasPuffTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    # Builds the configuration so that derived fields are populated.
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


def test_trial_types() -> None:
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


def test_trial_zone_end_less_than_start() -> None:
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


def test_trial_zone_start_outside_trial_length() -> None:
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


def test_trial_zone_end_outside_trial_length() -> None:
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


def test_trial_stimulus_location_outside_trial_length() -> None:
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


def test_trial_stimulus_location_precedes_trigger_zone() -> None:
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


def test_experiment_config_invalid_segment_reference() -> None:
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


def test_experiment_config_invalid_cue_in_segment() -> None:
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


def test_experiment_config_derives_trial_fields() -> None:
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
    """Verifies that MesoscopeExperimentConfiguration can be loaded from YAML."""
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    loaded_config = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    assert len(loaded_config.cues) == len(sample_experiment_config.cues)
    assert loaded_config.unity_scene_name == sample_experiment_config.unity_scene_name
    assert loaded_config.cue_offset_cm == sample_experiment_config.cue_offset_cm


def test_set_working_directory_creates_directory(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_working_directory creates the directory if it does not exist."""
    new_dir = clean_working_directory.parent / "new_working_dir"
    assert not new_dir.exists()

    # Redirects platformdirs to the isolated test application-data directory.
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(new_dir)

    assert new_dir.exists()


def test_set_working_directory_writes_path_file(clean_working_directory: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_working_directory writes the path to the cache file."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    path_file = app_dir / "working_directory_path.txt"
    assert path_file.exists()
    assert path_file.read_text() == str(clean_working_directory)


def test_set_working_directory_creates_app_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_working_directory creates the application data directory."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    working_dir = tmp_path / "working"
    working_dir.mkdir()

    assert not app_dir.exists()
    set_working_directory(working_dir)
    assert app_dir.exists()


def test_set_working_directory_overwrites_existing(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_working_directory overwrites an existing cached path."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    # Sets the initial working directory.
    first_dir = clean_working_directory / "first"
    first_dir.mkdir()
    set_working_directory(first_dir)

    # Replaces the cached path with a second directory.
    second_dir = clean_working_directory / "second"
    second_dir.mkdir()
    set_working_directory(second_dir)

    path_file = app_dir / "working_directory_path.txt"
    assert path_file.read_text() == str(second_dir)


def test_get_working_directory_returns_cached_path(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_working_directory returns the cached directory path."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)
    retrieved_dir = get_working_directory()

    assert retrieved_dir == clean_working_directory


def test_get_working_directory_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_working_directory raises FileNotFoundError if not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_working_directory()


def test_get_working_directory_raises_error_if_directory_missing(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_working_directory raises error if the cached directory does not exist."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Removes the cached working directory to simulate an out-of-date cache.
    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError, match=r"currently configured"):
        get_working_directory()


def test_set_google_credentials_path_creates_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_google_credentials_path creates the credentials cache file."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)

    cache_file = app_dir / "google_credentials_path.txt"
    assert cache_file.exists()
    assert cache_file.read_text() == str(credentials_file.resolve())


def test_set_google_credentials_path_raises_error_file_not_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_google_credentials_path raises error for non-existent files."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    non_existent_file = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        set_google_credentials_path(non_existent_file)


def test_set_google_credentials_path_raises_error_wrong_extension(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_google_credentials_path raises error for non-JSON files."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    wrong_extension = tmp_path / "credentials.txt"
    wrong_extension.write_text("not json")

    with pytest.raises(ValueError, match=r"\.json"):
        set_google_credentials_path(wrong_extension)


def test_get_google_credentials_path_returns_cached_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_google_credentials_path returns the cached credentials path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)
    retrieved_path = get_google_credentials_path()

    assert retrieved_path == credentials_file.resolve()


def test_get_google_credentials_path_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_google_credentials_path raises an error if not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_google_credentials_path()


def test_get_google_credentials_path_raises_error_if_file_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_google_credentials_path raises an error if the cached file no longer exists."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)

    # Removes the cached credentials file to simulate an out-of-date cache.
    credentials_file.unlink()

    with pytest.raises(FileNotFoundError, match=r"previously configured"):
        get_google_credentials_path()


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


def test_segment_empty_cue_sequence_raises_error() -> None:
    """Verifies that a Segment with an empty cue_sequence raises ValueError."""
    with pytest.raises(ValueError, match=r"must contain at least one cue"):
        Segment(name="Empty", cue_sequence=[], transition_probabilities=None)


def test_segment_invalid_probability_sum_raises_error() -> None:
    """Verifies that a Segment with transition_probabilities not summing to 1.0 raises ValueError."""
    with pytest.raises(ValueError, match=r"must sum to 1\.0"):
        Segment(name="Bad", cue_sequence=["A"], transition_probabilities=[0.3, 0.3])


def test_segment_valid_probabilities() -> None:
    """Verifies that a Segment with valid transition_probabilities initializes correctly."""
    segment = Segment(name="Valid", cue_sequence=["A", "B"], transition_probabilities=[0.5, 0.5])
    assert segment.transition_probabilities == [0.5, 0.5]


def test_segment_none_probabilities() -> None:
    """Verifies that a Segment with None transition_probabilities initializes correctly."""
    segment = Segment(name="NoProb", cue_sequence=["A"], transition_probabilities=None)
    assert segment.transition_probabilities is None


def test_task_template_valid_initialization() -> None:
    """Verifies that a valid TaskTemplate initializes without errors."""
    template = _create_base_task_template()
    assert len(template.cues) == 2
    assert len(template.segments) == 1
    assert "trial1" in template.trial_structures


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


def test_task_template_segment_references_unknown_cue_raises_error() -> None:
    """Verifies that a segment referencing an unknown cue raises ValueError."""
    cues = [Cue(name="A", code=1, length_cm=50.0)]
    segments = [Segment(name="Seg", cue_sequence=["A", "Z"], transition_probabilities=None)]
    with pytest.raises(ValueError, match=r"references unknown cue.*Z"):
        _create_base_task_template(cues=cues, segments=segments)


def test_task_template_trial_references_unknown_segment_raises_error() -> None:
    """Verifies that a trial referencing an unknown segment raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            segment_name="Nonexistent",
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"references unknown segment.*Nonexistent"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_invalid_trigger_type_raises_error() -> None:
    """Verifies that an invalid trigger_type raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            segment_name="Seg_ab",
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
            segment_name="Seg_ab",
            stimulus_trigger_zone_start_cm=90.0,
            stimulus_trigger_zone_end_cm=80.0,
            stimulus_location_cm=85.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"must be greater than or equal to"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_zone_start_outside_segment_raises_error() -> None:
    """Verifies that zone_start outside segment length raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            segment_name="Seg_ab",
            stimulus_trigger_zone_start_cm=150.0,
            stimulus_trigger_zone_end_cm=160.0,
            stimulus_location_cm=155.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"stimulus_trigger_zone_start_cm.*must be within"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_zone_end_outside_segment_raises_error() -> None:
    """Verifies that zone_end outside segment length raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            segment_name="Seg_ab",
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=150.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"stimulus_trigger_zone_end_cm.*must be within"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_location_outside_segment_raises_error() -> None:
    """Verifies that stimulus_location outside segment length raises ValueError."""
    trial_structures = {
        "trial1": TrialStructure(
            segment_name="Seg_ab",
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
            segment_name="Seg_ab",
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=70.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.LICK,
        ),
    }
    with pytest.raises(ValueError, match=r"(?s)stimulus_location_cm.*must not precede"):
        _create_base_task_template(trial_structures=trial_structures)


def test_task_template_properties() -> None:
    """Verifies the internal properties of TaskTemplate."""
    template = _create_base_task_template()

    # Asserts directly on private members to lock in the derived-data contract exercised by __post_init__.
    cue_map = template._cue_by_name  # noqa: SLF001
    assert "A" in cue_map
    assert "B" in cue_map
    assert cue_map["A"].code == 1

    segment_map = template._segment_by_name  # noqa: SLF001
    assert "Seg_ab" in segment_map

    length = template._get_segment_length_cm(segment_name="Seg_ab")  # noqa: SLF001
    assert length == 100.0


def test_experiment_config_duplicate_cue_codes_raises_error() -> None:
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


def test_experiment_config_duplicate_cue_names_raises_error() -> None:
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


def test_trial_validate_zones_zero_length_raises_error() -> None:
    """Verifies that validate_zones raises ValueError when trial_length_cm is zero."""
    # trial_length_cm defaults to 0.0 until the enclosing configuration's __post_init__ populates it.
    trial = WaterRewardTrial(
        segment_name="Seg",
        stimulus_trigger_zone_start_cm=10.0,
        stimulus_trigger_zone_end_cm=20.0,
        stimulus_location_cm=15.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match=r"trial_length_cm must be populated"):
        trial.validate_zones()


def test_set_task_templates_directory_creates_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory caches the directory path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(templates_dir)

    cache_file = app_dir / "task_templates_directory_path.txt"
    assert cache_file.exists()
    assert cache_file.read_text() == str(templates_dir.resolve())


def test_set_task_templates_directory_raises_error_not_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory raises error for non-existent directory."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    nonexistent = tmp_path / "missing_dir"

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        set_task_templates_directory(nonexistent)


def test_set_task_templates_directory_raises_error_not_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_task_templates_directory raises error when path is a file."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    file_path = tmp_path / "a_file.txt"
    file_path.write_text("content")

    with pytest.raises(ValueError, match=r"does not point to a\s+directory"):
        set_task_templates_directory(file_path)


def test_get_task_templates_directory_returns_cached_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_task_templates_directory returns the cached directory path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(templates_dir)
    retrieved = get_task_templates_directory()

    assert retrieved == templates_dir.resolve()


def test_get_task_templates_directory_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_task_templates_directory raises error if not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_task_templates_directory()


def test_get_task_templates_directory_raises_error_if_directory_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_task_templates_directory raises error if cached directory was deleted."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(templates_dir)
    shutil.rmtree(templates_dir)

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        get_task_templates_directory()


def test_create_experiment_configuration_mesoscope_vr() -> None:
    """Verifies that create_experiment_configuration creates a valid MesoscopeExperimentConfiguration."""
    template = _create_base_task_template()

    config = create_experiment_configuration(
        template=template,
        system=AcquisitionSystems.MESOSCOPE_VR,
        unity_scene_name="TestScene",
    )

    assert isinstance(config, MesoscopeExperimentConfiguration)
    assert config.unity_scene_name == "TestScene"
    assert len(config.cues) == 2
    assert len(config.trial_structures) == 1
    trial = config.trial_structures["trial1"]
    assert isinstance(trial, WaterRewardTrial)
    assert trial.reward_size_ul == 5.0


def test_create_experiment_configuration_with_occupancy_trial() -> None:
    """Verifies that create_experiment_configuration handles occupancy (gas puff) trials."""
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=2, length_cm=50.0),
    ]
    segments = [Segment(name="Seg_ab", cue_sequence=["A", "B"], transition_probabilities=None)]
    trial_structures = {
        "occ_trial": TrialStructure(
            segment_name="Seg_ab",
            stimulus_trigger_zone_start_cm=80.0,
            stimulus_trigger_zone_end_cm=100.0,
            stimulus_location_cm=90.0,
            show_stimulus_collision_boundary=False,
            trigger_type=TriggerType.OCCUPANCY,
        ),
    }
    template = TaskTemplate(
        cues=cues,
        segments=segments,
        trial_structures=trial_structures,
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="P",
            cm_per_unity_unit=10.0,
        ),
        cue_offset_cm=5.0,
    )

    config = create_experiment_configuration(
        template=template,
        system=AcquisitionSystems.MESOSCOPE_VR,
        unity_scene_name="OccScene",
        default_puff_duration_ms=200,
        default_occupancy_duration_ms=2000,
    )

    assert isinstance(config, MesoscopeExperimentConfiguration)
    trial = config.trial_structures["occ_trial"]
    assert isinstance(trial, GasPuffTrial)
    assert trial.puff_duration_ms == 200
    assert trial.occupancy_duration_ms == 2000
    assert config.cue_offset_cm == 5.0


def test_create_experiment_configuration_invalid_system_raises_error() -> None:
    """Verifies that create_experiment_configuration raises ValueError for unsupported systems."""
    template = _create_base_task_template()

    with pytest.raises(ValueError, match=r"not supported"):
        create_experiment_configuration(
            template=template,
            system="nonexistent_system",
            unity_scene_name="Test",
        )


def test_populate_default_experiment_states_with_water_reward() -> None:
    """Verifies that populate_default_experiment_states adds states with water reward guidance."""
    config = _create_test_config_with_trial(
        WaterRewardTrial(
            segment_name="TestSegment",
            stimulus_trigger_zone_start_cm=180.0,
            stimulus_trigger_zone_end_cm=200.0,
            stimulus_location_cm=190.0,
            show_stimulus_collision_boundary=False,
        ),
    )

    populate_default_experiment_states(experiment_configuration=config, state_count=3)

    assert "state_1" in config.experiment_states
    assert "state_2" in config.experiment_states
    assert "state_3" in config.experiment_states

    state_1 = config.experiment_states["state_1"]
    assert state_1.experiment_state_code == 1
    assert state_1.state_duration_s == 60
    assert state_1.supports_trials is True
    assert state_1.reinforcing_initial_guided_trials == 3
    assert state_1.aversive_initial_guided_trials == 0


def test_populate_default_experiment_states_with_gas_puff() -> None:
    """Verifies that populate_default_experiment_states adds states with gas puff guidance."""
    config = _create_test_config_with_trial(
        GasPuffTrial(
            segment_name="TestSegment",
            stimulus_trigger_zone_start_cm=180.0,
            stimulus_trigger_zone_end_cm=200.0,
            stimulus_location_cm=190.0,
            show_stimulus_collision_boundary=False,
        ),
    )

    populate_default_experiment_states(experiment_configuration=config, state_count=2)

    state_1 = config.experiment_states["state_1"]
    assert state_1.reinforcing_initial_guided_trials == 0
    assert state_1.aversive_initial_guided_trials == 3
    assert state_1.aversive_recovery_failed_threshold == 9
    assert state_1.aversive_recovery_guided_trials == 3
