"""Provides configuration utilities shared across all data acquisition systems.

This module contains the acquisition systems enumeration and working directory path utilities.
"""

from enum import StrEnum
from pathlib import Path

import appdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists


class AcquisitionSystems(StrEnum):
    """Defines the data acquisition systems currently used in the Sun lab."""

    MESOSCOPE_VR = "mesoscope"
    """Uses the 2-Photon Random Access Mesoscope (2P-RAM) with Virtual Reality (VR) environments running in Unity game
    engine to conduct experiments."""


def set_working_directory(path: Path) -> None:
    """Sets the specified directory as the Sun lab's working directory for the local machine (PC).

    Notes:
        This function caches the path to the working directory in the user's data directory.

        If the input path does not point to an existing directory, the function creates the requested directory.

    Args:
        path: The path to the directory to set as the local Sun lab's working directory.
    """
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    ensure_directory_exists(path_file)
    ensure_directory_exists(path)
    ensure_directory_exists(path.joinpath("configuration"))

    with path_file.open("w") as f:
        f.write(str(path))

    console.echo(message=f"Sun lab's working directory set to: {path}.", level=LogLevel.SUCCESS)


def get_working_directory() -> Path:
    """Resolves and returns the path to the local Sun lab's working directory.

    Returns:
        The path to the local working directory.

    Raises:
        FileNotFoundError: If the local working directory has not been configured for the host-machine.
    """
    app_dir = Path(appdirs.user_data_dir(appname="sun_lab_data", appauthor="sun_lab"))
    path_file = app_dir.joinpath("working_directory_path.txt")

    if not path_file.exists():
        message = (
            "Unable to resolve the path to the local Sun lab's working directory, as it has not been set. "
            "Set the local working directory by using the 'sl-configure directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    with path_file.open() as f:
        working_directory = Path(f.read().strip())

    if not working_directory.exists():
        message = (
            "Unable to resolve the path to the local Sun lab's working directory, as the currently configured "
            "directory does not exist at the expected path. Set a new working directory by using the 'sl-configure "
            "directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    return working_directory
