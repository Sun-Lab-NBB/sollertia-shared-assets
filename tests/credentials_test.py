"""Contains tests for the credentials toolset provided by the ``credentials`` module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import platformdirs

from sollertia_shared_assets.enums import CredentialsTypes
from sollertia_shared_assets.credentials import (
    get_credentials,
    set_credentials,
    resolve_credentials_file,
)
from sollertia_shared_assets.registries import CREDENTIALS_FILE_REGISTRY
from sollertia_shared_assets.configuration import CREDENTIALS_DIRECTORY, set_working_directory

if TYPE_CHECKING:
    from pathlib import Path


def test_resolve_credentials_file_returns_registered_file_name() -> None:
    """Verifies that resolve_credentials_file resolves both members and string values to canonical filenames."""
    assert resolve_credentials_file(credentials=CredentialsTypes.GOOGLE) == "google_credentials.json"
    assert resolve_credentials_file(credentials="google") == CREDENTIALS_FILE_REGISTRY[CredentialsTypes.GOOGLE]


def test_resolve_credentials_file_raises_error_unknown_category() -> None:
    """Verifies that resolve_credentials_file raises ValueError for unsupported categories."""
    with pytest.raises(ValueError, match=r"Unable to resolve the credentials category"):
        resolve_credentials_file(credentials="unsupported")


def test_set_credentials_copies_file_under_canonical_name(clean_working_directory: Path) -> None:
    """Verifies that set_credentials copies the source file into the credentials subdirectory, renaming it to the
    category's canonical filename."""
    set_working_directory(path=clean_working_directory)

    credentials_file = clean_working_directory.parent / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_credentials(credentials=CredentialsTypes.GOOGLE, path=credentials_file)

    stored_file = clean_working_directory / CREDENTIALS_DIRECTORY / "google_credentials.json"
    assert stored_file.exists()
    assert stored_file.read_text() == '{"type": "service_account"}'


def test_set_credentials_overwrites_existing_file(clean_working_directory: Path) -> None:
    """Verifies that set_credentials replaces a previously configured credentials file for the same category."""
    set_working_directory(path=clean_working_directory)

    first_file = clean_working_directory.parent / "first.json"
    first_file.write_text('{"account": "first"}')
    set_credentials(credentials=CredentialsTypes.GOOGLE, path=first_file)

    second_file = clean_working_directory.parent / "second.json"
    second_file.write_text('{"account": "second"}')
    set_credentials(credentials=CredentialsTypes.GOOGLE, path=second_file)

    stored_file = clean_working_directory / CREDENTIALS_DIRECTORY / "google_credentials.json"
    assert stored_file.read_text() == '{"account": "second"}'


def test_set_credentials_raises_error_file_not_exists(clean_working_directory: Path) -> None:
    """Verifies that set_credentials raises error for non-existent source files."""
    set_working_directory(path=clean_working_directory)

    non_existent_file = clean_working_directory.parent / "missing.json"

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        set_credentials(credentials=CredentialsTypes.GOOGLE, path=non_existent_file)


def test_set_credentials_raises_error_wrong_extension(clean_working_directory: Path) -> None:
    """Verifies that set_credentials raises error when the source file's extension does not match the canonical
    credentials filename's extension."""
    set_working_directory(path=clean_working_directory)

    wrong_extension = clean_working_directory.parent / "credentials.txt"
    wrong_extension.write_text("not json")

    with pytest.raises(ValueError, match=r"\.json"):
        set_credentials(credentials=CredentialsTypes.GOOGLE, path=wrong_extension)


def test_set_credentials_raises_error_unknown_category(clean_working_directory: Path) -> None:
    """Verifies that set_credentials raises ValueError for unsupported credentials categories."""
    set_working_directory(path=clean_working_directory)

    credentials_file = clean_working_directory.parent / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    with pytest.raises(ValueError, match=r"Unable to resolve the credentials category"):
        set_credentials(credentials="unsupported", path=credentials_file)


def test_set_credentials_raises_error_working_directory_not_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_credentials raises an error when the working directory is not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    with pytest.raises(FileNotFoundError, match=r"working directory"):
        set_credentials(credentials=CredentialsTypes.GOOGLE, path=credentials_file)


def test_get_credentials_returns_stored_path(clean_working_directory: Path) -> None:
    """Verifies that get_credentials returns the canonical path of a previously set credentials file."""
    set_working_directory(path=clean_working_directory)

    credentials_file = clean_working_directory.parent / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')
    set_credentials(credentials=CredentialsTypes.GOOGLE, path=credentials_file)

    retrieved_path = get_credentials(credentials=CredentialsTypes.GOOGLE)

    assert retrieved_path == clean_working_directory / CREDENTIALS_DIRECTORY / "google_credentials.json"


def test_get_credentials_accepts_string_category(clean_working_directory: Path) -> None:
    """Verifies that get_credentials resolves string category identifiers."""
    set_working_directory(path=clean_working_directory)

    credentials_file = clean_working_directory.parent / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')
    set_credentials(credentials="google", path=credentials_file)

    assert get_credentials(credentials="google") == get_credentials(credentials=CredentialsTypes.GOOGLE)


def test_get_credentials_raises_error_if_not_set(clean_working_directory: Path) -> None:
    """Verifies that get_credentials raises an error when no credentials file was set for the category."""
    set_working_directory(path=clean_working_directory)

    with pytest.raises(FileNotFoundError, match=r"has not\s+been set"):
        get_credentials(credentials=CredentialsTypes.GOOGLE)


def test_get_credentials_raises_error_working_directory_not_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_credentials raises an error when the working directory is not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"working directory"):
        get_credentials(credentials=CredentialsTypes.GOOGLE)


def test_get_credentials_raises_error_unknown_category(clean_working_directory: Path) -> None:
    """Verifies that get_credentials raises ValueError for unsupported credentials categories."""
    set_working_directory(path=clean_working_directory)

    with pytest.raises(ValueError, match=r"Unable to resolve the credentials category"):
        get_credentials(credentials="unsupported")
