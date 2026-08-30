"""Contains tests for the DatasetData, DatasetSession, and DatasetAnimal dataclasses housed in
sollertia_shared_assets.data_hierarchy.dataset_data.
"""

import shutil
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
from sollertia_shared_assets.data_hierarchy import dataset_data as dataset_data_module

# A representative column-description binding, passed to nearly every create() call. The empty-mapping test and the
# two invalid-mapping tests pass their own mappings instead. The mapping is intentionally small. The real mapping is
# donated by the acquisition-system packages, alongside the assembly worker whose columns it describes.
COLUMN_DESCRIPTIONS: dict[str, str] = {
    "time_us": "Microsecond-precision sample timestamps from the acquisition reference clock.",
    "lick": "Lick sensor state at each sample.",
}

# Tests for DatasetSession dataclass


def test_dataset_session_default_initialization() -> None:
    """Verifies that DatasetSession.session_path defaults to an empty Path()."""
    dataset_session = DatasetSession(session="2024-01-15-12-30-45-123456", animal="test_animal")

    assert dataset_session.session == "2024-01-15-12-30-45-123456"
    assert dataset_session.animal == "test_animal"
    assert dataset_session.session_path == Path()


def test_dataset_session_is_frozen() -> None:
    """Verifies that DatasetSession instances are immutable."""
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


@pytest.mark.parametrize("corrupt_value", [None, 5, ["lick training"]])
def test_dataset_data_post_init_rejects_values_outside_the_vocabulary(corrupt_value: object) -> None:
    """Verifies that __post_init__ rejects a session_type outside the platform vocabulary rather than storing it."""
    with pytest.raises(ValueError, match="is not a valid SessionTypes"):
        DatasetData(
            name="test_dataset",
            project="test_project",
            session_type=corrupt_value,  # type: ignore[arg-type]
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        )


def test_dataset_data_post_init_preserves_enum_members() -> None:
    """Verifies that __post_init__ leaves a session_type and an acquisition_system that are already enum members
    unchanged."""
    dataset_data = DatasetData(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
    )

    assert dataset_data.session_type is SessionTypes.LICK_TRAINING
    assert dataset_data.acquisition_system is AcquisitionSystems.MESOSCOPE_VR


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


