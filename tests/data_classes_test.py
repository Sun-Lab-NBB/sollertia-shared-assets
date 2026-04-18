"""Contains tests for classes and methods provided by the data_classes module."""

from pathlib import Path

import pytest
import platformdirs

from sollertia_shared_assets.data_classes import (
    SessionData,
    SessionTypes,
)
from sollertia_shared_assets.configuration import (
    Cue,
    Segment,
    VREnvironment,
    ExperimentState,
    WaterRewardTrial,
    AcquisitionSystems,
    MesoscopeExperimentConfiguration,
    set_working_directory,
)


@pytest.fixture
def sample_experiment_config() -> MesoscopeExperimentConfiguration:
    """Creates a sample MesoscopeExperimentConfiguration for testing."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
    )

    # Cues: A->50, B->75, C->50 = 175 total for Segment_abc
    cues = [
        Cue(name="A", code=1, length_cm=50.0, texture="Cue 016 - 4x1.png"),
        Cue(name="B", code=2, length_cm=75.0, texture="Cue 001 - 4x1.png"),
        Cue(name="C", code=3, length_cm=50.0, texture="Cue 008 - 2x1 repeat.png"),
    ]

    segments = [
        Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None),
    ]

    # Trial references the segment - cue_sequence and trial_length_cm are derived
    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=150.0,
        stimulus_trigger_zone_end_cm=175.0,
        stimulus_location_cm=160.0,
        show_stimulus_collision_boundary=False,
    )

    return MesoscopeExperimentConfiguration(
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


@pytest.fixture
def clean_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Sets up a clean temporary working directory for testing."""
    # Patches platformdirs to use temporary directory
    app_dir = tmp_path / "app_data"
    app_dir.mkdir()
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    working_dir = tmp_path / "working_directory"
    working_dir.mkdir()

    return working_dir


@pytest.fixture
def sample_session_hierarchy(tmp_path: Path) -> Path:
    """Creates a sample session directory hierarchy for testing."""
    # Creates the session hierarchy: root/project/animal/session/raw_data
    root = tmp_path / "data"
    session_path = root / "test_project" / "test_animal" / "2024-01-15-12-30-45-123456" / "raw_data"
    session_path.mkdir(parents=True)

    return session_path.parent


# Tests for SessionTypes enumeration


def test_session_types_values() -> None:
    """Verifies all SessionTypes enumeration values.

    This test ensures the enumeration contains all expected session types.
    """
    assert SessionTypes.LICK_TRAINING == "lick training"
    assert SessionTypes.RUN_TRAINING == "run training"
    assert SessionTypes.MESOSCOPE_EXPERIMENT == "mesoscope experiment"
    assert SessionTypes.WINDOW_CHECKING == "window checking"


def test_session_types_is_string_enum() -> None:
    """Verifies that SessionTypes inherits from StrEnum.

    This test ensures the enumeration members behave as strings.
    """
    assert isinstance(SessionTypes.LICK_TRAINING, str)
    assert isinstance(SessionTypes.RUN_TRAINING, str)
    assert isinstance(SessionTypes.MESOSCOPE_EXPERIMENT, str)
    assert isinstance(SessionTypes.WINDOW_CHECKING, str)


# Tests for SessionData dataclass


def test_session_data_default_path_fields() -> None:
    """Verifies that raw_data_path and processed_data_path default to empty Path() values.

    This test ensures the bare-Path dataclass fields are populated when SessionData is constructed
    without going through create() or load().
    """
    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
    )

    assert isinstance(session_data.raw_data_path, Path)
    assert isinstance(session_data.processed_data_path, Path)
    assert session_data.raw_data_path == Path()
    assert session_data.processed_data_path == Path()


