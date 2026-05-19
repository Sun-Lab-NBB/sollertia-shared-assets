"""Contains tests for the platform configuration utilities provided by the
``configuration.configuration_utilities`` module.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
import platformdirs

from sollertia_shared_assets.configuration import (
    Cue,
    TriggerType,
    GasPuffTrial,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
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


def test_acquisition_systems_mesoscope_vr_value() -> None:
    """Verifies the MESOSCOPE_VR acquisition system enumeration value."""
    assert AcquisitionSystems.MESOSCOPE_VR == "mesoscope"
    assert str(AcquisitionSystems.MESOSCOPE_VR) == "mesoscope"


def test_acquisition_systems_is_string_enum() -> None:
    """Verifies that AcquisitionSystems inherits from StrEnum."""
    assert isinstance(AcquisitionSystems.MESOSCOPE_VR, str)


def test_set_working_directory_creates_directory(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory creates the directory if it does not exist."""
    new_dir = clean_working_directory.parent / "new_working_dir"
    assert not new_dir.exists()

    set_working_directory(path=new_dir)

    assert new_dir.exists()


def test_set_working_directory_writes_path_file(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory writes the path to the cache file."""
    set_working_directory(path=clean_working_directory)

    app_dir = clean_working_directory.parent / "app_data"
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
    set_working_directory(path=working_dir)
    assert app_dir.exists()


def test_set_working_directory_overwrites_existing(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory overwrites an existing cached path."""
    first_dir = clean_working_directory / "first"
    first_dir.mkdir()
    set_working_directory(path=first_dir)

    second_dir = clean_working_directory / "second"
    second_dir.mkdir()
    set_working_directory(path=second_dir)

    app_dir = clean_working_directory.parent / "app_data"
    path_file = app_dir / "working_directory_path.txt"
    assert path_file.read_text() == str(second_dir)


def test_get_working_directory_returns_cached_path(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory returns the cached directory path."""
    set_working_directory(path=clean_working_directory)
    retrieved_dir = get_working_directory()

    assert retrieved_dir == clean_working_directory


def test_get_working_directory_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_working_directory raises FileNotFoundError if not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_working_directory()


def test_get_working_directory_raises_error_if_directory_missing(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory raises error if the cached directory does not exist."""
    set_working_directory(path=clean_working_directory)

    # Simulates an out-of-date cache.
    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError, match=r"currently configured"):
        get_working_directory()


def test_set_google_credentials_path_creates_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_google_credentials_path creates the credentials cache file."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(path=credentials_file)

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
        set_google_credentials_path(path=non_existent_file)


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
        set_google_credentials_path(path=wrong_extension)


def test_get_google_credentials_path_returns_cached_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_google_credentials_path returns the cached credentials path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(path=credentials_file)
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

    set_google_credentials_path(path=credentials_file)

    # Simulates an out-of-date cache.
    credentials_file.unlink()

    with pytest.raises(FileNotFoundError, match=r"previously configured"):
        get_google_credentials_path()


def test_set_task_templates_directory_creates_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory caches the directory path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(path=templates_dir)

    cache_file = app_dir / "task_templates_directory_path.txt"
    assert cache_file.exists()
    assert cache_file.read_text() == str(templates_dir.resolve())


def test_set_task_templates_directory_raises_error_not_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory raises error for non-existent directory."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    nonexistent = tmp_path / "missing_dir"

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        set_task_templates_directory(path=nonexistent)


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
        set_task_templates_directory(path=file_path)


def test_get_task_templates_directory_returns_cached_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_task_templates_directory returns the cached directory path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(path=templates_dir)
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

    set_task_templates_directory(path=templates_dir)
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
    assert len(config.trial_structures) == 1
    trial = config.trial_structures["trial1"]
    assert isinstance(trial, WaterRewardTrial)
    assert trial.reward_size_ul == 5.0


def test_create_experiment_configuration_with_occupancy_trial() -> None:
    """Verifies that create_experiment_configuration handles occupancy (gas puff) trials."""
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
    config = MesoscopeExperimentConfiguration(
        trial_structures={"test_trial": WaterRewardTrial()},
        experiment_states={},
        unity_scene_name="TestScene",
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
    config = MesoscopeExperimentConfiguration(
        trial_structures={"test_trial": GasPuffTrial()},
        experiment_states={},
        unity_scene_name="TestScene",
    )

    populate_default_experiment_states(experiment_configuration=config, state_count=2)

    state_1 = config.experiment_states["state_1"]
    assert state_1.reinforcing_initial_guided_trials == 0
    assert state_1.aversive_initial_guided_trials == 3
    assert state_1.aversive_recovery_failed_threshold == 9
    assert state_1.aversive_recovery_guided_trials == 3
