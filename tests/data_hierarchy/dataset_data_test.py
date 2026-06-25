"""Contains tests for the DatasetData, DatasetSession, and DatasetAnimal dataclasses housed in
sollertia_shared_assets.data_hierarchy.dataset_data.
"""

from pathlib import Path

import pytest
from sollertia_shared_assets import (
    DatasetData,
    SessionTypes,
    DatasetFiles,
    DatasetSession,
    AcquisitionSystems,
)

# A representative column-description binding, passed to every create() call. The mapping is intentionally small;
# the assembly worker that produces the real mapping lives in the acquisition-system packages, not in slsa.
COLUMN_DESCRIPTIONS: dict[str, str] = {
    "time_us": "Microsecond-precision sample timestamps from the acquisition reference clock.",
    "lick": "Lick sensor state at each sample.",
}

# Tests for DatasetSession dataclass


def test_dataset_session_default_initialization() -> None:
    """Verifies default initialization of DatasetSession.

    This test ensures session_path defaults to an empty Path() when not provided.
    """
    dataset_session = DatasetSession(session="2024-01-15-12-30-45-123456", animal="test_animal")

    assert dataset_session.session == "2024-01-15-12-30-45-123456"
    assert dataset_session.animal == "test_animal"
    assert dataset_session.session_path == Path()


def test_dataset_session_is_frozen() -> None:
    """Verifies that DatasetSession instances are immutable.

    This test ensures attempting to modify a DatasetSession field raises an error.
    """
    dataset_session = DatasetSession(
        session="2024-01-15-12-30-45-123456",
        animal="test_animal",
        session_path=Path("/tmp/test"),
    )

    with pytest.raises(AttributeError):
        dataset_session.session = "new_session"  # type: ignore[misc]


def test_dataset_session_data_and_descriptor_paths() -> None:
    """Verifies that data_path, descriptor_path, and vr_configuration_path resolve relative to session_path."""
    session_path = Path("/tmp/test_dataset/animal_a/2024-01-15-12-30-45-123456")
    dataset_session = DatasetSession(
        session="2024-01-15-12-30-45-123456",
        animal="animal_a",
        session_path=session_path,
    )

    assert dataset_session.data_path == session_path / "data.feather"
    assert dataset_session.descriptor_path == session_path / "session_descriptor.yaml"
    assert dataset_session.vr_configuration_path == session_path / "vr_configuration.yaml"


# Tests for DatasetData dataclass


def test_dataset_data_direct_initialization() -> None:
    """Verifies that DatasetData can be constructed directly for in-memory use (load path)."""
    dataset_data = DatasetData(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    assert dataset_data.name == "test_dataset"
    assert dataset_data.project == "test_project"
    assert dataset_data.session_type == SessionTypes.LICK_TRAINING
    assert dataset_data.acquisition_system == AcquisitionSystems.MESOSCOPE_VR
    assert dataset_data.sessions == ()


def test_dataset_data_create_initializes_directory_structure(tmp_path: Path) -> None:
    """Verifies that DatasetData.create materializes the dataset hierarchy on disk."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
        DatasetSession(session="2024-01-16-09-15-22-654321", animal="animal_b"),
    )

    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    dataset_root = tmp_path / "test_dataset"
    assert dataset_root.is_dir()
    assert (dataset_root / "dataset.yaml").is_file()
    assert (dataset_root / "animal_a" / "2024-01-15-12-30-45-123456").is_dir()
    assert (dataset_root / "animal_b" / "2024-01-16-09-15-22-654321").is_dir()
    assert dataset_data.dataset_data_path == dataset_root / "dataset.yaml"


def test_dataset_data_create_resolves_session_paths(tmp_path: Path) -> None:
    """Verifies that create() rebuilds each input DatasetSession with its resolved session_path."""
    inputs = (DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a", session_path=Path("/ignored")),)

    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=inputs,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    resolved = dataset_data.sessions[0]
    assert resolved.session_path == tmp_path / "test_dataset" / "animal_a" / "2024-01-15-12-30-45-123456"


def test_dataset_data_create_accepts_set_of_sessions(tmp_path: Path) -> None:
    """Verifies that create() accepts a set of DatasetSession instances and converts them to a tuple."""
    sessions = {
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
        DatasetSession(session="2024-01-16-09-15-22-654321", animal="animal_b"),
    }

    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    assert isinstance(dataset_data.sessions, tuple)
    assert len(dataset_data.sessions) == 2


def test_dataset_data_create_raises_on_empty_sessions(tmp_path: Path) -> None:
    """Verifies that create() rejects an empty sessions collection."""
    with pytest.raises(ValueError, match="at least one"):
        DatasetData.create(
            name="empty_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=(),
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )


def test_dataset_data_create_rejects_existing_directory(tmp_path: Path) -> None:
    """Verifies that create() refuses to overwrite an existing dataset directory."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),)
    (tmp_path / "existing").mkdir()

    with pytest.raises(FileExistsError):
        DatasetData.create(
            name="existing",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )


def test_dataset_data_load_roundtrips_through_yaml(tmp_path: Path) -> None:
    """Verifies that load() reconstructs a DatasetData instance from a previously saved dataset.yaml file."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
        DatasetSession(session="2024-01-16-09-15-22-654321", animal="animal_b"),
    )
    created = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    loaded = DatasetData.load(dataset_path=tmp_path / "test_dataset")

    assert loaded.name == created.name
    assert loaded.project == created.project
    assert loaded.session_type == SessionTypes.LICK_TRAINING
    assert loaded.acquisition_system == AcquisitionSystems.MESOSCOPE_VR
    assert len(loaded.sessions) == 2


def test_dataset_data_load_errors_when_no_marker(tmp_path: Path) -> None:
    """Verifies that load() raises FileNotFoundError when dataset.yaml cannot be located."""
    (tmp_path / "empty_dataset").mkdir()

    with pytest.raises(FileNotFoundError):
        DatasetData.load(dataset_path=tmp_path / "empty_dataset")


def test_dataset_data_animals_expose_per_animal_paths(tmp_path: Path) -> None:
    """Verifies that DatasetAnimal instances expose the canonical per-animal subpaths."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
        DatasetSession(session="2024-01-15-12-30-45-000002", animal="animal_b"),
        DatasetSession(session="2024-01-15-12-30-45-000003", animal="animal_a"),
    )
    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    dataset_root = tmp_path / "test_dataset"
    surgery_paths = {animal.animal: animal.surgery_path for animal in dataset_data.animals}

    assert set(surgery_paths.keys()) == {"animal_a", "animal_b"}
    assert surgery_paths["animal_a"] == dataset_root / "animal_a" / "surgery_metadata.yaml"
    assert surgery_paths["animal_b"] == dataset_root / "animal_b" / "surgery_metadata.yaml"


