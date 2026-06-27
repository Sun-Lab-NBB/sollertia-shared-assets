"""Contains tests for the dataclasses provided by the ``data_hierarchy.session_data`` module."""

from __future__ import annotations

from pathlib import Path

import pytest

from sollertia_shared_assets.enums import SessionTypes, AcquisitionSystems
from sollertia_shared_assets.registries import SYSTEM_SESSION_TYPES, SYSTEM_RAW_DATA_REGISTRY
from sollertia_shared_assets.data_hierarchy import (
    RawData,
    AnimalData,
    Directories,
    SessionData,
    RawDataFiles,
    ProcessedData,
    ProcessingTrackers,
)
from sollertia_shared_assets.mesoscope_vr import MesoscopeRawData, MesoscopeExperimentConfiguration
from sollertia_shared_assets.configuration import (
    Cue,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
    set_working_directory,
    set_task_templates_directory,
)

_DEFAULT_PYTHON_VERSION: str = "3.14.4"
"""Canonical Python version string for SessionData fixtures; matches SessionData.python_version default."""

_DEFAULT_EXPERIMENT_VERSION: str = "5.0.0"
"""Canonical sollertia-experiment version string for SessionData fixtures; matches the dataclass default."""

_SENTINEL_RAW_PATH: Path = Path("/sentinel/raw")
"""Placeholder raw_data root used by path-resolution tests; never touched on disk."""

_SENTINEL_PROCESSED_PATH: Path = Path("/sentinel/processed")
"""Placeholder processed_data root used by path-resolution tests; never touched on disk."""


@pytest.fixture
def sample_session_hierarchy(tmp_path: Path) -> Path:
    """Creates a sample session directory hierarchy and returns the session root."""
    root = tmp_path / "data"
    session_path = root / "test_project" / "test_animal" / "2024-01-15-12-30-45-123456" / "raw_data"
    session_path.mkdir(parents=True)

    return session_path.parent


def _write_session_marker(
    session_root: Path,
    *,
    session_type: SessionTypes = SessionTypes.LICK_TRAINING,
    acquisition_system: AcquisitionSystems = AcquisitionSystems.MESOSCOPE_VR,
    experiment_name: str | None = None,
) -> SessionData:
    """Writes a ``session_data.yaml`` marker via ``SessionData.save`` and returns the constructed instance."""
    raw_data_path = session_root / "raw_data"
    raw_data_path.mkdir(parents=True, exist_ok=True)
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name=session_root.name,
        session_type=session_type,
        acquisition_system=acquisition_system,
        experiment_name=experiment_name,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        raw_data_path=raw_data_path,
    )
    session.save()
    return session


def _build_sample_task_template() -> TaskTemplate:
    """Builds a minimal TaskTemplate suitable for testing the VR template caching behavior."""
    return TaskTemplate(
        cues=[
            Cue(name="A", code=1, length_cm=50.0),
            Cue(name="B", code=2, length_cm=50.0),
        ],
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
            cue_offset_cm=0.0,
        ),
        trial_structures={
            "trial1": TrialStructure(
                cue_sequence=["A", "B"],
                stimulus_trigger_zone_start_cm=80.0,
                stimulus_trigger_zone_end_cm=100.0,
                stimulus_location_cm=90.0,
                show_stimulus_collision_boundary=False,
                trigger_type=TriggerType.INTERACTION,
            ),
        },
    )


def _make_session_with_paths(raw: Path, processed: Path) -> SessionData:
    """Builds a SessionData instance with explicit roots and the runtime sub-dataclasses populated."""
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        raw_data_path=raw,
        processed_data_path=processed,
    )
    session._build_sub_dataclasses()
    return session


def _make_session(session_type: SessionTypes, experiment_name: str | None, raw: Path) -> SessionData:
    """Builds a SessionData of the given type and experiment name with the runtime sub-dataclasses populated."""
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=session_type,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        experiment_name=experiment_name,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        raw_data_path=raw,
    )
    session._build_sub_dataclasses()
    return session


def test_required_raw_assets_training_session(tmp_path: Path) -> None:
    """Verifies a non-experiment training session requires only the descriptor and the system configuration."""
    session = _make_session(SessionTypes.LICK_TRAINING, None, tmp_path / "raw_data")

    names = [name for name, _ in session.required_raw_assets()]

    assert names == [RawDataFiles.SESSION_DESCRIPTOR.value, RawDataFiles.SYSTEM_CONFIGURATION.value]


