"""Contains tests for the DatasetData, DatasetSession, and DatasetAnimal dataclasses housed in
sollertia_shared_assets.data_hierarchy.dataset_data.
"""

from pathlib import Path

import polars as pl
import pytest

from sollertia_shared_assets import (
    DatasetData,
    DatasetFiles,
    SessionTypes,
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
    """Verifies that the data, descriptor, and re-exported configuration paths resolve relative to session_path."""
    session_path = Path("/tmp/test_dataset/animal_a/2024-01-15-12-30-45-123456")
    dataset_session = DatasetSession(
        session="2024-01-15-12-30-45-123456",
        animal="animal_a",
        session_path=session_path,
    )

    assert dataset_session.data_path == session_path / "data.feather"
    assert dataset_session.descriptor_path == session_path / "session_descriptor.yaml"
    assert dataset_session.vr_configuration_path == session_path / "vr_configuration.yaml"
    assert dataset_session.experiment_configuration_path == session_path / "experiment_configuration.yaml"


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


def test_dataset_data_create_rejects_session_repeated_in_request(tmp_path: Path) -> None:
    """Verifies that create() rejects a tuple naming the same animal and session twice."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
    )

    with pytest.raises(ValueError, match="animal_a/2024-01-15-12-30-45-123456"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert not (tmp_path / "test_dataset").exists()


def test_dataset_data_create_rejects_session_repeated_in_set(tmp_path: Path) -> None:
    """Verifies that create() rejects a set whose entries name one animal and session under different paths."""
    sessions = {
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a", session_path=Path("/first")),
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a", session_path=Path("/second")),
    }

    # The session_path field participates in the frozen dataclass hash, so the set keeps both entries and the identity
    # screen is the only thing standing between the request and a dataset that counts the session twice.
    assert len(sessions) == 2

    with pytest.raises(ValueError, match="animal_a/2024-01-15-12-30-45-123456"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert not (tmp_path / "test_dataset").exists()


def test_dataset_data_create_writes_marker_after_descriptions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() publishes the dataset marker only once the descriptions companion is on disk."""
    failure = OSError("simulated descriptions write failure")

    def _fail_descriptions(self, column_descriptions):
        """Fails the descriptions write, standing in for an interruption partway through create()."""
        raise failure

    monkeypatch.setattr(DatasetData, "_write_column_descriptions", _fail_descriptions)

    with pytest.raises(OSError, match="simulated descriptions write failure"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=(DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),),
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    # A dataset that never received its companion feather stays undiscoverable, so no consumer loads a dataset whose
    # column_descriptions() would raise.
    assert not (tmp_path / "test_dataset" / "dataset.yaml").exists()


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


def test_dataset_data_load_falls_back_to_scanning_when_marker_is_not_canonical(tmp_path: Path) -> None:
    """Verifies that load() scans the tree when the input path is not the dataset root, so a caller pointing at the
    datasets root still resolves the single marker it holds.
    """
    DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=(DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),),
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    # The datasets root holds no 'dataset.yaml' of its own, so the canonical lookup misses and the recursive scan
    # resolves the dataset's marker instead.
    loaded = DatasetData.load(dataset_path=tmp_path)

    assert loaded.name == "test_dataset"
    assert loaded.dataset_data_path == tmp_path / "test_dataset" / "dataset.yaml"


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


def test_dataset_data_get_animal_rejects_unknown_animal(tmp_path: Path) -> None:
    """Verifies that get_animal() rejects an animal the dataset does not hold."""
    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=(DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),),
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    with pytest.raises(ValueError, match=r"Unable to look up the animal"):
        dataset_data.get_animal(animal="animal_z")


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


# Tests for the add_sessions and remove_animal hierarchy mutators


def _make_hierarchy_dataset(tmp_path: Path, sessions: tuple[DatasetSession, ...]) -> DatasetData:
    """Creates a dataset holding the provided sessions, used by the add_sessions and remove_animal tests."""
    return DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=sessions,
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )


