"""Contains tests for the platform configuration utilities provided by the
``configuration.configuration_utilities`` module.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
import platformdirs

from sollertia_shared_assets.configuration import (
    CREDENTIALS_DIRECTORY,
    CREDENTIALS_FILE_REGISTRY,
    CredentialsTypes,
    AcquisitionSystems,
    get_data_root,
    set_data_root,
    get_credentials,
    set_credentials,
    get_working_directory,
    set_working_directory,
    resolve_credentials_file,
    get_task_templates_directory,
    set_task_templates_directory,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_acquisition_systems_mesoscope_vr_value() -> None:
    """Verifies the MESOSCOPE_VR acquisition system enumeration value."""
    assert AcquisitionSystems.MESOSCOPE_VR == "mesoscope"
    assert str(AcquisitionSystems.MESOSCOPE_VR) == "mesoscope"


def test_acquisition_systems_is_string_enum() -> None:
    """Verifies that AcquisitionSystems inherits from StrEnum."""
    assert isinstance(AcquisitionSystems.MESOSCOPE_VR, str)


def test_set_working_directory_creates_directory(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory creates the directory if it does not exist."""
    new_dir = clean_working_directory.parent / "new_working_dir"
    assert not new_dir.exists()

    set_working_directory(path=new_dir)

    assert new_dir.exists()


def test_set_working_directory_creates_service_subdirectories(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory creates the configuration and credentials subdirectories."""
    set_working_directory(path=clean_working_directory)

    assert (clean_working_directory / "configuration").is_dir()
    assert (clean_working_directory / CREDENTIALS_DIRECTORY).is_dir()


def test_set_working_directory_writes_path_file(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory writes the path to the cache file."""
    set_working_directory(path=clean_working_directory)

    app_dir = clean_working_directory.parent / "app_data"
    path_file = app_dir / "working_directory_path.txt"
    assert path_file.exists()
    assert path_file.read_text() == str(clean_working_directory)


def test_set_working_directory_creates_app_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_working_directory creates the application data directory."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    working_dir = tmp_path / "working"
    working_dir.mkdir()

    assert not app_dir.exists()
    set_working_directory(path=working_dir)
    assert app_dir.exists()


def test_set_working_directory_overwrites_existing(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory overwrites an existing cached path."""
    first_dir = clean_working_directory / "first"
    first_dir.mkdir()
    set_working_directory(path=first_dir)

    second_dir = clean_working_directory / "second"
    second_dir.mkdir()
    set_working_directory(path=second_dir)

    app_dir = clean_working_directory.parent / "app_data"
    path_file = app_dir / "working_directory_path.txt"
    assert path_file.read_text() == str(second_dir)


def test_get_working_directory_returns_cached_path(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory returns the cached directory path."""
    set_working_directory(path=clean_working_directory)
    retrieved_dir = get_working_directory()

    assert retrieved_dir == clean_working_directory


def test_get_working_directory_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_working_directory raises FileNotFoundError if not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_working_directory()


def test_get_working_directory_raises_error_if_directory_missing(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory raises error if the cached directory does not exist."""
    set_working_directory(path=clean_working_directory)

    # Simulates an out-of-date cache.
    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError, match=r"currently configured"):
        get_working_directory()


def test_set_data_root_creates_directory(clean_working_directory: Path) -> None:
    """Verifies that set_data_root creates the directory if it does not exist (working-directory model)."""
    new_dir = clean_working_directory.parent / "new_data_root"
    assert not new_dir.exists()

    set_data_root(path=new_dir)

    assert new_dir.exists()


def test_set_data_root_writes_path_file(clean_working_directory: Path) -> None:
    """Verifies that set_data_root writes the path to the cache file."""
    set_data_root(path=clean_working_directory)

    app_dir = clean_working_directory.parent / "app_data"
    path_file = app_dir / "data_root_path.txt"
    assert path_file.exists()
    assert path_file.read_text() == str(clean_working_directory)


def test_get_data_root_returns_cached_path(clean_working_directory: Path) -> None:
    """Verifies that get_data_root returns the cached directory path."""
    set_data_root(path=clean_working_directory)

    assert get_data_root() == clean_working_directory


def test_get_data_root_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_data_root raises FileNotFoundError if not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_data_root()


def test_get_data_root_raises_error_if_directory_missing(clean_working_directory: Path) -> None:
    """Verifies that get_data_root raises error if the cached directory does not exist."""
    set_data_root(path=clean_working_directory)

    # Simulates an out-of-date cache.
    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError, match=r"currently configured"):
        get_data_root()


def test_credentials_types_google_value() -> None:
    """Verifies the GOOGLE credentials category enumeration value."""
    assert CredentialsTypes.GOOGLE == "google"
    assert isinstance(CredentialsTypes.GOOGLE, str)


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


def test_set_task_templates_directory_creates_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory caches the directory path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(path=templates_dir)

    cache_file = app_dir / "task_templates_directory_path.txt"
    assert cache_file.exists()
    assert cache_file.read_text() == str(templates_dir.resolve())


def test_set_task_templates_directory_raises_error_not_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory raises error for non-existent directory."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    nonexistent = tmp_path / "missing_dir"

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        set_task_templates_directory(path=nonexistent)


def test_set_task_templates_directory_raises_error_not_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_task_templates_directory raises error when path is a file."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    file_path = tmp_path / "a_file.txt"
    file_path.write_text("content")

    with pytest.raises(ValueError, match=r"does not point to a\s+directory"):
        set_task_templates_directory(path=file_path)


def test_get_task_templates_directory_returns_cached_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_task_templates_directory returns the cached directory path."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(path=templates_dir)
    retrieved = get_task_templates_directory()

    assert retrieved == templates_dir.resolve()


def test_get_task_templates_directory_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_task_templates_directory raises error if not configured."""
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_task_templates_directory()


def test_get_task_templates_directory_raises_error_if_directory_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_task_templates_directory raises error if cached directory was deleted."""
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    set_task_templates_directory(path=templates_dir)
    shutil.rmtree(templates_dir)

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        get_task_templates_directory()
