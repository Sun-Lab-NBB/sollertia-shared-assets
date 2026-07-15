"""Contains tests for the project-data-hierarchy assets provided by the ``data_hierarchy.project_hierarchy`` module."""

from __future__ import annotations

from pathlib import Path

from sollertia_shared_assets.enums import SessionTypes, AcquisitionSystems
from sollertia_shared_assets.configuration import CONFIGURATION_DIRECTORY
from sollertia_shared_assets.data_hierarchy import (
    RAW_DATA_DIRECTORY,
    DATASET_MARKER_FILENAME,
    PERSISTENT_DATA_DIRECTORY,
    AnimalData,
    ProjectData,
    SessionData,
    discover_projects,
    iter_project_animals,
)

_LOCAL_ROOT: Path = Path("/data/local")
"""Sentinel local data root used by the path-resolution tests; never touched on disk."""

_NAS_ROOT: Path = Path("/mnt/nas")
"""Sentinel NAS storage root used by the multi-root resolution tests; never touched on disk."""

_SERVER_ROOT: Path = Path("/mnt/server")
"""Sentinel server storage root used by the multi-root resolution tests; never touched on disk."""


def _write_session_marker(root: Path, project_name: str, animal_id: str, session_name: str) -> None:
    """Writes a ``session_data.yaml`` marker for the given identity under the data root."""
    raw_data_path = root.joinpath(project_name, animal_id, session_name, RAW_DATA_DIRECTORY)
    raw_data_path.mkdir(parents=True, exist_ok=True)
    SessionData(
        project_name=project_name,
        animal_id=animal_id,
        session_name=session_name,
        session_type=SessionTypes.LICK_TRAINING,
        acquisition_system=AcquisitionSystems.MESOSCOPE_VR,
        raw_data_path=raw_data_path,
    ).save()


def test_project_data_path_resolution() -> None:
    """Verifies that ProjectData resolves the project and configuration directory paths under the root."""
    project = ProjectData(root=_LOCAL_ROOT, project_name="alpha")

    assert project.path == _LOCAL_ROOT / "alpha"
    assert project.configuration_directory == _LOCAL_ROOT / "alpha" / CONFIGURATION_DIRECTORY


def test_project_data_animal_and_for_root() -> None:
    """Verifies that ProjectData builds AnimalData views and rebinds onto a different root."""
    project = ProjectData(root=_LOCAL_ROOT, project_name="alpha")

    animal = project.animal(animal_id="mouse1")
    assert animal == AnimalData(root=_LOCAL_ROOT, project_name="alpha", animal_id="mouse1")

    rebound = project.for_root(root=_NAS_ROOT)
    assert rebound == ProjectData(root=_NAS_ROOT, project_name="alpha")


def test_project_data_experiment_configs(tmp_path: Path) -> None:
    """Verifies that experiment_configs returns the sorted YAML paths and an empty tuple without the directory."""
    project = ProjectData(root=tmp_path, project_name="alpha")
    assert project.experiment_configs() == ()

    project.configuration_directory.mkdir(parents=True)
    second = project.configuration_directory / "second.yaml"
    first = project.configuration_directory / "first.yaml"
    second.write_text("a")
    first.write_text("b")

    assert project.experiment_configs() == (first, second)


def test_project_data_experiment_configs_natural_order(tmp_path: Path) -> None:
    """Verifies that experiment_configs orders numeric-suffixed names naturally rather than lexicographically."""
    project = ProjectData(root=tmp_path, project_name="alpha")
    project.configuration_directory.mkdir(parents=True)
    for name in ("experiment_1", "experiment_2", "experiment_10"):
        (project.configuration_directory / f"{name}.yaml").write_text("a")

    # Natural sort keeps experiment_10 last; a plain lexicographic sort would place it before experiment_2.
    assert [path.stem for path in project.experiment_configs()] == ["experiment_1", "experiment_2", "experiment_10"]


def test_project_data_exists(tmp_path: Path) -> None:
    """Verifies that exists reflects the presence of the project directory on disk."""
    project = ProjectData(root=tmp_path, project_name="alpha")
    assert not project.exists()

    project.path.mkdir(parents=True)
    assert project.exists()


def test_project_data_create(tmp_path: Path) -> None:
    """Verifies that create materializes the project configuration directory, returns self, and is idempotent."""
    project = ProjectData(root=tmp_path, project_name="alpha")
    assert not project.exists()

    returned = project.create()

    assert returned is project
    assert project.configuration_directory.is_dir()
    assert project.exists()

    # Calling create again leaves the existing directories untouched.
    project.create()
    assert project.configuration_directory.is_dir()