def test_session_data_create_requires_valid_session_type(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() raises error for invalid session types.

    This test ensures only valid session types are accepted.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    with pytest.raises(ValueError, match=r"must be one of the SessionTypes"):
        SessionData.create(
            project_name="test_project",
            animal_id="test_animal",
            session_type="invalid_session_type",
            python_version="3.11.13",
            sollertia_experiment_version="3.0.0",
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            root_directory=clean_working_directory,
        )


def test_session_data_create_requires_valid_acquisition_system(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() raises error for invalid acquisition systems.

    This test ensures only valid acquisition systems are accepted.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    (clean_working_directory / "test_project").mkdir()

    with pytest.raises(ValueError, match=r"must be one of the AcquisitionSystems"):
        SessionData.create(
            project_name="test_project",
            animal_id="test_animal",
            session_type=SessionTypes.LICK_TRAINING,
            python_version="3.11.13",
            sollertia_experiment_version="3.0.0",
            acquisition_system="not_a_real_system",
            root_directory=clean_working_directory,
        )


def test_session_data_create_generates_session_directory(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() generates the session directory structure.

    This test ensures all required directories are created.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        root_directory=clean_working_directory,
    )

    # Verifies session directory exists
    session_path = session_data.raw_data_path.parent
    assert session_path.exists()
    assert session_data.raw_data_path.exists()


def test_session_data_create_saves_session_data_yaml(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() saves session_data.yaml file.

    This test ensures session metadata is persisted.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.RUN_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        root_directory=clean_working_directory,
    )

    # Verifies session_data.yaml exists
    session_data_yaml = session_data.raw_data_path.joinpath("session_data.yaml")
    assert session_data_yaml.exists()

    content = session_data_yaml.read_text()
    assert "test_project" in content
    assert "test_animal" in content


def test_session_data_create_marks_with_nk_file(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() creates the nk.bin marker file.

    This test ensures the session is marked as not yet initialized.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        root_directory=clean_working_directory,
    )

    # Verifies nk.bin exists
    assert session_data.raw_data_path.joinpath("nk.bin").exists()


def test_session_data_load_finds_session_data_yaml(sample_session_hierarchy: Path) -> None:
    """Verifies that load() finds and loads session_data.yaml.

    This test ensures sessions can be loaded from disk.
    """
    # Creates session_data.yaml
    session_data_path = sample_session_hierarchy / "raw_data" / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: lick training
acquisition_system: mesoscope
python_version: "3.11.13"
sollertia_experiment_version: "3.0.0"
raw_data: null
processed_data: null
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    assert loaded_session.project_name == "test_project"
    assert loaded_session.animal_id == "test_animal"
    assert loaded_session.session_type == SessionTypes.LICK_TRAINING


def test_session_data_load_raises_error_no_session_data_file(tmp_path: Path) -> None:
    """Verifies that load() raises error when session_data.yaml is missing.

    This test ensures proper error handling for missing session files.
    """
    # Creates empty session directory
    session_path = tmp_path / "empty_session" / "raw_data"
    session_path.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_path.parent)


def test_session_data_load_raises_error_multiple_session_data_files(tmp_path: Path) -> None:
    """Verifies that load() raises error with multiple session_data files.

    This test ensures ambiguous sessions are rejected.
    """
    session_path = tmp_path / "session"
    session_path.mkdir()

    # Creates multiple session data files
    (session_path / "session_data_1.yaml").write_text("test1")
    (session_path / "session_data_2.yaml").write_text("test2")

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_path)


def test_session_data_load_resolves_all_paths(sample_session_hierarchy: Path) -> None:
    """Verifies that load() resolves all data paths.

    This test ensures raw_data and processed_data paths are set.
    """
    session_data_path = sample_session_hierarchy / "raw_data" / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: mesoscope experiment
acquisition_system: mesoscope
python_version: "3.11.13"
sollertia_experiment_version: "3.0.0"
raw_data: null
processed_data: null
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    # Verifies paths are resolved
    assert loaded_session.raw_data_path == sample_session_hierarchy / "raw_data"
    assert loaded_session.processed_data_path == sample_session_hierarchy / "processed_data"


