"""Contains tests for classes and methods provided by the data_classes module."""

from pathlib import Path

import pytest
import platformdirs

from sollertia_shared_assets.data_classes import (
    Directories,
    MesoscopeRawData,
    MesoscopeRawDataFiles,
    MesoscopeDirectories,
    RawData,
    RawDataFiles,
    ProcessedData,
    SessionData,
    SessionTypes,
    ProcessingTrackers,
)
from sollertia_shared_assets.configuration import (
    AcquisitionSystems,
    MesoscopeExperimentConfiguration,
    set_working_directory,
)


@pytest.fixture
def sample_session_hierarchy(tmp_path: Path) -> Path:
    """Creates a sample session directory hierarchy for testing."""
    # Builds the session hierarchy: root/project/animal/session/raw_data.
    root = tmp_path / "data"
    session_path = root / "test_project" / "test_animal" / "2024-01-15-12-30-45-123456" / "raw_data"
    session_path.mkdir(parents=True)

    return session_path.parent


def test_session_types_values() -> None:
    """Verifies all SessionTypes enumeration values."""
    assert SessionTypes.LICK_TRAINING == "lick training"
    assert SessionTypes.RUN_TRAINING == "run training"
    assert SessionTypes.MESOSCOPE_EXPERIMENT == "mesoscope experiment"
    assert SessionTypes.WINDOW_CHECKING == "window checking"


def test_session_types_is_string_enum() -> None:
    """Verifies that SessionTypes inherits from StrEnum."""
    assert isinstance(SessionTypes.LICK_TRAINING, str)
    assert isinstance(SessionTypes.RUN_TRAINING, str)
    assert isinstance(SessionTypes.MESOSCOPE_EXPERIMENT, str)
    assert isinstance(SessionTypes.WINDOW_CHECKING, str)


def test_session_data_default_path_fields() -> None:
    """Verifies that raw_data_path and processed_data_path default to empty Path() values."""
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
    """Verifies that create() raises error for invalid session types."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates the project directory.
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
    """Verifies that create() raises error for invalid acquisition systems."""
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
    """Verifies that create() generates the session directory structure."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates the project directory.
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

    # Verifies that the session directory and its raw_data subdirectory were created.
    session_path = session_data.raw_data_path.parent
    assert session_path.exists()
    assert session_data.raw_data_path.exists()


def test_session_data_create_saves_session_data_yaml(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() saves the session_data.yaml file."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates the project directory.
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

    # Verifies that session_data.yaml exists and contains the expected metadata.
    session_data_yaml = session_data.raw_data_path.joinpath("session_data.yaml")
    assert session_data_yaml.exists()

    content = session_data_yaml.read_text()
    assert "test_project" in content
    assert "test_animal" in content


def test_session_data_create_marks_with_nk_file(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() creates the nk.bin marker file."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates the project directory.
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

    # Verifies that the nk.bin marker file was created.
    assert session_data.raw_data_path.joinpath("nk.bin").exists()


def test_session_data_load_finds_session_data_yaml(sample_session_hierarchy: Path) -> None:
    """Verifies that load() finds and loads session_data.yaml."""
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
    """Verifies that load() raises error when session_data.yaml is missing."""
    # Creates an empty session directory without a session_data.yaml file.
    session_path = tmp_path / "empty_session" / "raw_data"
    session_path.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_path.parent)


def test_session_data_load_raises_error_multiple_session_data_files(tmp_path: Path) -> None:
    """Verifies that load() raises error when multiple session_data.yaml files are found."""
    session_path = tmp_path / "session"
    (session_path / "first").mkdir(parents=True)
    (session_path / "second").mkdir(parents=True)

    # Creates two session_data.yaml files so rglob() returns more than one match.
    (session_path / "first" / "session_data.yaml").write_text("first")
    (session_path / "second" / "session_data.yaml").write_text("second")

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_path)