def test_dataset_data_create_materializes_a_lazy_sessions_iterable(tmp_path: Path) -> None:
    """Verifies that create() materializes a generator before the screens read it, so every yielded session lands in
    the hierarchy."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
        DatasetSession(session="2024-01-16-09-15-22-654321", animal="animal_b"),
    )

    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=(session for session in sessions),  # type: ignore[arg-type]
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    dataset_root = tmp_path / "test_dataset"
    assert len(dataset_data.sessions) == 2
    assert (dataset_root / "animal_a" / "2024-01-15-12-30-45-123456").is_dir()
    assert (dataset_root / "animal_b" / "2024-01-16-09-15-22-654321").is_dir()


def test_dataset_data_create_rejects_an_empty_lazy_sessions_iterable(tmp_path: Path) -> None:
    """Verifies that create() rejects a generator that yields nothing instead of persisting a session-less dataset."""
    with pytest.raises(ValueError, match="at least one"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=(session for session in ()),  # type: ignore[arg-type]
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("corrupt_name", ["", ".", "..", "nested/dataset", "trailing/"])
def test_dataset_data_create_rejects_a_name_outside_one_directory(corrupt_name: str, tmp_path: Path) -> None:
    """Verifies that create() rejects a dataset name that does not resolve to a single directory under the root."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),)

    with pytest.raises(ValueError, match="The name must be a non-empty string naming a single directory"):
        DatasetData.create(
            name=corrupt_name,
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "animal, session",
    [
        ("", "2024-01-15-12-30-45-123456"),
        (".", "2024-01-15-12-30-45-123456"),
        ("..", "2024-01-15-12-30-45-123456"),
        ("nested/animal", "2024-01-15-12-30-45-123456"),
        ("/absolute", "2024-01-15-12-30-45-123456"),
        ("animal_a", ""),
        ("animal_a", "../escape"),
    ],
)
def test_dataset_data_create_rejects_identifiers_outside_one_directory(
    animal: str,
    session: str,
    tmp_path: Path,
) -> None:
    """Verifies that create() rejects an animal or session identifier that does not name a single directory."""
    with pytest.raises(ValueError, match="Every animal and session identifier"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=(DatasetSession(session=session, animal=animal),),
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert list(tmp_path.iterdir()) == []


def test_dataset_data_create_names_every_invalid_identifier(tmp_path: Path) -> None:
    """Verifies that create() reports every offending identifier in one error rather than aborting on the first."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="../escape"),
        DatasetSession(session="nested/session", animal="animal_b"),
    )

    with pytest.raises(ValueError, match=r"'\.\./escape',\s+'nested/session'"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("corrupt_value", [None, 5, "bogus", ["lick training"]])
def test_dataset_data_create_rejects_session_type_outside_the_vocabulary(
    corrupt_value: object,
    tmp_path: Path,
) -> None:
    """Verifies that create() rejects a session_type outside the platform vocabulary before it creates any
    directory."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),)

    with pytest.raises(ValueError, match="must be one of the SessionTypes"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=corrupt_value,  # type: ignore[arg-type]
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("corrupt_value", [None, 5, "bogus", ["mesoscope"]])
def test_dataset_data_create_rejects_acquisition_system_outside_the_vocabulary(
    corrupt_value: object,
    tmp_path: Path,
) -> None:
    """Verifies that create() rejects an acquisition_system outside the platform vocabulary before it creates any
    directory."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),)

    with pytest.raises(ValueError, match="must be one of the AcquisitionSystems"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=corrupt_value,  # type: ignore[arg-type]
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
        )

    assert list(tmp_path.iterdir()) == []


def test_dataset_data_create_retries_under_the_same_name_after_a_vocabulary_rejection(tmp_path: Path) -> None:
    """Verifies that a create() call rejected for its vocabulary releases the dataset name, so the corrected retry
    completes instead of failing as an already-existing dataset."""
    sessions = (
        DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
        DatasetSession(session="2024-01-16-09-15-22-123456", animal="animal_b"),
    )

    with pytest.raises(ValueError, match="Unable to create the 'test_dataset' forged dataset"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type="bogus",
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=COLUMN_DESCRIPTIONS,
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

    # The retry reuses the rejected request's name, so a completed hierarchy is what proves the rejected request left
    # the datasets root untouched.
    dataset_root = tmp_path / "test_dataset"
    assert dataset_data.session_type is SessionTypes.LICK_TRAINING
    assert (dataset_root / "dataset.yaml").is_file()
    assert (dataset_root / DatasetFiles.DESCRIPTIONS).is_file()
    assert (dataset_root / "animal_a" / "2024-01-15-12-30-45-123456").is_dir()
    assert (dataset_root / "animal_b" / "2024-01-16-09-15-22-123456").is_dir()


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
    real_save = DatasetData.save
    companion_present: list[bool] = []

    def _record_save(self):
        """Records whether the descriptions companion is already on disk when the marker write starts."""
        companion_present.append(self.descriptions_path.is_file())
        real_save(self)

    monkeypatch.setattr(DatasetData, "save", _record_save)

    dataset_data = DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=(DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),),
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )

    # The marker is what makes a dataset discoverable, so publishing it last is what keeps every discoverable dataset
    # one whose column_descriptions() resolves. The ordering is observed directly, since a creation interrupted before
    # the marker write now rolls the whole hierarchy back and leaves nothing to inspect afterwards.
    assert companion_present == [True]
    assert dataset_data.dataset_data_path.is_file()


@pytest.mark.parametrize(
    "corrupt_descriptions",
    [
        {"time_us": None},
        {"time_us": 5},
        {"time_us": ""},
        {"": "Microsecond-precision sample timestamps."},
        {5: "Microsecond-precision sample timestamps."},
        {("time_us",): "Microsecond-precision sample timestamps."},
    ],
)
def test_dataset_data_create_rejects_invalid_column_descriptions(
    corrupt_descriptions: dict[str, str],
    tmp_path: Path,
) -> None:
    """Verifies that create() rejects a column_descriptions entry that does not bind two non-empty strings."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),)

    with pytest.raises(ValueError, match="Every column_descriptions entry must bind a non-empty string"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=corrupt_descriptions,
        )

    # The mapping is the dataset's permanent interpretation contract, so a rejected mapping must not leave a dataset
    # that would carry a null or a partial one forever.
    assert list(tmp_path.iterdir()) == []


def test_dataset_data_create_names_every_invalid_column_description(tmp_path: Path) -> None:
    """Verifies that create() reports every offending column_descriptions entry in one error."""
    sessions = (DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),)
    corrupt_descriptions = {
        "time_us": None,
        "lick": "",
        "valve": 5,
        "torque": "Torque sensor readout at each sample.",
    }

    with pytest.raises(ValueError, match=r"'lick',\s+'time_us',\s+'valve'"):
        DatasetData.create(
            name="test_dataset",
            project="test_project",
            session_type=SessionTypes.LICK_TRAINING,
            acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
            sessions=sessions,
            datasets_root=tmp_path,
            column_descriptions=corrupt_descriptions,  # type: ignore[arg-type]
        )

    assert list(tmp_path.iterdir()) == []


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


# Tests for the transactional guarantee of create()


def _fail_descriptions(self, column_descriptions):
    """Fails the descriptions write, standing in for a failure partway through create()."""
    message = "simulated descriptions write failure"
    raise OSError(message)


def _fail_save(self):
    """Fails the marker write, standing in for a full disk, a read-only mount, or a revoked permission."""
    message = "simulated marker write failure"
    raise OSError(message)


def _interrupt_save(self):
    """Interrupts the marker write, standing in for a Ctrl-C landing inside a mutation."""
    raise KeyboardInterrupt


def _leave_directory(directory_path):
    """Stands in for a delete_directory() call that exhausts its attempts and leaves the directory in place."""


def _fail_delete(directory_path):
    """Stands in for a delete_directory() call that cannot read the tree it is asked to remove."""
    message = "simulated rollback failure"
    raise OSError(message)


def _make_failing_directory_creator(failing_call: int):
    """Returns an ensure_directory_exists() stand-in that fails on the requested call and delegates on every other."""
    real_creator = dataset_data_module.ensure_directory_exists
    calls: list[Path] = []

    def _create(path, is_file):
        """Creates the directory unless this is the call the test asked to fail."""
        calls.append(path)
        if len(calls) == failing_call:
            message = "simulated directory creation failure"
            raise OSError(message)
        real_creator(path=path, is_file=is_file)

    return _create


def _create_rollback_dataset(tmp_path: Path) -> DatasetData:
    """Creates the two-animal dataset every rollback test builds, so the retries repeat an identical request."""
    return DatasetData.create(
        name="test_dataset",
        project="test_project",
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        sessions=(
            DatasetSession(session="2024-01-15-12-30-45-123456", animal="animal_a"),
            DatasetSession(session="2024-01-16-09-15-22-654321", animal="animal_b"),
        ),
        datasets_root=tmp_path,
        column_descriptions=COLUMN_DESCRIPTIONS,
    )


def test_dataset_data_create_rolls_back_when_the_descriptions_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a descriptions write failure removes the hierarchy and releases the dataset name."""
    monkeypatch.setattr(DatasetData, "_write_column_descriptions", _fail_descriptions)

    with pytest.raises(OSError, match="simulated descriptions write failure"):
        _create_rollback_dataset(tmp_path)

    assert list(tmp_path.iterdir()) == []

    # The identical request is what proves the name was released, since create() refuses an existing destination.
    monkeypatch.undo()
    dataset_data = _create_rollback_dataset(tmp_path)
    assert dataset_data.dataset_data_path.is_file()
    assert dataset_data.descriptions_path.is_file()


def test_dataset_data_create_rolls_back_when_a_session_directory_cannot_be_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a session directory the filesystem refuses removes the dataset root created before it."""
    # The second call is the first per-session directory, so the dataset root is already on disk when it fails.
    monkeypatch.setattr(dataset_data_module, "ensure_directory_exists", _make_failing_directory_creator(2))

    with pytest.raises(OSError, match="simulated directory creation failure"):
        _create_rollback_dataset(tmp_path)

    assert list(tmp_path.iterdir()) == []

    monkeypatch.undo()
    assert _create_rollback_dataset(tmp_path).dataset_data_path.is_file()


def test_dataset_data_create_rolls_back_when_the_marker_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a marker write failure removes the whole hierarchy, companion feather included."""
    monkeypatch.setattr(DatasetData, "save", _fail_save)

    with pytest.raises(OSError, match="simulated marker write failure"):
        _create_rollback_dataset(tmp_path)

    assert list(tmp_path.iterdir()) == []

    monkeypatch.undo()
    assert _create_rollback_dataset(tmp_path).dataset_data_path.is_file()


def test_dataset_data_create_rolls_back_on_an_interrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a Ctrl-C landing inside create() removes the hierarchy and re-raises the interruption."""
    monkeypatch.setattr(DatasetData, "save", _interrupt_save)

    with pytest.raises(KeyboardInterrupt):
        _create_rollback_dataset(tmp_path)

    assert list(tmp_path.iterdir()) == []

    monkeypatch.undo()
    assert _create_rollback_dataset(tmp_path).dataset_data_path.is_file()


def test_dataset_data_create_skips_the_rollback_when_no_directory_was_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() attempts no removal when the dataset root directory never came to be."""
    removals: list[Path] = []

    def _record_removal(directory_path):
        """Records every removal the rollback attempts."""
        removals.append(directory_path)

    monkeypatch.setattr(dataset_data_module, "ensure_directory_exists", _make_failing_directory_creator(1))
    monkeypatch.setattr(dataset_data_module, "delete_directory", _record_removal)

    with pytest.raises(OSError, match="simulated directory creation failure"):
        _create_rollback_dataset(tmp_path)

    # A rollback that runs unconditionally would target a path this call never claimed, which is what admits a
    # dangling symlink at the destination being unlinked by a creation that never touched it.
    assert removals == []
    assert list(tmp_path.iterdir()) == []


def test_dataset_data_create_leaves_a_colliding_dataset_intact(tmp_path: Path) -> None:
    """Verifies that a request colliding with an existing dataset leaves that dataset untouched."""
    existing = _create_rollback_dataset(tmp_path)
    (existing.dataset_data_path.parent / "animal_a" / "2024-01-15-12-30-45-123456" / "data.feather").write_bytes(
        b"payload"
    )

    with pytest.raises(FileExistsError, match="must not exist"):
        _create_rollback_dataset(tmp_path)

    # Every screen runs outside the rollback, so a rejected request never removes the dataset it collided with.
    reloaded = DatasetData.load(dataset_path=tmp_path / "test_dataset")
    assert len(reloaded.sessions) == 2
    assert reloaded.get_session(animal="animal_a", session="2024-01-15-12-30-45-123456").data_path.is_file()


def test_dataset_data_create_reports_a_rollback_that_leaves_the_hierarchy_behind(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that create() raises when the rollback returns with the hierarchy still on disk."""
    monkeypatch.setattr(DatasetData, "save", _fail_save)
    monkeypatch.setattr(dataset_data_module, "delete_directory", _leave_directory)

    with pytest.raises(RuntimeError, match="partially created hierarchy must be removed"):
        _create_rollback_dataset(tmp_path)

    # delete_directory reports an exhausted removal as a warning on a console that is disabled by default, so the
    # surviving hierarchy has to be raised or it goes unreported.
    assert (tmp_path / "test_dataset").is_dir()


def test_dataset_data_create_reports_a_rollback_that_cannot_remove_the_hierarchy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that an OSError raised by the rollback itself is reported as the surviving hierarchy it leaves."""
    monkeypatch.setattr(DatasetData, "save", _fail_save)
    monkeypatch.setattr(dataset_data_module, "delete_directory", _fail_delete)

    with pytest.raises(RuntimeError, match="partially created hierarchy must be removed"):
        _create_rollback_dataset(tmp_path)

    assert (tmp_path / "test_dataset").is_dir()


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


def test_dataset_data_add_sessions_materializes_a_lazy_sessions_iterable(tmp_path: Path) -> None:
    """Verifies that add_sessions() materializes a generator before the screens read it."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )
    requested = (DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),)

    added = dataset_data.add_sessions(sessions=(session for session in requested))  # type: ignore[arg-type]

    assert len(added) == 1
    assert added[0].session_path.is_dir()
    assert len(dataset_data.sessions) == 2