def test_required_raw_assets_vr_experiment_session(tmp_path: Path) -> None:
    """Verifies a VR experiment session also requires the experiment and VR configuration snapshots."""
    session = _make_session(SessionTypes.MESOSCOPE_EXPERIMENT, "visual_discrimination", tmp_path / "raw_data")

    names = [name for name, _ in session.required_raw_assets()]

    assert RawDataFiles.EXPERIMENT_CONFIGURATION.value in names
    assert RawDataFiles.VR_CONFIGURATION.value in names


def test_required_raw_assets_gates_experiment_and_vr_independently(tmp_path: Path) -> None:
    """Verifies the experiment-config gate (experiment_name) and the VR-config gate (session type) are independent."""
    session = _make_session(SessionTypes.LICK_TRAINING, "some_experiment", tmp_path / "raw_data")

    names = [name for name, _ in session.required_raw_assets()]

    assert RawDataFiles.EXPERIMENT_CONFIGURATION.value in names
    assert RawDataFiles.VR_CONFIGURATION.value not in names


def test_session_data_default_path_fields() -> None:
    """Verifies that raw_data_path and processed_data_path default to empty Path() values."""
    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
    )

    assert isinstance(session_data.raw_data_path, Path)
    assert isinstance(session_data.processed_data_path, Path)
    assert session_data.raw_data_path == Path()
    assert session_data.processed_data_path == Path()


def test_session_data_create_requires_valid_session_type(clean_working_directory: Path) -> None:
    """Verifies that create() raises ValueError for invalid session types."""
    set_working_directory(path=clean_working_directory)
    (clean_working_directory / "test_project").mkdir()

    with pytest.raises(ValueError, match=r"must be one of the SessionTypes"):
        SessionData.create(
            animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
            session_type="invalid_session_type",
            python_version=_DEFAULT_PYTHON_VERSION,
            sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        )


def test_session_data_create_requires_valid_acquisition_system(clean_working_directory: Path) -> None:
    """Verifies that create() raises ValueError for invalid acquisition systems."""
    set_working_directory(path=clean_working_directory)
    (clean_working_directory / "test_project").mkdir()

    with pytest.raises(ValueError, match=r"must be one of the AcquisitionSystems"):
        SessionData.create(
            animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
            session_type=SessionTypes.LICK_TRAINING,
            python_version=_DEFAULT_PYTHON_VERSION,
            sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
            acquisition_system="not_a_real_system",
        )


def test_session_data_create_generates_session_directory(clean_working_directory: Path) -> None:
    """Verifies that create() generates the session directory structure."""
    set_working_directory(path=clean_working_directory)
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
        session_type=SessionTypes.LICK_TRAINING,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    session_path = session_data.raw_data_path.parent
    assert session_path.exists()
    assert session_data.raw_data_path.exists()


def test_session_data_create_saves_session_data_yaml(clean_working_directory: Path) -> None:
    """Verifies that create() saves the session_data.yaml file with the expected metadata."""
    set_working_directory(path=clean_working_directory)
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
        session_type=SessionTypes.RUN_TRAINING,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    session_data_yaml = session_data.raw_data_path.joinpath(RawDataFiles.SESSION_DATA)
    assert session_data_yaml.exists()

    content = session_data_yaml.read_text()
    assert "test_project" in content
    assert "test_animal" in content


def test_session_data_create_marks_with_nk_file(clean_working_directory: Path) -> None:
    """Verifies that create() creates the nk.bin marker file."""
    set_working_directory(path=clean_working_directory)
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
        session_type=SessionTypes.LICK_TRAINING,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    assert session_data.raw_data_path.joinpath(RawDataFiles.NK_MARKER).exists()


def test_session_data_load_finds_session_data_yaml(sample_session_hierarchy: Path) -> None:
    """Verifies that load() finds and loads session_data.yaml."""
    _write_session_marker(session_root=sample_session_hierarchy)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    assert loaded_session.project_name == "test_project"
    assert loaded_session.animal_id == "test_animal"
    assert loaded_session.session_type == SessionTypes.LICK_TRAINING