def test_animal_data_path_resolution() -> None:
    """Verifies that AnimalData resolves the animal, persistent-data, and session paths under the root."""
    animal = AnimalData(root=_LOCAL_ROOT, project_name="alpha", animal_id="mouse1")

    assert animal.path == _LOCAL_ROOT / "alpha" / "mouse1"
    assert animal.persistent_data_path == _LOCAL_ROOT / "alpha" / "mouse1" / PERSISTENT_DATA_DIRECTORY
    assert animal.session_path(session_name="s1") == _LOCAL_ROOT / "alpha" / "mouse1" / "s1"
    assert animal.project == ProjectData(root=_LOCAL_ROOT, project_name="alpha")


def test_animal_data_for_root() -> None:
    """Verifies that AnimalData rebinds the same project and animal onto a different root."""
    animal = AnimalData(root=_LOCAL_ROOT, project_name="alpha", animal_id="mouse1")

    rebound = animal.for_root(root=_SERVER_ROOT)
    assert rebound == AnimalData(root=_SERVER_ROOT, project_name="alpha", animal_id="mouse1")
    assert rebound.session_path(session_name="s1") == _SERVER_ROOT / "alpha" / "mouse1" / "s1"


def test_animal_data_exists(tmp_path: Path) -> None:
    """Verifies that exists reflects the presence of the animal directory on disk."""
    animal = AnimalData(root=tmp_path, project_name="alpha", animal_id="mouse1")
    assert not animal.exists()

    animal.path.mkdir(parents=True)
    assert animal.exists()


def test_discover_projects_markers_strategy(tmp_path: Path) -> None:
    """Verifies that the markers strategy buckets projects by SessionData identity and ignores stray directories."""
    _write_session_marker(root=tmp_path, project_name="beta", animal_id="mouse1", session_name="s1")
    _write_session_marker(root=tmp_path, project_name="alpha", animal_id="mouse2", session_name="s2")
    tmp_path.joinpath("stray_directory").mkdir()

    projects = discover_projects(root_path=tmp_path, strategy="markers")

    assert [project.project_name for project in projects] == ["alpha", "beta"]
    assert all(project.root == tmp_path for project in projects)


def test_discover_projects_directories_strategy(tmp_path: Path) -> None:
    """Verifies that the directories strategy lists project directories, including those without sessions."""
    tmp_path.joinpath("alpha").mkdir()
    tmp_path.joinpath("beta").mkdir()
    tmp_path.joinpath(".hidden").mkdir()

    projects = discover_projects(root_path=tmp_path, strategy="directories")

    assert [project.project_name for project in projects] == ["alpha", "beta"]


def test_discover_projects_directories_strategy_missing_root_returns_empty(tmp_path: Path) -> None:
    """Verifies that the directories strategy returns an empty list when the data root does not exist."""
    missing_root = tmp_path / "does_not_exist"

    assert discover_projects(root_path=missing_root, strategy="directories") == []


def test_iter_project_animals_excludes_non_animal_directories(tmp_path: Path) -> None:
    """Verifies that animal iteration skips the configuration directory, dataset directories, and hidden ones."""
    project = ProjectData(root=tmp_path, project_name="alpha")
    project.path.mkdir(parents=True)
    project.path.joinpath("mouse1").mkdir()
    project.path.joinpath("mouse2").mkdir()
    project.configuration_directory.mkdir()
    project.path.joinpath(".hidden").mkdir()
    dataset_directory = project.path.joinpath("dataset_one")
    dataset_directory.mkdir()
    dataset_directory.joinpath(DATASET_MARKER_FILENAME).write_text("marker")

    animals = list(iter_project_animals(project=project))

    assert [animal.animal_id for animal in animals] == ["mouse1", "mouse2"]


def test_iter_project_animals_missing_project_directory_yields_nothing(tmp_path: Path) -> None:
    """Verifies that animal iteration yields nothing when the project directory does not exist."""
    project = ProjectData(root=tmp_path, project_name="ghost")

    assert list(iter_project_animals(project=project)) == []


def test_iter_project_animals_skips_non_directory_children(tmp_path: Path) -> None:
    """Verifies that animal iteration skips regular files among the project's children."""
    project = ProjectData(root=tmp_path, project_name="alpha")
    project.path.mkdir(parents=True)
    project.path.joinpath("mouse1").mkdir()
    project.path.joinpath("stray_file.txt").write_text("not an animal")

    animals = list(iter_project_animals(project=project))

    assert [animal.animal_id for animal in animals] == ["mouse1"]


def test_iter_project_animals_orders_numeric_ids_naturally(tmp_path: Path) -> None:
    """Verifies that animal iteration orders purely numeric animal IDs naturally rather than lexicographically."""
    project = ProjectData(root=tmp_path, project_name="alpha")
    project.path.mkdir(parents=True)
    for animal_id in ("1", "2", "9", "10"):
        project.path.joinpath(animal_id).mkdir()

    animals = list(iter_project_animals(project=project))

    # Natural sort keeps "10" last; a plain lexicographic sort would place it right after "1".
    assert [animal.animal_id for animal in animals] == ["1", "2", "9", "10"]