def test_dataset_data_add_sessions_rejects_an_empty_lazy_sessions_iterable(tmp_path: Path) -> None:
    """Verifies that add_sessions() rejects a generator that yields nothing instead of rewriting the marker."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    with pytest.raises(ValueError, match="at least one"):
        dataset_data.add_sessions(sessions=(session for session in ()))  # type: ignore[arg-type]

    assert len(dataset_data.sessions) == 1


def test_dataset_data_add_sessions_rejects_identifiers_outside_one_directory(tmp_path: Path) -> None:
    """Verifies that add_sessions() rejects an identifier that does not name a single directory."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )

    escaping = (DatasetSession(session="2024-01-16-09-15-22-000002", animal="../escape"),)

    with pytest.raises(ValueError, match="Every animal and session identifier"):
        dataset_data.add_sessions(sessions=escaping)

    assert list((tmp_path / "test_dataset").parent.iterdir()) == [tmp_path / "test_dataset"]
    assert len(dataset_data.sessions) == 1


def test_dataset_data_add_sessions_removes_directories_when_a_later_session_cannot_be_created(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a session directory the filesystem refuses removes the directories the same call created."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )
    dataset_root = tmp_path / "test_dataset"

    # The second call is the second requested session, so the first session's directories are already on disk.
    monkeypatch.setattr(dataset_data_module, "ensure_directory_exists", _make_failing_directory_creator(2))

    with pytest.raises(OSError, match="simulated directory creation failure"):
        dataset_data.add_sessions(
            sessions=(
                DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
                DatasetSession(session="2024-01-17-09-15-22-000003", animal="animal_c"),
            )
        )

    assert not (dataset_root / "animal_b").exists()
    assert not (dataset_root / "animal_c").exists()
    assert (dataset_root / "animal_a" / "2024-01-15-12-30-45-000001").is_dir()
    assert len(dataset_data.sessions) == 1


def test_dataset_data_add_sessions_restores_sessions_when_the_marker_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a failed marker write restores the instance's session list and removes the created directories."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )
    dataset_root = tmp_path / "test_dataset"
    request = (DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),)

    monkeypatch.setattr(DatasetData, "save", _fail_save)

    with pytest.raises(OSError, match="simulated marker write failure"):
        dataset_data.add_sessions(sessions=request)

    assert len(dataset_data.sessions) == 1
    assert not (dataset_root / "animal_b").exists()
    assert {session.session for session in DatasetData.load(dataset_path=dataset_root).sessions} == {
        "2024-01-15-12-30-45-000001"
    }

    # The identical request is what proves the instance is retryable, since a session left in the instance's list
    # would be refused as a duplicate.
    monkeypatch.undo()
    dataset_data.add_sessions(sessions=request)
    assert len(dataset_data.sessions) == 2
    assert (dataset_root / "animal_b" / "2024-01-16-09-15-22-000002").is_dir()


