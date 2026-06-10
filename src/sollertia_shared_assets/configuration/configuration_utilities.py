"""Provides configuration utilities shared across all data acquisition systems."""

from __future__ import annotations

from enum import StrEnum
import shutil
from typing import TYPE_CHECKING
from pathlib import Path

import platformdirs
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .mesoscope_configuration import MesoscopeExperimentConfiguration

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig

CONFIGURATION_DIRECTORY: str = "configuration"
"""The name of the directory that stores configuration files. Used both under the local working directory (where it
holds the host's system configuration) and under each project directory (where it holds the project's experiment
configuration YAML files)."""

CREDENTIALS_DIRECTORY: str = "credentials"
"""The name of the working-directory subdirectory that stores all platform credentials files."""


class AcquisitionSystems(StrEnum):
    """Defines the data acquisition systems supported by the Sollertia platform.

    Every Sollertia acquisition system runs in Virtual Reality, presenting a Unity task in the linear infinite
    corridor. Each acquisition runtime package owns its own system configuration classes; this enum remains the shared
    vocabulary that identifies which runtime a session or dataset was acquired on.
    """

    MESOSCOPE_VR = "mesoscope"
    """Uses the 2-Photon Random Access Mesoscope (2P-RAM) from Thor-Labs and a heavily modified Janelia / Allen 
    hardware harness."""


EXPERIMENT_CONFIGURATION_REGISTRY: dict[AcquisitionSystems, type[YamlConfig]] = {
    AcquisitionSystems.MESOSCOPE_VR: MesoscopeExperimentConfiguration,
}
"""Maps each acquisition system to its experiment configuration dataclass. Every registered class satisfies the
experiment-configuration contract; the configuration and template-creation tools dispatch through this registry."""


class CredentialsTypes(StrEnum):
    """Enumerates the credentials categories supported by the Sollertia platform.

    Each member's string value is the canonical identifier for the credentials' category. Downstream consumers extend
    this enumeration (together with ``CREDENTIALS_FILE_REGISTRY``) to wire additional credentials categories into the
    platform.
    """

    GOOGLE = "google"
    """The Google service account credentials used for all interactions with the Google Sheets API (canonical
    filename ``google_credentials.json``)."""


CREDENTIALS_FILE_REGISTRY: dict[CredentialsTypes, str] = {
    CredentialsTypes.GOOGLE: "google_credentials.json",
}
"""Maps each credentials category to the canonical filename under which its credentials file is stored inside the
working directory's credentials subdirectory."""


def resolve_credentials_file(credentials: str | CredentialsTypes) -> str:
    """Resolves a credentials category identifier to the canonical filename of its credentials file.

    Args:
        credentials: A ``CredentialsTypes`` member or its string value (e.g., ``"google"``).

    Returns:
        The canonical filename registered for the category in ``CREDENTIALS_FILE_REGISTRY``.

    Raises:
        ValueError: If the identifier is not a valid ``CredentialsTypes`` member.
    """
    if credentials not in CredentialsTypes:
        valid = ", ".join(member.value for member in CredentialsTypes)
        message = (
            f"Unable to resolve the credentials category '{credentials}'. Expected one of the supported "
            f"CredentialsTypes members: {valid}."
        )
        console.error(message=message, error=ValueError)
        # Unreachable: console.error() is NoReturn, but ruff cannot trace NoReturn through method calls (RET503).
        # noinspection PyUnreachableCode
        raise ValueError(message)  # pragma: no cover

    return CREDENTIALS_FILE_REGISTRY[CredentialsTypes(credentials)]


def set_working_directory(path: Path) -> None:
    """Sets the specified directory as the Sollertia platform working directory for the local machine (PC).

    Notes:
        This function caches the path to the working directory in the user's data directory.

        If the input path does not point to an existing directory, the function creates the requested directory.

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

    The data root is the directory under which all project directories, and therefore all animal and session
    directories, are stored on this machine. Persisting it lets the discovery and inventory assets resolve the
    project hierarchy without the caller supplying the root each time.

    Notes:
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


def set_credentials(credentials: str | CredentialsTypes, path: Path) -> None:
    """Copies the specified credentials file into the working directory's credentials subdirectory.

    The copy is stored under the canonical filename registered for the credentials category, replacing any
    previously configured credentials file for that category.

    Notes:
        The configured credentials file is used for all future interactions with the corresponding external
        service carried out from this machine.

    Args:
        credentials: The ``CredentialsTypes`` member or its string value identifying the credentials category to
            configure.
        path: The path to the credentials file to copy into the credentials' subdirectory.

    Raises:
        ValueError: If the credentials category is not a valid ``CredentialsTypes`` member, or if the specified
            file's extension does not match the canonical credentials filename's extension.
        FileNotFoundError: If the specified credentials file does not exist at the provided path, or if the local
            working directory has not been configured for the host-machine.
    """
    file_name = resolve_credentials_file(credentials=credentials)

    if not path.exists():
        message = (
            f"Unable to set the '{CredentialsTypes(credentials)}' credentials file. The specified file ({path}) does "
            f"not exist. Ensure the credentials file exists at the specified path before calling this function."
        )
        console.error(message=message, error=FileNotFoundError)

    expected_suffix = Path(file_name).suffix
    if path.suffix.lower() != expected_suffix:
        message = (
            f"Unable to set the '{CredentialsTypes(credentials)}' credentials file. The specified file ({path}) does "
            f"not have a {expected_suffix} extension. Provide the path to a valid {expected_suffix} credentials file."
        )
        console.error(message=message, error=ValueError)

    credentials_directory = get_working_directory().joinpath(CREDENTIALS_DIRECTORY)
    ensure_directory_exists(path=credentials_directory)

    destination = credentials_directory.joinpath(file_name)
    shutil.copyfile(src=path, dst=destination)

    console.echo(
        message=f"The '{CredentialsTypes(credentials)}' credentials file copied to: {destination}.",
        level=LogLevel.SUCCESS,
    )


def get_credentials(credentials: str | CredentialsTypes) -> Path:
    """Resolves and returns the path to the requested credentials file stored in the working directory's credentials
    subdirectory.

    Args:
        credentials: The ``CredentialsTypes`` member or its string value identifying the credentials category to
            resolve.

    Returns:
        The path to the requested credentials file.

    Raises:
        ValueError: If the credentials category is not a valid ``CredentialsTypes`` member.
        FileNotFoundError: If the local working directory has not been configured for the host-machine, or if the
            credentials file for the requested category has not been set.
    """
    file_name = resolve_credentials_file(credentials=credentials)
    credentials_path = get_working_directory().joinpath(CREDENTIALS_DIRECTORY, file_name)

    if not credentials_path.exists():
        message = (
            f"Unable to resolve the path to the '{CredentialsTypes(credentials)}' credentials file, as it has not "
            f"been set. Set the credentials file by using the 'slsa configure credentials' CLI command."
        )
        console.error(message=message, error=FileNotFoundError)

    return credentials_path


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