def test_session_data_mark_runtime_initialized_removes_nk_file(sample_session_hierarchy: Path) -> None:
    """Verifies that mark_runtime_initialized() removes the nk.bin file.

    This test ensures sessions can be marked as initialized.
    """
    session_data_path = sample_session_hierarchy / "raw_data" / "session_data.yaml"
    session_data_content = """
project_name: test_project
animal_id: test_animal
session_name: 2024-01-15-12-30-45-123456
session_type: run training
acquisition_system: mesoscope
python_version: "3.11.13"
sollertia_experiment_version: "3.0.0"
raw_data: null
processed_data: null
"""
    session_data_path.write_text(session_data_content)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    # Creates the nk.bin file
    nk_path = loaded_session.raw_data_path.joinpath("nk.bin")
    nk_path.touch()
    assert nk_path.exists()

    # Calls mark_runtime_initialized
    loaded_session.mark_runtime_initialized()

    assert not nk_path.exists()


def test_session_data_save_converts_enums_to_strings(sample_session_hierarchy: Path) -> None:
    """Verifies that save() converts SessionTypes and AcquisitionSystems to strings.

    This test ensures enum values are properly serialized in YAML.
    """
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        raw_data_path=raw_data_path,
    )
    session_data.save()

    content = session_data.raw_data_path.joinpath("session_data.yaml").read_text()
    assert "session_type: mesoscope experiment" in content
    assert "acquisition_system: mesoscope" in content


def test_session_data_save_serializes_path_fields(sample_session_hierarchy: Path) -> None:
    """Verifies that save() serializes the raw and processed data root paths as YAML scalars.

    This test ensures the path fields are written using the YamlConfig automatic Path serialization.
    """
    raw_data_path = sample_session_hierarchy / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)

    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.RUN_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        raw_data_path=raw_data_path,
    )
    session_data.save()

    content = session_data.raw_data_path.joinpath("session_data.yaml").read_text()
    assert f"raw_data_path: {raw_data_path.as_posix()}" in content
    assert "processed_data_path: ." in content


def test_session_data_create_raises_error_if_project_does_not_exist(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() raises FileNotFoundError when the project doesn't exist.

    This test ensures sessions cannot be created for non-existent projects.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Does NOT create the project directory

    with pytest.raises(FileNotFoundError) as exc_info:
        SessionData.create(
            project_name="nonexistent_project",
            animal_id="test_animal",
            session_type=SessionTypes.LICK_TRAINING,
            python_version="3.11.13",
            sollertia_experiment_version="3.0.0",
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            root_directory=clean_working_directory,
        )

    # Verifies the error message mentioning the project and CLI command
    assert "nonexistent_project" in str(exc_info.value)
    assert "sl-project create" in str(exc_info.value)


def test_session_data_create_copies_experiment_configuration(
    clean_working_directory: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() copies experiment configuration when experiment_name is provided.

    This test ensures experiment configuration files are copied to session directories.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates project directory and experiment configuration
    project_path = clean_working_directory / "test_project"
    project_path.mkdir()
    configuration_path = project_path / "configuration"
    configuration_path.mkdir()

    experiment_config_path = configuration_path / "test_experiment.yaml"
    sample_experiment_config.to_yaml(file_path=experiment_config_path)

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        experiment_name="test_experiment",
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        root_directory=clean_working_directory,
    )

    # Verifies experiment configuration was copied
    session_experiment_config = session_data.raw_data_path / "experiment_configuration.yaml"
    assert session_experiment_config.exists()

    content = session_experiment_config.read_text()
    assert "TestScene" in content


def test_session_data_create_without_experiment_name_skips_experiment_config(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() without experiment_name does not copy experiment config.

    This test ensures non-experiment sessions don't require experiment configuration.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates project directory
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        project_name="test_project",
        animal_id="test_animal",
        session_type=SessionTypes.LICK_TRAINING,
        # No experiment_name provided
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        root_directory=clean_working_directory,
    )

    # Verifies experiment configuration was NOT created
    session_experiment_config = session_data.raw_data_path / "experiment_configuration.yaml"
    assert not session_experiment_config.exists()


def test_session_data_post_init_coerces_string_session_type() -> None:
    """Verifies that __post_init__ converts a string session_type into a SessionTypes enum member.

    This test ensures the manual-construction code path that bypasses YamlConfig type hooks still produces a
    properly typed enum value.
    """
    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type="lick training",
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
    )

    assert session_data.session_type == SessionTypes.LICK_TRAINING