def test_dataset_data_add_sessions_restores_sessions_when_the_marker_write_is_interrupted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a Ctrl-C landing inside the marker write restores the instance's session list and the tree."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )
    dataset_root = tmp_path / "test_dataset"
    request = (DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),)

    monkeypatch.setattr(DatasetData, "save", _interrupt_save)

    with pytest.raises(KeyboardInterrupt):
        dataset_data.add_sessions(sessions=request)

    assert len(dataset_data.sessions) == 1
    assert not (dataset_root / "animal_b").exists()

    monkeypatch.undo()
    dataset_data.add_sessions(sessions=request)
    assert len(dataset_data.sessions) == 2


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


def test_dataset_data_remove_animal_tolerates_missing_animal_directory(tmp_path: Path) -> None:
    """Verifies that remove_animal() drops the animal from the marker when its directory is already absent."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path,
        (
            DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
            DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
        ),
    )
    dataset_root = tmp_path / "test_dataset"

    # Reproduces a removal interrupted after the directory tree was cleared but before the marker was rewritten.
    shutil.rmtree(dataset_root / "animal_a")

    removed = dataset_data.remove_animal(animal="animal_a")

    assert {session.session for session in removed} == {"2024-01-15-12-30-45-000001"}
    assert (dataset_root / "animal_b" / "2024-01-16-09-15-22-000002").is_dir()

    reloaded = DatasetData.load(dataset_path=dataset_root)
    assert tuple(animal.animal for animal in reloaded.animals) == ("animal_b",)


def test_dataset_data_remove_animal_reports_a_directory_that_survives_the_removal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that remove_animal() raises, instead of rewriting the marker, when the directory survives."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path,
        (
            DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
            DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
        ),
    )
    dataset_root = tmp_path / "test_dataset"

    monkeypatch.setattr(dataset_data_module, "delete_directory", _leave_directory)

    with pytest.raises(RuntimeError, match=r"directory must no longer\s+exist"):
        dataset_data.remove_animal(animal="animal_a")

    # Dropping the animal from the marker while its data survives is the exact state the removal ordering exists to
    # prevent, so the marker keeps describing the tree that is still on disk.
    assert (dataset_root / "animal_a").is_dir()
    assert len(dataset_data.sessions) == 2
    assert tuple(animal.animal for animal in DatasetData.load(dataset_path=dataset_root).animals) == (
        "animal_a",
        "animal_b",
    )


def test_dataset_data_remove_animal_rejects_an_identifier_outside_one_directory(tmp_path: Path) -> None:
    """Verifies that remove_animal() refuses an identifier that resolves outside the animal's own directory."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path, (DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),)
    )
    dataset_root = tmp_path / "test_dataset"

    # Reproduces a marker written before the creation-time screen existed, whose animal identifier joins onto the
    # dataset root itself rather than onto a directory under it.
    dataset_data.sessions = (DatasetSession(session="2024-01-15-12-30-45-000001", animal=""),)

    with pytest.raises(ValueError, match="The animal identifier must be a non-empty string"):
        dataset_data.remove_animal(animal="")

    assert (dataset_root / "dataset.yaml").is_file()
    assert (dataset_root / DatasetFiles.DESCRIPTIONS).is_file()
    assert (dataset_root / "animal_a" / "2024-01-15-12-30-45-000001").is_dir()


def test_dataset_data_remove_animal_restores_sessions_when_the_marker_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that a failed marker write restores the instance's session list, so the removal can be retried."""
    dataset_data = _make_hierarchy_dataset(
        tmp_path,
        (
            DatasetSession(session="2024-01-15-12-30-45-000001", animal="animal_a"),
            DatasetSession(session="2024-01-16-09-15-22-000002", animal="animal_b"),
        ),
    )
    dataset_root = tmp_path / "test_dataset"

    monkeypatch.setattr(DatasetData, "save", _fail_save)

    with pytest.raises(OSError, match="simulated marker write failure"):
        dataset_data.remove_animal(animal="animal_a")

    assert len(dataset_data.sessions) == 2

    # The identical call is what proves the instance is retryable, since an animal already dropped from the instance's
    # list would be refused as one the dataset does not hold.
    monkeypatch.undo()
    removed = dataset_data.remove_animal(animal="animal_a")

    assert {session.session for session in removed} == {"2024-01-15-12-30-45-000001"}
    assert tuple(animal.animal for animal in DatasetData.load(dataset_path=dataset_root).animals) == ("animal_b",)


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
    # Emits only a subset of the described columns. The unused 'lick' description must not trigger a violation.
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
