"""Provides the credentials toolset that copies per-category credentials files into the working directory's
credentials subdirectory and resolves them back for downstream consumers.

This toolset lives in its own top-level module, rather than next to the other persistent host settings in
``configuration/configuration_utilities.py``, because its functions are the runtime consumers of
``CREDENTIALS_FILE_REGISTRY``. Keeping the consumers downstream of the ``registries`` module preserves the
library-wide rule that every dispatch registry is defined in ``registries`` while keeping the import graph acyclic:
this module imports the registry, and the registry module never imports this one. The ``CREDENTIALS_DIRECTORY``
constant remains part of the working-directory layout owned by the configuration package (``set_working_directory``
pre-creates the subdirectory) and is imported from there.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .enums import CredentialsTypes
from .registries import CREDENTIALS_FILE_REGISTRY
from .configuration import CREDENTIALS_DIRECTORY, get_working_directory


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
