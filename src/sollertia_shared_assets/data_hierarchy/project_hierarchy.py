"""Provides the system-agnostic project-data-hierarchy assets shared across all Sollertia platform machines.

The assets in this module model the platform directory layout above the session level
(``<root>/<project>/<animal>/<session>``) as derived runtime aggregates that hold no on-disk markers. They
operate purely on resolved paths, so they remain agnostic to any particular acquisition or processing system,
and they can rebind the same project / animal / session subtree onto any mounted root via ``for_root``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from ..configuration import CONFIGURATION_DIRECTORY

if TYPE_CHECKING:
    from pathlib import Path

PERSISTENT_DATA_DIRECTORY: str = "persistent_data"
"""Subdirectory under each animal that holds data persisted across the animal's sessions. This directory is typically
only present on data acquisition systems."""

DATASET_MARKER_FILENAME: str = "dataset.yaml"
"""Filename of the dataset marker. Datasets are created and owned by sollertia-forgery, but their directories live
inside the project hierarchy as siblings of the animal directories. The canonical marker name is defined here so the
shared hierarchy walkers can recognize, skip, or count dataset directories without depending on sollertia-forgery."""


@dataclass(frozen=True, slots=True)
class ProjectData:
    """Resolves the on-disk locations of a single project's assets under a given data root.

    Instances are lightweight path-grammar views: they construct paths from the root and project name and do
    not require the project directory to exist on disk. Rebind the same project under a different root with
    ``for_root`` to resolve its locations on a remote storage root, or materialize the project's directory
    structure on the current root with ``create``.
    """

    root: Path
    """The data root under which the project hierarchy is stored."""
    project_name: str
    """The name of the project, used as the project directory name directly under the root."""

    @property
    def path(self) -> Path:
        """Returns the absolute path to the project directory under the data root."""
        return self.root.joinpath(self.project_name)

    @property
    def configuration_directory(self) -> Path:
        """Returns the absolute path to the project's experiment configuration directory."""
        return self.path.joinpath(CONFIGURATION_DIRECTORY)

    def animal(self, animal_id: str) -> AnimalData:
        """Returns the ``AnimalData`` view for the given animal under this project.

        Args:
            animal_id: The unique identifier of the animal, used as the animal directory name.

        Returns:
            An ``AnimalData`` anchored on the same root and project as this instance.
        """
        return AnimalData(root=self.root, project_name=self.project_name, animal_id=animal_id)

    def for_root(self, root: Path) -> ProjectData:
        """Returns a copy of this project anchored on a different data root.

        Args:
            root: The data root to rebind the project under, such as a mounted remote storage root.

        Returns:
            A new ``ProjectData`` with the same project name resolved under the input root.
        """
        return ProjectData(root=root, project_name=self.project_name)

    def experiment_configs(self) -> tuple[Path, ...]:
        """Returns the sorted experiment configuration YAML paths under the project's configuration directory.

        Returns:
            A tuple of the ``.yaml`` file paths directly under the configuration directory, empty when the
            directory does not exist.
        """
        configuration_directory = self.configuration_directory
        if not configuration_directory.is_dir():
            return ()
        return tuple(sorted(configuration_directory.glob("*.yaml")))

    def create(self) -> ProjectData:
        """Creates the project's directory structure under the data root.

        Materializes the project's configuration directory, which also creates the project directory itself as
        a parent. The operation is idempotent, so existing directories are left untouched.

        Returns:
            This instance, to support call chaining.
        """
        self.configuration_directory.mkdir(parents=True, exist_ok=True)
        return self

    def exists(self) -> bool:
        """Determines whether the project directory exists on disk under the data root."""
        return self.path.exists()


@dataclass(frozen=True, slots=True)
class AnimalData:
    """Resolves the on-disk locations of a single animal's assets under a given data root.

    Like ``ProjectData``, instances are path-grammar views that do not require the animal directory to exist.
    Rebind the animal under a different root with ``for_root`` to resolve its session paths on a remote storage
    root.
    """

    root: Path
    """The data root under which the project hierarchy is stored."""
    project_name: str
    """The name of the project the animal belongs to."""
    animal_id: str
    """The unique identifier of the animal, used as the animal directory name."""

    @property
    def path(self) -> Path:
        """Returns the absolute path to the animal directory under the project."""
        return self.root.joinpath(self.project_name, self.animal_id)

    @property
    def project(self) -> ProjectData:
        """Returns the ``ProjectData`` view for the project this animal belongs to."""
        return ProjectData(root=self.root, project_name=self.project_name)

    @property
    def persistent_data_path(self) -> Path:
        """Returns the absolute path to the animal's cross-session persistent data directory."""
        return self.path.joinpath(PERSISTENT_DATA_DIRECTORY)

    def session_path(self, session_name: str) -> Path:
        """Returns the absolute path to the session directory for the given session name.

        Args:
            session_name: The unique identifier of the session, used as the session directory name.

        Returns:
            The absolute path to the session directory under this animal.
        """
        return self.path.joinpath(session_name)

    def for_root(self, root: Path) -> AnimalData:
        """Returns a copy of this animal anchored on a different data root.

        Args:
            root: The data root to rebind the animal under, such as a mounted remote storage root.

        Returns:
            A new ``AnimalData`` with the same project and animal resolved under the input root.
        """
        return AnimalData(root=root, project_name=self.project_name, animal_id=self.animal_id)

    def exists(self) -> bool:
        """Determines whether the animal directory exists on disk under the project."""
        return self.path.exists()