def test_dataset_data_add_sessions_appends_and_materializes(tmp_path: Path) -> None:
    """Verifies that add_sessions() appends the sessions, creates their directories, and persists the marker."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    added = dataset_data.add_sessions(
        sessions=(DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),)
    )

    dataset_root = tmp_path / "test_dataset"
    assert len(added) == 1
    assert added[0].session_path == dataset_root / "animal_b" / "2024-01-16-09-15-22-000002"
    assert added[0].session_path.is_dir()
    assert len(dataset_data.sessions) == 2

    # The marker is rewritten in place, so a fresh load sees the appended session.
    reloaded = DatasetData.load(dataset_path=dataset_root)
    assert {session.session for session in reloaded.sessions} == {
        "2024-01-15-12-30-45-000001",
        "2024-01-16-09-15-22-000002",
    }
    assert tuple(animal.animal for animal in reloaded.animals) == ("animal_a", "animal_b")


def test_dataset_data_add_sessions_resolves_session_paths(tmp_path: Path) -> None:
    """Verifies that add_sessions() replaces the input session_path with the path inside the dataset hierarchy."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    added = dataset_data.add_sessions(
        sessions=(
            DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b", session_path=Path("/ignored")),
        )
    )

    assert added[0].session_path == tmp_path / "test_dataset" / "animal_b" / "2024-01-16-09-15-22-000002"


def test_dataset_data_add_sessions_accepts_set_of_sessions(tmp_path: Path) -> None:
    """Verifies that add_sessions() accepts a set of DatasetSession instances."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    added = dataset_data.add_sessions(
        sessions={
            DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
            DatasetSession(session="2024-01-17-09-15-22-000003", animal="animal_c"),
        }
    )

    assert len(added) == 2
    assert len(dataset_data.sessions) == 3


def test_dataset_data_add_sessions_rejects_empty_collection(tmp_path: Path) -> None:
    """Verifies that add_sessions() rejects an empty sessions collection."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    with pytest.raises(ValueError, match="at least one"):
        dataset_data.add_sessions(sessions=())


def test_dataset_data_add_sessions_rejects_session_already_in_dataset(tmp_path: Path) -> None:
    """Verifies that add_sessions() rejects a session the dataset already holds."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    with pytest.raises(ValueError, match="animal_a/2024-01-15-12-30-45-000001"):
        dataset_data.add_sessions(sessions=(DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),))


def test_dataset_data_add_sessions_rejects_session_repeated_in_request(tmp_path: Path) -> None:
    """Verifies that add_sessions() rejects a request naming the same animal and session twice."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    with pytest.raises(ValueError, match="animal_b/2024-01-16-09-15-22-000002"):
        dataset_data.add_sessions(
            sessions=(
                DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
                DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
            )
        )


def test_dataset_data_add_sessions_leaves_hierarchy_untouched_when_rejected(tmp_path: Path) -> None:
    """Verifies that a rejected add_sessions() request creates no directory for its acceptable entries."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    with pytest.raises(ValueError, match="animal_a/2024-01-15-12-30-45-000001"):
        dataset_data.add_sessions(
            sessions=(
                DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
                DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
            )
        )

    assert not (tmp_path / "test_dataset" / "animal_b").exists()
    assert len(dataset_data.sessions) == 1


def test_dataset_data_remove_animal_drops_sessions_and_directory(tmp_path: Path) -> None:
    """Verifies that remove_animal() deletes the animal's directory tree and rewrites the dataset marker."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path,
        (
            DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
            DatasetSession(session="2024-01-15-12-30-45-000002", animal="animal_a"),
            DatasetSession(session="2024-01-16-09-15-22-000003", animal="animal_b"),
        ),
    )
    dataset_root = tmp_path / "test_dataset"

    # Writes a payload into the removed animal's hierarchy to confirm the whole tree is cleared.
    (dataset_root / "animal_a" / "2024-01-15-12-30-45-000001" / "data.feather").write_bytes(b"payload")
    (dataset_root / "animal_a" / "surgery_metadata.yaml").write_text("animal: animal_a")

    removed = dataset_data.remove_animal(animal="animal_a")

    assert {session.session for session in removed} == {
        "2024-01-15-12-30-45-000001",
        "2024-01-15-12-30-45-000002",
    }
    assert not (dataset_root / "animal_a").exists()
    assert (dataset_root / "animal_b" / "2024-01-16-09-15-22-000003").is_dir()

    reloaded = DatasetData.load(dataset_path=dataset_root)
    assert tuple(animal.animal for animal in reloaded.animals) == ("animal_b",)