def test_session_data_load_raises_error_no_session_data_file(tmp_path: Path) -> None:
    """Verifies that load() raises FileNotFoundError when session_data.yaml is missing."""
    session_path = tmp_path / "empty_session" / "raw_data"
    session_path.mkdir(parents=True)

    with pytest.raises(FileNotFoundError):
        SessionData.load(session_path=session_path.parent)


def test_session_data_load_raises_error_multiple_session_data_files(tmp_path: Path) -> None:
    """Verifies that load() raises FileNotFoundError when multiple session_data.yaml files are found."""
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
    _write_session_marker(session_root=sample_session_hierarchy, session_type=SessionTypes.MESOSCOPE_EXPERIMENT)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    assert loaded_session.raw_data_path == sample_session_hierarchy / "raw_data"
    assert loaded_session.processed_data_path == sample_session_hierarchy / "processed_data"


def test_session_data_mark_runtime_initialized_removes_nk_file(sample_session_hierarchy: Path) -> None:
    """Verifies that mark_runtime_initialized() removes the nk.bin file."""
    _write_session_marker(session_root=sample_session_hierarchy, session_type=SessionTypes.RUN_TRAINING)

    loaded_session = SessionData.load(session_path=sample_session_hierarchy)

    nk_path = loaded_session.raw_data_path.joinpath(RawDataFiles.NK_MARKER)
    nk_path.touch()
    assert nk_path.exists()

    loaded_session.mark_runtime_initialized()

    assert not nk_path.exists()


def test_session_data_save_converts_enums_to_strings(sample_session_hierarchy: Path) -> None:
    """Verifies that save() converts SessionTypes and AcquisitionSystems to strings."""
    session = _write_session_marker(
        session_root=sample_session_hierarchy,
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
    )

    content = session.raw_data_path.joinpath(RawDataFiles.SESSION_DATA).read_text()
    assert "session_type: mesoscope experiment" in content
    assert "acquisition_system: mesoscope" in content


def test_session_data_save_serializes_path_fields(sample_session_hierarchy: Path) -> None:
    """Verifies that save() serializes the raw and processed data root paths as YAML scalars and writes the marker
    file at ``raw_data_path / session_data.yaml``.
    """
    session = _write_session_marker(session_root=sample_session_hierarchy, session_type=SessionTypes.RUN_TRAINING)

    marker_path = session.raw_data_path.joinpath(RawDataFiles.SESSION_DATA)
    assert marker_path.exists()
    content = marker_path.read_text()
    assert f"raw_data_path: {session.raw_data_path.as_posix()}" in content
    assert "processed_data_path: ." in content


def test_session_data_create_raises_error_if_project_does_not_exist(clean_working_directory: Path) -> None:
    """Verifies that create() raises FileNotFoundError when the project does not exist."""
    set_working_directory(path=clean_working_directory)

    # Intentionally omits project-directory creation to trigger the FileNotFoundError path.

    with pytest.raises(FileNotFoundError) as exc_info:
        SessionData.create(
            animal=AnimalData(
                root=clean_working_directory, project_name="nonexistent_project", animal_id="test_animal"
            ),
            session_type=SessionTypes.LICK_TRAINING,
            python_version=_DEFAULT_PYTHON_VERSION,
            sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        )

    assert "nonexistent_project" in str(exc_info.value)
    assert "slsa configure project" in str(exc_info.value)