def test_session_data_load_resolves_all_paths(sample_session_hierarchy: Path) -> None:
    """Verifies that load() resolves the raw_data and processed_data paths."""
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

    assert loaded_session.raw_data_path == sample_session_hierarchy / "raw_data"
    assert loaded_session.processed_data_path == sample_session_hierarchy / "processed_data"


def test_session_data_mark_runtime_initialized_removes_nk_file(sample_session_hierarchy: Path) -> None:
    """Verifies that mark_runtime_initialized() removes the nk.bin file."""
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

    nk_path = loaded_session.raw_data_path.joinpath("nk.bin")
    nk_path.touch()
    assert nk_path.exists()

    loaded_session.mark_runtime_initialized()

    assert not nk_path.exists()


def test_session_data_save_converts_enums_to_strings(sample_session_hierarchy: Path) -> None:
    """Verifies that save() converts SessionTypes and AcquisitionSystems to strings."""
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
    """Verifies that save() serializes the raw and processed data root paths as YAML scalars and writes the marker
    file at ``raw_data_path / session_data.yaml``.
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

    marker_path = raw_data_path.joinpath(RawDataFiles.SESSION_DATA)
    assert marker_path.exists()
    content = marker_path.read_text()
    assert f"raw_data_path: {raw_data_path.as_posix()}" in content
    assert "processed_data_path: ." in content


def test_session_data_create_raises_error_if_project_does_not_exist(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() raises FileNotFoundError when the project does not exist."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Intentionally omits project-directory creation to trigger the FileNotFoundError path.

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

    # Verifies that the error message names the project and suggests the CLI command.
    assert "nonexistent_project" in str(exc_info.value)
    assert "sl-project create" in str(exc_info.value)


def test_session_data_create_copies_experiment_configuration(
    clean_working_directory: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() copies experiment configuration when experiment_name is provided."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates the project directory and writes the experiment configuration file.
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

    # Verifies that the experiment configuration was copied into the session directory.
    session_experiment_config = session_data.raw_data_path / "experiment_configuration.yaml"
    assert session_experiment_config.exists()

    content = session_experiment_config.read_text()
    assert "TestScene" in content


def test_session_data_create_without_experiment_name_skips_experiment_config(
    clean_working_directory: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() without experiment_name does not copy experiment configuration."""
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates the project directory.
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

    # Verifies that no experiment configuration file was written.
    session_experiment_config = session_data.raw_data_path / "experiment_configuration.yaml"
    assert not session_experiment_config.exists()


def test_session_data_post_init_coerces_string_session_type() -> None:
    """Verifies that __post_init__ converts a string session_type into a SessionTypes enum member."""
    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type="lick training",
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
    )

    assert session_data.session_type == SessionTypes.LICK_TRAINING


def _make_session(raw: Path, processed: Path) -> SessionData:
    """Builds a SessionData instance with explicit roots and the runtime sub-dataclasses populated."""
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
        raw_data_path=raw,
        processed_data_path=processed,
    )
    session._build_sub_dataclasses()
    return session


def test_session_data_raw_data_file_paths() -> None:
    """Verifies that every generic raw-data file path resolves to raw_data_path / <RawDataFiles member>."""
    session = _make_session(raw=Path("/tmp/raw"), processed=Path("/tmp/proc"))

    assert session.raw_data.session_data_path == Path("/tmp/raw") / RawDataFiles.SESSION_DATA
    assert session.raw_data.session_descriptor_path == Path("/tmp/raw") / RawDataFiles.SESSION_DESCRIPTOR
    assert session.raw_data.surgery_metadata_path == Path("/tmp/raw") / RawDataFiles.SURGERY_METADATA
    assert session.raw_data.hardware_state_path == Path("/tmp/raw") / RawDataFiles.HARDWARE_STATE
    assert session.raw_data.experiment_configuration_path == Path("/tmp/raw") / RawDataFiles.EXPERIMENT_CONFIGURATION
    assert session.raw_data.system_configuration_path == Path("/tmp/raw") / RawDataFiles.SYSTEM_CONFIGURATION
    assert session.raw_data.checksum_path == Path("/tmp/raw") / RawDataFiles.CHECKSUM
    assert session.raw_data.checksum_tracker_path == Path("/tmp/raw") / ProcessingTrackers.CHECKSUM
    assert session.raw_data.nk_path == Path("/tmp/raw") / RawDataFiles.NK_MARKER


