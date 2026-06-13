"""Provides configuration utilities shared across all data acquisition systems."""

from __future__ import annotations

from pathlib import Path

import platformdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

CONFIGURATION_DIRECTORY: str = "configuration"
"""The name of the directory that stores configuration files. Used both under the local working directory (where it
holds the host's system configuration) and under each project directory (where it holds the project's experiment
configuration YAML files)."""

CREDENTIALS_DIRECTORY: str = "credentials"
"""The name of the working-directory subdirectory that stores all platform credentials files. The constant lives with
the working-directory layout (``set_working_directory`` pre-creates the subdirectory); the credentials toolset that
fills the subdirectory lives in the top-level ``credentials`` module."""


def set_working_directory(path: Path) -> None:
    """Sets the specified directory as the Sollertia platform working directory for the local machine (PC).

    Notes:
        This function caches the path to the working directory in the user's data directory.

        If the input path does not point to an existing directory, the function creates the requested directory
        along with its ``configuration`` and ``credentials`` subdirectories.

    Args:
        path: The path to the directory to set as the local Sollertia platform working directory.
    """
    application_directory = Path(platformdirs.user_data_dir(appname="sollertia_data", appauthor="sollertia"))
    path_file = application_directory.joinpath("working_directory_path.txt")

    ensure_directory_exists(path=path_file)
    ensure_directory_exists(path=path)
    ensure_directory_exists(path=path.joinpath(CONFIGURATION_DIRECTORY))
    ensure_directory_exists(path=path.joinpath(CREDENTIALS_DIRECTORY))

    with path_file.open(mode="w") as file:
        file.write(str(path))

    console.echo(message=f"Sollertia platform working directory set to: {path}.", level=LogLevel.SUCCESS)


def get_working_directory() -> Path:
    """Resolves and returns the path to the local Sollertia platform working directory.

    Returns:
        The path to the local working directory.

    Raises:
        FileNotFoundError: If the local working directory has not been configured for the host-machine, or if the
            currently configured directory does not exist at the expected path.
    """
    application_directory = Path(platformdirs.user_data_dir(appname="sollertia_data", appauthor="sollertia"))
    path_file = application_directory.joinpath("working_directory_path.txt")

    if not path_file.exists():
        message = (
            "Unable to resolve the path to the local Sollertia platform working directory, as it has not been set. "
            "Set the local working directory by using the 'slsa configure directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    with path_file.open() as file:
        working_directory = Path(file.read().strip())

    if not working_directory.exists():
        message = (
            "Unable to resolve the path to the local Sollertia platform working directory, as the currently configured "
            "directory does not exist at the expected path. Set a new working directory by using the 'slsa configure "
            "directory' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    return working_directory


def set_data_root(path: Path) -> None:
    """Sets the specified directory as the local machine's Sollertia platform data root.

    Notes:
        The data root is the directory under which all project directories, and therefore all animal and session
        directories, are stored on this machine. Persisting it lets the discovery and inventory assets resolve the
        project hierarchy without the caller supplying the root each time.

        This function caches the path to the data root in the user's data directory.

        If the input path does not point to an existing directory, the function creates the requested directory.

    Args:
        path: The path to the directory to set as the local Sollertia platform data root.
    """
    application_directory = Path(platformdirs.user_data_dir(appname="sollertia_data", appauthor="sollertia"))
    path_file = application_directory.joinpath("data_root_path.txt")

    ensure_directory_exists(path=path_file)
    ensure_directory_exists(path=path)

    with path_file.open(mode="w") as file:
        file.write(str(path))

    console.echo(message=f"Sollertia platform data root set to: {path}.", level=LogLevel.SUCCESS)


def get_data_root() -> Path:
    """Resolves and returns the path to the local machine's Sollertia platform data root.

    Returns:
        The path to the local data root, the directory under which all project directories are stored.

    Raises:
        FileNotFoundError: If the local data root has not been configured for the host-machine, or if the currently
            configured directory does not exist at the expected path.
    """
    application_directory = Path(platformdirs.user_data_dir(appname="sollertia_data", appauthor="sollertia"))
    path_file = application_directory.joinpath("data_root_path.txt")

    if not path_file.exists():
        message = (
            "Unable to resolve the path to the local Sollertia platform data root, as it has not been set. "
            "Set the local data root by using the 'slsa configure data-root' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    with path_file.open() as file:
        data_root = Path(file.read().strip())

    if not data_root.exists():
        message = (
            "Unable to resolve the path to the local Sollertia platform data root, as the currently configured "
            "directory does not exist at the expected path. Set a new data root by using the 'slsa configure "
            "data-root' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    return data_root


def set_task_templates_directory(path: Path) -> None:
    """Sets the path to the sollertia-unity-tasks project's Configurations (Template) directory.

    Persists the path under ``platformdirs``-managed application data so it is reused by subsequent ``slsa mcp``
    sessions on the same local machine (PC).

    Args:
        path: The path to the sollertia-unity-tasks project's Configurations (Template) directory.

    Raises:
        FileNotFoundError: If the specified directory does not exist at the provided path.
        ValueError: If the specified path does not point to a directory.
    """
    if not path.exists():
        message = (
            f"Unable to set the task templates directory path. The specified directory ({path}) does not exist. "
            f"Ensure the directory exists at the specified path before calling this function."
        )
        console.error(message=message, error=FileNotFoundError)

    if not path.is_dir():
        message = (
            f"Unable to set the task templates directory path. The specified path ({path}) does not point to a "
            f"directory. Provide the path to the sollertia-unity-tasks project's Configurations (Template) directory."
        )
        console.error(message=message, error=ValueError)

    application_directory = Path(platformdirs.user_data_dir(appname="sollertia_data", appauthor="sollertia"))
    path_file = application_directory.joinpath("task_templates_directory_path.txt")

    ensure_directory_exists(path=path_file)

    with path_file.open(mode="w") as file:
        file.write(str(path.resolve()))

    console.echo(message=f"Task templates directory path set to: {path.resolve()}.", level=LogLevel.SUCCESS)


def get_task_templates_directory() -> Path:
    """Resolves and returns the path to the sollertia-unity-tasks project's Configurations (Template) directory.

    Returns:
        The path to the task templates directory.

    Raises:
        FileNotFoundError: If the task templates directory path has not been configured for the host-machine, or if
            the previously configured directory does not exist at the expected path.
    """
    application_directory = Path(platformdirs.user_data_dir(appname="sollertia_data", appauthor="sollertia"))
    path_file = application_directory.joinpath("task_templates_directory_path.txt")

    if not path_file.exists():
        message = (
            "Unable to resolve the path to the task templates directory, as it has not been set. "
            "Set the task templates directory path by using the 'slsa configure templates' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    with path_file.open() as file:
        templates_directory = Path(file.read().strip())

    if not templates_directory.exists():
        message = (
            f"Unable to resolve the path to the task templates directory, as the previously configured "
            f"directory does not exist at the expected path ({templates_directory}). Set a new directory path "
            f"by using the 'slsa configure templates' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    return templates_directory