def test_session_data_create_copies_experiment_configuration(
    clean_working_directory: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies that create() copies experiment configuration when experiment_name is provided."""
    set_working_directory(path=clean_working_directory)

    project_path = clean_working_directory / "test_project"
    project_path.mkdir()
    configuration_path = project_path / "configuration"
    configuration_path.mkdir()

    experiment_config_path = configuration_path / "test_experiment.yaml"
    sample_experiment_config.to_yaml(file_path=experiment_config_path)

    templates_directory = clean_working_directory / "task_templates"
    templates_directory.mkdir()
    _build_sample_task_template().to_yaml(
        file_path=templates_directory / f"{sample_experiment_config.unity_scene_name}.yaml",
    )
    set_task_templates_directory(path=templates_directory)

    session_data = SessionData.create(
        animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        experiment_name="test_experiment",
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    session_experiment_config = session_data.raw_data_path / RawDataFiles.EXPERIMENT_CONFIGURATION
    assert session_experiment_config.exists()

    content = session_experiment_config.read_text()
    assert "TestScene" in content


def test_session_data_create_caches_vr_configuration(
    clean_working_directory: Path,
    sample_experiment_config: MesoscopeExperimentConfiguration,
) -> None:
    """Verifies that create() caches the VR task template alongside the experiment configuration."""
    set_working_directory(path=clean_working_directory)

    project_path = clean_working_directory / "test_project"
    project_path.mkdir()
    configuration_path = project_path / "configuration"
    configuration_path.mkdir()

    experiment_config_path = configuration_path / "test_experiment.yaml"
    sample_experiment_config.to_yaml(file_path=experiment_config_path)

    templates_directory = clean_working_directory / "task_templates"
    templates_directory.mkdir()
    sample_template = _build_sample_task_template()
    sample_template.to_yaml(
        file_path=templates_directory / f"{sample_experiment_config.unity_scene_name}.yaml",
    )
    set_task_templates_directory(path=templates_directory)

    session_data = SessionData.create(
        animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
        session_type=SessionTypes.MESOSCOPE_EXPERIMENT,
        experiment_name="test_experiment",
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    session_vr_config = session_data.raw_data_path / RawDataFiles.VR_CONFIGURATION
    assert session_vr_config.exists()
    assert session_vr_config == session_data.raw_data.vr_configuration_path

    # Round-trips the cached file through TaskTemplate to confirm it parses as a valid VR template.
    cached_template = TaskTemplate.from_yaml(file_path=session_vr_config)
    assert "trial1" in cached_template.trial_structures
    assert [cue.name for cue in cached_template.cues] == ["A", "B"]


def test_session_data_create_without_experiment_name_skips_experiment_config(clean_working_directory: Path) -> None:
    """Verifies that create() without experiment_name does not copy experiment or VR configuration."""
    set_working_directory(path=clean_working_directory)
    (clean_working_directory / "test_project").mkdir()

    session_data = SessionData.create(
        animal=AnimalData(root=clean_working_directory, project_name="test_project", animal_id="test_animal"),
        session_type=SessionTypes.LICK_TRAINING,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    session_experiment_config = session_data.raw_data_path / RawDataFiles.EXPERIMENT_CONFIGURATION
    session_vr_config = session_data.raw_data_path / RawDataFiles.VR_CONFIGURATION
    assert not session_experiment_config.exists()
    assert not session_vr_config.exists()


def test_session_data_post_init_coerces_string_session_type() -> None:
    """Verifies that __post_init__ converts a string session_type into a SessionTypes enum member."""
    session_data = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type="lick training",
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
    )

    assert session_data.session_type == SessionTypes.LICK_TRAINING


def test_session_data_raw_data_file_paths() -> None:
    """Verifies that every generic raw-data file path resolves to raw_data_path / <RawDataFiles member>."""
    session = _make_session_with_paths(raw=_SENTINEL_RAW_PATH, processed=_SENTINEL_PROCESSED_PATH)

    assert session.raw_data.session_data_path == _SENTINEL_RAW_PATH / RawDataFiles.SESSION_DATA
    assert session.raw_data.session_descriptor_path == _SENTINEL_RAW_PATH / RawDataFiles.SESSION_DESCRIPTOR
    assert session.raw_data.surgery_metadata_path == _SENTINEL_RAW_PATH / RawDataFiles.SURGERY_METADATA
    assert session.raw_data.hardware_state_path == _SENTINEL_RAW_PATH / RawDataFiles.HARDWARE_STATE
    assert session.raw_data.experiment_configuration_path == _SENTINEL_RAW_PATH / RawDataFiles.EXPERIMENT_CONFIGURATION
    assert session.raw_data.vr_configuration_path == _SENTINEL_RAW_PATH / RawDataFiles.VR_CONFIGURATION
    assert session.raw_data.system_configuration_path == _SENTINEL_RAW_PATH / RawDataFiles.SYSTEM_CONFIGURATION
    assert session.raw_data.checksum_path == _SENTINEL_RAW_PATH / RawDataFiles.CHECKSUM
    assert session.raw_data.checksum_tracker_path == _SENTINEL_RAW_PATH / ProcessingTrackers.CHECKSUM
    assert session.raw_data.nk_path == _SENTINEL_RAW_PATH / RawDataFiles.NK_MARKER


def test_session_data_system_raw_data_file_paths() -> None:
    """Verifies that the system-specific raw-data sub-dataclass is dispatched and anchored on the raw data root."""
    session = _make_session_with_paths(raw=_SENTINEL_RAW_PATH, processed=_SENTINEL_PROCESSED_PATH)

    assert isinstance(session.system_raw_data, MesoscopeRawData)
    assert session.system_raw_data == MesoscopeRawData.build(root=_SENTINEL_RAW_PATH)


def test_session_data_raw_data_directory_paths() -> None:
    """Verifies that raw-data directory paths resolve to raw_data_path / <Directories member>."""
    session = _make_session_with_paths(raw=_SENTINEL_RAW_PATH, processed=_SENTINEL_PROCESSED_PATH)

    assert session.raw_data.camera_data_path == _SENTINEL_RAW_PATH / Directories.CAMERA_DATA
    assert session.raw_data.behavior_data_path == _SENTINEL_RAW_PATH / Directories.BEHAVIOR_DATA


def test_session_data_processed_data_directory_paths() -> None:
    """Verifies that processed-data directory paths resolve to processed_data_path / <Directories member>."""
    session = _make_session_with_paths(raw=_SENTINEL_RAW_PATH, processed=_SENTINEL_PROCESSED_PATH)

    assert session.processed_data.runtime_data_path == _SENTINEL_PROCESSED_PATH / Directories.RUNTIME_DATA
    assert session.processed_data.cindra_data_path == _SENTINEL_PROCESSED_PATH / Directories.CINDRA
    assert session.processed_data.video_data_path == _SENTINEL_PROCESSED_PATH / Directories.VIDEO_DATA
    assert (
        session.processed_data.microcontroller_data_path == _SENTINEL_PROCESSED_PATH / Directories.MICROCONTROLLER_DATA
    )


def test_session_data_processing_tracker_paths() -> None:
    """Verifies that each processing-tracker path resolves to the expected subdirectory + filename."""
    session = _make_session_with_paths(raw=_SENTINEL_RAW_PATH, processed=_SENTINEL_PROCESSED_PATH)

    processed = session.processed_data
    assert processed.runtime_tracker_path == processed.runtime_data_path / ProcessingTrackers.RUNTIME
    assert processed.video_tracker_path == processed.video_data_path / ProcessingTrackers.VIDEO
    assert (
        processed.microcontroller_tracker_path
        == processed.microcontroller_data_path / ProcessingTrackers.MICROCONTROLLER
    )
    assert processed.two_photon_tracker_path == processed.cindra_data_path / ProcessingTrackers.TWO_PHOTON
    assert processed.cindra_multi_recording_path == processed.cindra_data_path / Directories.MULTI_RECORDING


def test_session_data_paths_on_default_instance() -> None:
    """Verifies that sub-dataclass paths resolve relative to Path() when the SessionData roots are at their defaults."""
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
    )
    session._build_sub_dataclasses()

    assert session.raw_data.hardware_state_path == Path(RawDataFiles.HARDWARE_STATE)
    assert session.processed_data.runtime_data_path == Path(Directories.RUNTIME_DATA)
    assert session.processed_data.two_photon_tracker_path == Path(Directories.CINDRA) / ProcessingTrackers.TWO_PHOTON


def test_session_data_sub_dataclass_attributes_unset_without_build() -> None:
    """Verifies that the sub-dataclass attributes are unset when SessionData is constructed without going through
    create() / load() / _build_sub_dataclasses().
    """
    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
    )

    with pytest.raises(AttributeError):
        _ = session.raw_data
    with pytest.raises(AttributeError):
        _ = session.processed_data
    with pytest.raises(AttributeError):
        _ = session.system_raw_data


def test_session_data_build_sub_dataclasses_unsupported_system_raises_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that _build_sub_dataclasses raises ValueError when the acquisition system is not registered."""
    # Empties the registry so the lookup falls into the defensive error branch even though the
    # acquisition_system value is a valid AcquisitionSystems member.
    monkeypatch.setattr(
        "sollertia_shared_assets.data_hierarchy.session_data.SYSTEM_RAW_DATA_REGISTRY",
        {},
    )

    session = SessionData(
        project_name="test_project",
        animal_id="test_animal",
        session_name="2024-01-15-12-30-45-123456",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        python_version=_DEFAULT_PYTHON_VERSION,
        sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
    )

    with pytest.raises(ValueError, match=r"not supported by the Sollertia platform"):
        session._build_sub_dataclasses()


def test_system_raw_data_registry_includes_mesoscope_vr() -> None:
    """Verifies that the registry exposes the expected acquisition systems."""
    assert AcquisitionSystems.MESOSCOPE_VR in SYSTEM_RAW_DATA_REGISTRY
    assert SYSTEM_RAW_DATA_REGISTRY[AcquisitionSystems.MESOSCOPE_VR] is MesoscopeRawData


def test_system_session_types_maps_mesoscope_vr() -> None:
    """Verifies that SYSTEM_SESSION_TYPES pairs the Mesoscope-VR system with its four session types."""
    assert SYSTEM_SESSION_TYPES[AcquisitionSystems.MESOSCOPE_VR] == frozenset(
        {
            SessionTypes.LICK_TRAINING,
            SessionTypes.RUN_TRAINING,
            SessionTypes.MESOSCOPE_EXPERIMENT,
            SessionTypes.WINDOW_CHECKING,
        }
    )


def test_session_data_create_rejects_unsupported_session_type(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() rejects a session type the acquisition system does not support."""
    # Narrows the Mesoscope-VR session-type set so WINDOW_CHECKING becomes an unsupported pairing for this test. The
    # enforcement runs before the project-existence check, so no on-disk project is required.
    monkeypatch.setitem(
        SYSTEM_SESSION_TYPES,
        AcquisitionSystems.MESOSCOPE_VR,
        frozenset({SessionTypes.LICK_TRAINING}),
    )
    with pytest.raises(ValueError, match=r"is not supported by"):
        SessionData.create(
            animal=AnimalData(root=tmp_path, project_name="test_project", animal_id="test_animal"),
            session_type=SessionTypes.WINDOW_CHECKING,
            python_version=_DEFAULT_PYTHON_VERSION,
            sollertia_experiment_version=_DEFAULT_EXPERIMENT_VERSION,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        )


def test_session_data_build_sub_dataclasses_returns_typed_instances() -> None:
    """Verifies that _build_sub_dataclasses populates the three sub-dataclass attributes with their concrete types."""
    session = _make_session_with_paths(raw=_SENTINEL_RAW_PATH, processed=_SENTINEL_PROCESSED_PATH)

    assert isinstance(session.raw_data, RawData)
    assert isinstance(session.processed_data, ProcessedData)
    assert isinstance(session.system_raw_data, MesoscopeRawData)


def test_raw_data_files_enum_is_string_enum() -> None:
    """Verifies that RawDataFiles members are strings (StrEnum)."""
    assert isinstance(RawDataFiles.SESSION_DATA, str)
    assert RawDataFiles.SESSION_DATA == "session_data.yaml"
    assert RawDataFiles.SESSION_DESCRIPTOR == "session_descriptor.yaml"
    assert RawDataFiles.NK_MARKER == "nk.bin"


def test_directories_enum_is_string_enum() -> None:
    """Verifies that Directories members are strings (StrEnum)."""
    assert isinstance(Directories.CINDRA, str)
    assert Directories.CINDRA == "cindra"
    assert Directories.MULTI_RECORDING == "multi_recording"
    assert Directories.RUNTIME_DATA == "runtime_data"
    assert Directories.VIDEO_DATA == "video_data"


def test_processing_trackers_enum_is_string_enum() -> None:
    """Verifies that ProcessingTrackers members are strings (StrEnum)."""
    assert isinstance(ProcessingTrackers.CHECKSUM, str)
    assert ProcessingTrackers.CHECKSUM == "checksum_processing_tracker.yaml"
    assert ProcessingTrackers.RUNTIME == "runtime_processing_tracker.yaml"
    assert ProcessingTrackers.MICROCONTROLLER == "microcontroller_processing_tracker.yaml"
    assert ProcessingTrackers.VIDEO == "video_processing_tracker.yaml"
    assert ProcessingTrackers.TWO_PHOTON == "single_recording_tracker.yaml"
    assert ProcessingTrackers.CINDRA_MULTI_RECORDING == "multi_recording_tracker.yaml"
    assert ProcessingTrackers.FORGING == "forging_tracker.yaml"
    assert ProcessingTrackers.MANIFEST == "manifest_processing_tracker.yaml"