def test_dataset_data_animals_returns_unique_sorted_ids(tmp_path: Path) -> None:
    """Verifies that the animals property exposes one DatasetAnimal per unique animal in sorted order."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_b"),
        DatasetSession(session="2024-01-15-12-30-45-000002", animal="animal_a"),
        DatasetSession(session="2024-01-15-12-30-45-000003", animal="animal_b"),
    )
    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    animal_ids = tuple(animal.animal for animal in dataset_data.animals)
    assert animal_ids == ("animal_a", "animal_b")


def test_dataset_data_get_sessions_for_animal(tmp_path: Path) -> None:
    """Verifies that get_sessions_for_animal returns only sessions belonging to the requested animal."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
        DatasetSession(session="2024-01-15-12-30-45-000002", animal="animal_b"),
        DatasetSession(session="2024-01-15-12-30-45-000003", animal="animal_a"),
    )
    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    animal_a_sessions = dataset_data.get_sessions_for_animal(animal="animal_a")

    assert len(animal_a_sessions) == 2
    assert all(session.animal == "animal_a" for session in animal_a_sessions)


def test_dataset_data_get_session_found(tmp_path: Path) -> None:
    """Verifies that get_session() returns the DatasetSession matching the specified animal and session."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
        DatasetSession(session="2024-01-15-12-30-45-000002", animal="animal_b"),
    )
    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    found = dataset_data.get_session(animal="animal_a", session="2024-01-15-12-30-45-000001")

    assert found.animal == "animal_a"
    assert found.session == "2024-01-15-12-30-45-000001"


def test_dataset_data_get_session_not_found(tmp_path: Path) -> None:
    """Verifies that get_session() raises ValueError when the animal/session pair is not in the dataset."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    with pytest.raises(ValueError, match="must exist in the 'test_dataset' dataset"):
        dataset_data.get_session(animal="animal_z", session="2024-01-15-12-30-45-999999")


# Tests for the per-dataset column-descriptions feather


def _make_dataset(tmp_path: Path, descriptions: dict[str, str]) -> DatasetData:
    """Creates a minimal single-session dataset carrying the provided column descriptions."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    return DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=descriptions,
    )


def test_dataset_data_create_writes_descriptions_feather(tmp_path: Path) -> None:
    """Verifies that create() writes the per-dataset data_descriptions.feather at the dataset root."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)

    descriptions_path = tmp_path / "test_dataset" / DatasetFiles.DESCRIPTIONS
    assert descriptions_path.is_file()
    assert dataset_data.descriptions_path == descriptions_path


def test_dataset_data_column_descriptions_roundtrip(tmp_path: Path) -> None:
    """Verifies that column_descriptions() reads back exactly what create() wrote, surviving a reload."""
    _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)

    loaded = DatasetData.load(dataset_path=tmp_path / "test_dataset")
    assert loaded.column_descriptions() == COLUMN_DESCRIPTIONS


def test_dataset_data_column_descriptions_accepts_empty_mapping(tmp_path: Path) -> None:
    """Verifies that an empty descriptions mapping round-trips to an empty dict (explicit-schema feather)."""
    _make_dataset(tmp_path, {})

    loaded = DatasetData.load(dataset_path=tmp_path / "test_dataset")
    assert loaded.column_descriptions() == {}


def test_dataset_data_get_column_description_hit(tmp_path: Path) -> None:
    """Verifies that get_column_description() returns the description for a known column."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)

    assert dataset_data.get_column_description("lick") == COLUMN_DESCRIPTIONS["lick"]


def test_dataset_data_get_column_description_miss(tmp_path: Path) -> None:
    """Verifies that get_column_description() raises ValueError for an undescribed column."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)

    with pytest.raises(ValueError, match="must be described"):
        dataset_data.get_column_description("not_a_real_column")


def test_dataset_data_column_descriptions_errors_when_feather_missing(tmp_path: Path) -> None:
    """Verifies that column_descriptions() raises FileNotFoundError when the companion feather is absent."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)
    dataset_data.descriptions_path.unlink()

    with pytest.raises(FileNotFoundError, match="data_descriptions.feather"):
        dataset_data.column_descriptions()