def test_dataset_data_remove_animal_rejects_unknown_animal(tmp_path: Path) -> None:
    """Verifies that remove_animal() rejects an animal the dataset does not hold."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    with pytest.raises(ValueError, match="must be part of the dataset"):
        dataset_data.remove_animal(animal="animal_z")

    assert (tmp_path / "test_dataset" / "animal_a").is_dir()
    assert len(dataset_data.sessions) == 1


def test_dataset_data_remove_animal_then_add_sessions_rebuilds_animal(tmp_path: Path) -> None:
    """Verifies that pairing remove_animal() with add_sessions() replaces one animal's session set."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path,
        (
            DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
            DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
        ),
    )

    dataset_data.remove_animal(animal="animal_a")
    dataset_data.add_sessions(
        sessions=(
            DatasetSession(session="2024-01-17-10-00-00-000003", animal="animal_a"),
            DatasetSession(session="2024-01-18-10-00-00-000004", animal="animal_a"),
        )
    )

    reloaded = DatasetData.load(dataset_path=tmp_path / "test_dataset")
    animal_a_sessions = {session.session for session in reloaded.get_sessions_for_animal(animal="animal_a")}

    assert animal_a_sessions == {"2024-01-17-10-00-00-000003", "2024-01-18-10-00-00-000004"}
    assert {session.session for session in reloaded.get_sessions_for_animal(animal="animal_b")} == {
        "2024-01-16-09-15-22-000002"
    }
    assert not (tmp_path / "test_dataset" / "animal_a" / "2024-01-15-12-30-45-000001").exists()


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


# Tests for verify_data_descriptions()


def _write_session_data(dataset_data: DatasetData, columns: tuple[str, ...]) -> None:
    """Writes a single-row ``data.feather`` carrying the given columns into the dataset's first session."""
    session_path = dataset_data.sessions[0].data_path
    pl.DataFrame({column: [0] for column in columns}).write_ipc(file=session_path)


def test_dataset_data_verify_data_descriptions_passes_when_all_columns_described(tmp_path: Path) -> None:
    """Verifies that verify_data_descriptions() accepts a session whose every column is described."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)
    _write_session_data(dataset_data, ("time_us", "lick"))

    dataset_data.verify_data_descriptions()


def test_dataset_data_verify_data_descriptions_allows_unused_descriptions(tmp_path: Path) -> None:
    """Verifies the check is one-directional: a described column no session emits is permitted."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)
    # Emits only a subset of the described columns; the unused 'lick' description must not trigger a violation.
    _write_session_data(dataset_data, ("time_us",))

    dataset_data.verify_data_descriptions()


def test_dataset_data_verify_data_descriptions_raises_on_undescribed_column(tmp_path: Path) -> None:
    """Verifies that verify_data_descriptions() raises ValueError naming an undescribed written column."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)
    _write_session_data(dataset_data, ("time_us", "lick", "mystery_column"))

    with pytest.raises(ValueError, match="mystery_column"):
        dataset_data.verify_data_descriptions()


def test_dataset_data_verify_data_descriptions_errors_when_session_feather_missing(tmp_path: Path) -> None:
    """Verifies that verify_data_descriptions() raises FileNotFoundError when a session's data.feather is absent."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)

    with pytest.raises(FileNotFoundError, match="data.feather"):
        dataset_data.verify_data_descriptions()


def test_dataset_data_verify_data_descriptions_errors_when_descriptions_missing(tmp_path: Path) -> None:
    """Verifies that verify_data_descriptions() surfaces a missing descriptions feather as FileNotFoundError."""
    dataset_data = _make_dataset(tmp_path, COLUMN_DESCRIPTIONS)
    _write_session_data(dataset_data, ("time_us", "lick"))
    dataset_data.descriptions_path.unlink()

    with pytest.raises(FileNotFoundError, match="data_descriptions.feather"):
        dataset_data.verify_data_descriptions()
