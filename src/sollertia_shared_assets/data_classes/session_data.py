"""Provides assets for maintaining the Sollertia platform project data hierarchy across all data acquisition and
processing machines.
"""

from __future__ import annotations

from enum import StrEnum
import shutil
from pathlib import Path
from dataclasses import dataclass

from ataraxis_time import TimestampFormats, get_timestamp
from ataraxis_base_utilities import console, ensure_directory_exists
from ataraxis_data_structures import YamlConfig

from ..configuration import AcquisitionSystems


class SessionTypes(StrEnum):
    """Defines the data acquisition session types supported by all data acquisition systems in the Sollertia
    platform.
    """

    LICK_TRAINING = "lick training"
    """Teaches animals to use the water delivery port while being head-fixed on the Mesoscope-VR system."""
    RUN_TRAINING = "run training"
    """Teaches animals to run on the treadmill while being head-fixed on the Mesoscope-VR system."""
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    """Runs virtual reality tasks using Unity game engine and collects brain activity data using the 2-Photon
    Random Access Mesoscope (2P-RAM)."""
    WINDOW_CHECKING = "window checking"
    """Evaluates the quality of the cranial window implantation procedure and the suitability of the animal for
    experiment sessions using the Mesoscope."""


@dataclass
class SessionData(YamlConfig):
    """Defines the structure and the metadata of a data acquisition session.

    This class encapsulates the information necessary to access the session's data stored on disk and functions as the
    entry point for all interactions with the session's data.

    Notes:
        Do not initialize this class directly. Instead, use the create() method when starting new data acquisition
        sessions or the load() method when accessing data for an existing session.

        When this class is used to create a new session, it generates the new session's name using the current UTC
        timestamp, accurate to microseconds. This ensures that each session 'name' is unique and preserves the overall
        session order.
    """

    project_name: str
    """The name of the project for which the session was acquired."""
    animal_id: str
    """The unique identifier of the animal that participates in the session."""
    session_name: str
    """The unique identifier (name) of the session."""
    session_type: str | SessionTypes
    """The type of the session."""
    acquisition_system: str | AcquisitionSystems = AcquisitionSystems.MESOSCOPE_VR
    """The name of the data acquisition system used to acquire the session's data."""
    experiment_name: str | None = None
    """The name of the experiment performed during the session or Null (None), if the session is not an
    experiment session."""
    python_version: str = "3.14.4"
    """The Python version used to acquire session's data."""
    sollertia_experiment_version: str = "5.0.0"
    """The sollertia-experiment library version used to acquire the session's data."""
    raw_data_path: Path = Path()
    """The path to the root directory that stores the session's raw data."""
    processed_data_path: Path = Path()
    """The path to the root directory that stores the session's processed data."""

    def __post_init__(self) -> None:
        """Ensures that all fields used to define the session are properly initialized."""
        # Converts string values loaded from YAML to proper enum types.
        if isinstance(self.session_type, str):
            self.session_type = SessionTypes(self.session_type)
        if isinstance(self.acquisition_system, str):
            self.acquisition_system = AcquisitionSystems(self.acquisition_system)

    @classmethod
    def create(
        cls,
        project_name: str,
        animal_id: str,
        session_type: str | SessionTypes,
        python_version: str,
        sollertia_experiment_version: str,
        acquisition_system: str | AcquisitionSystems,
        root_directory: Path,
        experiment_name: str | None = None,
    ) -> SessionData:
        """Initializes a new data acquisition session and creates its data structure on the host-machine's filesystem.

        Notes:
            To access the data of an already existing session, use the load() method.

            This method does not persist the acquisition system's own configuration snapshot; the acquisition runtime
            package (e.g., sl-experiment) owns that data and is responsible for writing it into the returned
            session's raw_data directory after this method returns.

        Args:
            project_name: The name of the project for which the session is acquired.
            animal_id: The unique identifier of the animal participating in the session.
            session_type: The type of the session.
            python_version: The Python version used to acquire the session's data.
            sollertia_experiment_version: The sollertia-experiment library version used to acquire the session's data.
            acquisition_system: The acquisition system that will run the session. Accepts an ``AcquisitionSystems``
                enumeration member or its string value.
            root_directory: The root directory of the acquisition system's project hierarchy on the local machine
                (PC). The session is created under ``root_directory / project_name / animal_id / <session_name>``.
            experiment_name: The name of the experiment performed during the session or None, if the session is
                not an experiment session.

        Returns:
            An initialized SessionData instance that stores the structure and the metadata of the created session.

        Raises:
            ValueError: If the specified session_type or acquisition_system is not a valid enumeration member.
            FileNotFoundError: If the project does not exist on the local machine (PC).
        """
        if session_type not in SessionTypes:
            message = (
                f"Unable to initialize a new data acquisition session. The session_type must be one of the "
                f"SessionTypes enumeration members, but got '{session_type}'."
            )
            console.error(message=message, error=ValueError)

        if acquisition_system not in AcquisitionSystems:
            message = (
                f"Unable to initialize a new data acquisition session. The acquisition_system must be one of the "
                f"AcquisitionSystems enumeration members, but got '{acquisition_system}'."
            )
            console.error(message=message, error=ValueError)
        acquisition_system = AcquisitionSystems(acquisition_system)

        # Acquires the UTC timestamp to use as the session name.
        session_name = str(get_timestamp(time_separator="-", output_format=TimestampFormats.STRING))

        # Constructs the root session directory path from the caller-provided root directory.
        session_path = root_directory.joinpath(project_name, animal_id, session_name)

        # Prevents creating new sessions for non-existent projects.
        if not root_directory.joinpath(project_name).exists():
            message = (
                f"Unable to initialize a new data acquisition session {session_name} for the animal '{animal_id}' and "
                f"project '{project_name}'. The project does not exist on the local machine (PC). Use the "
                f"'sl-project create' CLI command to create the project on the local machine before creating new "
                f"sessions."
            )
            console.error(message=message, error=FileNotFoundError)

        # Generates the session's raw data directory. This method assumes that the session is created on the
        # data acquisition machine that only acquires the data and does not create the other session's directories used
        # during data processing.
        raw_data_path = session_path.joinpath("raw_data")
        ensure_directory_exists(path=raw_data_path)

        # Generates the SessionData instance. processed_data_path is left at the default Path() because the data
        # acquisition machine does not own the processed data hierarchy.
        instance = cls(
            project_name=project_name,
            animal_id=animal_id,
            session_name=session_name,
            session_type=session_type,
            acquisition_system=acquisition_system,
            experiment_name=experiment_name,
            python_version=python_version,
            sollertia_experiment_version=sollertia_experiment_version,
            raw_data_path=raw_data_path,
        )

        # Saves the configured instance data to the session's directory so that it can be reused during processing or
        # preprocessing.
        instance.save()

        if experiment_name is not None:
            # Copies the experiment_configuration.yaml file to the session's directory.
            experiment_configuration_path = root_directory.joinpath(
                project_name, "configuration", f"{experiment_name}.yaml"
            )
            shutil.copy2(
                src=experiment_configuration_path,
                dst=instance.raw_data_path.joinpath("experiment_configuration.yaml"),
            )

        # All newly created sessions are marked with the 'nk.bin' file. If the marker is not removed during runtime,
        # the session becomes a valid target for deletion (purging) runtimes operating from the main acquisition
        # machine of any data acquisition system.
        instance.raw_data_path.joinpath("nk.bin").touch()

        return instance

    @classmethod
    def load(cls, session_path: Path) -> SessionData:
        """Loads the target session's data from the specified session_data.yaml file.

        Notes:
            To create a new session, use the create() method.

        Args:
            session_path: The path to the directory where to search for the session_data.yaml file. Typically, this
                is the path to the root session's directory, e.g.: root/project/animal/session.

        Returns:
            An initialized SessionData instance that stores the loaded session's data.

        Raises:
            FileNotFoundError: If multiple or no 'session_data.yaml' file instances are found under the input directory.
        """
        # To properly initialize the SessionData instance, the provided path should contain a single session_data.yaml
        # file at any hierarchy level.
        session_data_files = list(session_path.rglob("session_data.yaml"))
        if len(session_data_files) != 1:
            message = (
                f"Unable to load the target session's data. Expected a single session_data.yaml file to be located "
                f"under the directory tree specified by the input path: {session_path}. Instead, encountered "
                f"{len(session_data_files)} candidate files. This indicates that the input path does not point to a "
                f"valid session data hierarchy."
            )
            console.error(message=message, error=FileNotFoundError)

        # If a single candidate is found (as expected), extracts it from the list and uses it to resolve the
        # session data hierarchy.
        session_data_path = session_data_files.pop()

        # Loads the session's data from the .yaml file.
        instance: SessionData = cls.from_yaml(file_path=session_data_path)

        # The method assumes that the 'donor' YAML file is always stored inside the raw_data directory of the session
        # to be processed. Uses this heuristic to get the path to the root session's directory and re-resolves the
        # raw and processed data root paths against the local filesystem layout so the session remains portable.
        local_root = session_data_path.parents[1]
        instance.raw_data_path = local_root.joinpath("raw_data")
        instance.processed_data_path = local_root.joinpath("processed_data")

        return instance

    def mark_runtime_initialized(self) -> None:
        """Removes the 'nk.bin' marker file from the session's raw_data directory to signal that runtime
        initialization has completed.

        Notes:
            This service method is used by the sollertia-experiment library to acquire the session's data. Do not call
            this method manually.
        """
        self.raw_data_path.joinpath("nk.bin").unlink(missing_ok=True)

    def save(self) -> None:
        """Caches the instance's data to the session's 'raw_data' directory as a 'session_data.yaml' file."""
        self.to_yaml(file_path=self.raw_data_path.joinpath("session_data.yaml"))