def test_session_data_system_raw_data_file_paths() -> None:
    """Verifies that every Mesoscope-VR-specific raw-data file path resolves under raw_data_path."""
    session = _make_session(raw=Path("/tmp/raw"), processed=Path("/tmp/proc"))

    assert isinstance(session.system_raw_data, MesoscopeRawData)
    assert session.system_raw_data.zaber_positions_path == Path("/tmp/raw") / MesoscopeRawDataFiles.ZABER_POSITIONS
    assert (
        session.system_raw_data.mesoscope_positions_path == Path("/tmp/raw") / MesoscopeRawDataFiles.MESOSCOPE_POSITIONS
    )
    assert session.system_raw_data.window_screenshot_path == Path("/tmp/raw") / MesoscopeRawDataFiles.WINDOW_SCREENSHOT
    assert session.system_raw_data.mesoscope_data_path == Path("/tmp/raw") / MesoscopeDirectories.MESOSCOPE_DATA


def test_session_data_raw_data_directory_paths() -> None:
    """Verifies that raw-data directory paths resolve to raw_data_path / <Directories member>."""
    session = _make_session(raw=Path("/tmp/raw"), processed=Path("/tmp/proc"))

    assert session.raw_data.camera_data_path == Path("/tmp/raw") / Directories.CAMERA_DATA
    assert session.raw_data.behavior_data_path == Path("/tmp/raw") / Directories.BEHAVIOR_DATA


def test_session_data_processed_data_directory_paths() -> None:
    """Verifies that processed-data directory paths resolve to processed_data_path / <Directories member>."""
    session = _make_session(raw=Path("/tmp/raw"), processed=Path("/tmp/proc"))

    assert session.processed_data.behavior_data_path == Path("/tmp/proc") / Directories.BEHAVIOR_DATA
    assert session.processed_data.cindra_data_path == Path("/tmp/proc") / Directories.CINDRA
    assert session.processed_data.camera_timestamps_path == Path("/tmp/proc") / Directories.CAMERA_TIMESTAMPS
    assert session.processed_data.video_data_path == Path("/tmp/proc") / Directories.CAMERA_DATA
    assert session.processed_data.microcontroller_data_path == Path("/tmp/proc") / Directories.MICROCONTROLLER_DATA


def test_directories_enum_disambiguation() -> None:
    """Verifies that raw-side and processed-side fields sharing a Directories value resolve to distinct paths
    anchored on the correct parent.
    """
    session = _make_session(raw=Path("/tmp/raw"), processed=Path("/tmp/proc"))

    assert session.raw_data.camera_data_path != session.processed_data.video_data_path
    assert session.raw_data.behavior_data_path != session.processed_data.behavior_data_path


def test_session_data_processing_tracker_paths() -> None:
    """Verifies that each processing-tracker path resolves to the expected subdirectory + filename."""
    session = _make_session(raw=Path("/tmp/raw"), processed=Path("/tmp/proc"))

    processed = session.processed_data
    assert processed.behavior_tracker_path == processed.behavior_data_path / ProcessingTrackers.BEHAVIOR
    assert processed.camera_tracker_path == processed.camera_timestamps_path / ProcessingTrackers.CAMERA
    assert processed.video_tracker_path == processed.video_data_path / ProcessingTrackers.VIDEO
    assert (
        processed.microcontroller_tracker_path
        == processed.microcontroller_data_path / ProcessingTrackers.MICROCONTROLLER
    )
    assert (
        processed.cindra_single_recording_tracker_path
        == processed.cindra_data_path / ProcessingTrackers.CINDRA_SINGLE_RECORDING
    )
    assert processed.cindra_multi_recording_path == processed.cindra_data_path / Directories.MULTI_RECORDING


def test_session_data_paths_on_default_instance() -> None:
    """Verifies that sub-dataclass paths resolve relative to Path() when the SessionData roots are at their defaults."""
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
    )
    session._build_sub_dataclasses()

    assert session.raw_data.hardware_state_path == Path(RawDataFiles.HARDWARE_STATE)
    assert session.processed_data.behavior_data_path == Path(Directories.BEHAVIOR_DATA)
    assert (
        session.processed_data.cindra_single_recording_tracker_path
        == Path(Directories.CINDRA) / ProcessingTrackers.CINDRA_SINGLE_RECORDING
    )


def test_session_data_sub_dataclass_attributes_unset_without_build() -> None:
    """Verifies that the sub-dataclass attributes are unset when SessionData is constructed without going through
    create() / load() / _build_sub_dataclasses().
    """
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        python_version="3.11.13",
        sollertia_experiment_version="3.0.0",
    )

    with pytest.raises(AttributeError):
        _ = session.raw_data
    with pytest.raises(AttributeError):
        _ = session.processed_data
    with pytest.raises(AttributeError):
        _ = session.system_raw_data


def test_session_data_build_sub_dataclasses_returns_typed_instances() -> None:
    """Verifies that _build_sub_dataclasses populates the three sub-dataclass attributes with their concrete types."""
    session = _make_session(raw=Path("/tmp/raw"), processed=Path("/tmp/proc"))

    assert isinstance(session.raw_data, RawData)
    assert isinstance(session.processed_data, ProcessedData)
    assert isinstance(session.system_raw_data, MesoscopeRawData)


def test_raw_data_files_enum_is_string_enum() -> None:
    """Verifies that RawDataFiles members are strings (StrEnum) and that Mesoscope-specific entries live separately."""
    assert isinstance(RawDataFiles.SESSION_DATA, str)
    assert RawDataFiles.SESSION_DATA == "session_data.yaml"
    assert RawDataFiles.SESSION_DESCRIPTOR == "session_descriptor.yaml"
    assert RawDataFiles.NK_MARKER == "nk.bin"
    assert MesoscopeRawDataFiles.ZABER_POSITIONS == "zaber_positions.yaml"
    assert MesoscopeRawDataFiles.MESOSCOPE_POSITIONS == "mesoscope_positions.yaml"
    assert MesoscopeRawDataFiles.WINDOW_SCREENSHOT == "window_screenshot.png"


def test_directories_enum_is_string_enum() -> None:
    """Verifies that Directories members are strings (StrEnum)."""
    assert isinstance(Directories.CINDRA, str)
    assert Directories.CINDRA == "cindra"
    assert Directories.MULTI_RECORDING == "multi_recording"


def test_processing_trackers_enum_is_string_enum() -> None:
    """Verifies that ProcessingTrackers members are strings (StrEnum)."""
    assert isinstance(ProcessingTrackers.BEHAVIOR, str)
    assert ProcessingTrackers.CHECKSUM == "checksum_processing_tracker.yaml"
    assert ProcessingTrackers.CINDRA_SINGLE_RECORDING == "single_recording_tracker.yaml"
    assert ProcessingTrackers.CINDRA_MULTI_RECORDING == "multi_recording_tracker.yaml"
    assert ProcessingTrackers.VIDEO == "video_processing_tracker.yaml"
    assert ProcessingTrackers.FORGING == "forging_tracker.yaml"
    assert ProcessingTrackers.MANIFEST == "manifest_processing_tracker.yaml"
    assert ProcessingTrackers.TRANSFER == "transfer_processing_tracker.yaml"
