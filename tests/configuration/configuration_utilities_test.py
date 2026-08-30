"""Contains tests for the platform configuration utilities provided by the ``configuration.configuration_utilities``
module.
"""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import pytest
import platformdirs

from sollertia_shared_assets.configuration import (
    CREDENTIALS_DIRECTORY,
    get_data_root,
    set_data_root,
    get_working_directory,
    set_working_directory,
    get_task_templates_directory,
    set_task_templates_directory,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_set_working_directory_creates_directory(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory creates the directory if it does not exist."""
    new_directory = clean_working_directory.parent / "new_working_dir"
    assert not new_directory.exists()

    set_working_directory(path=new_directory)

    assert new_directory.exists()


def test_set_working_directory_creates_service_subdirectories(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory creates the configuration and credentials subdirectories."""
    set_working_directory(path=clean_working_directory)

    assert (clean_working_directory / "configuration").is_dir()
    assert (clean_working_directory / CREDENTIALS_DIRECTORY).is_dir()


def test_set_working_directory_writes_path_file(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory writes the path to the cache file."""
    set_working_directory(path=clean_working_directory)

    application_directory = clean_working_directory.parent / "app_data"
    path_file = application_directory / "working_directory_path.txt"
    assert path_file.exists()
    assert path_file.read_text() == str(clean_working_directory)


def test_set_working_directory_creates_app_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_working_directory creates the application data directory."""
    application_directory = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    working_directory = tmp_path / "working"
    working_directory.mkdir()

    assert not application_directory.exists()
    set_working_directory(path=working_directory)
    assert application_directory.exists()


def test_set_working_directory_overwrites_existing(clean_working_directory: Path) -> None:
    """Verifies that set_working_directory overwrites an existing cached path."""
    first_directory = clean_working_directory / "first"
    first_directory.mkdir()
    set_working_directory(path=first_directory)

    second_directory = clean_working_directory / "second"
    second_directory.mkdir()
    set_working_directory(path=second_directory)

    application_directory = clean_working_directory.parent / "app_data"
    path_file = application_directory / "working_directory_path.txt"
    assert path_file.read_text() == str(second_directory)


def test_get_working_directory_returns_cached_path(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory returns the cached directory path."""
    set_working_directory(path=clean_working_directory)
    retrieved_directory = get_working_directory()

    assert retrieved_directory == clean_working_directory


def test_get_working_directory_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_working_directory raises FileNotFoundError if not configured."""
    application_directory = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_working_directory()


def test_get_working_directory_raises_error_if_directory_missing(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory raises an error if the cached directory does not exist."""
    set_working_directory(path=clean_working_directory)

    # Simulates an out-of-date cache.
    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError, match=r"currently configured"):
        get_working_directory()


def test_get_working_directory_preserves_trailing_whitespace(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory preserves a trailing space in a newline-terminated path record."""
    spaced_directory = clean_working_directory.parent / "working directory "
    spaced_directory.mkdir()
    path_file = clean_working_directory.parent / "app_data" / "working_directory_path.txt"
    path_file.write_text(f"{spaced_directory}\n")

    assert get_working_directory() == spaced_directory


def test_get_working_directory_raises_error_if_record_is_whitespace(clean_working_directory: Path) -> None:
    """Verifies that get_working_directory raises FileNotFoundError for a newline-only path record."""
    set_working_directory(path=clean_working_directory)

    path_file = clean_working_directory.parent / "app_data" / "working_directory_path.txt"
    path_file.write_text("\n")

    with pytest.raises(FileNotFoundError, match=r"cached path record\s+is empty"):
        get_working_directory()


def test_set_data_root_creates_directory(clean_working_directory: Path) -> None:
    """Verifies that set_data_root creates the directory if it does not exist (working-directory model)."""
    new_directory = clean_working_directory.parent / "new_data_root"
    assert not new_directory.exists()

    set_data_root(path=new_directory)

    assert new_directory.exists()


def test_set_data_root_writes_path_file(clean_working_directory: Path) -> None:
    """Verifies that set_data_root writes the path to the cache file."""
    set_data_root(path=clean_working_directory)

    application_directory = clean_working_directory.parent / "app_data"
    path_file = application_directory / "data_root_path.txt"
    assert path_file.exists()
    assert path_file.read_text() == str(clean_working_directory)


def test_get_data_root_returns_cached_path(clean_working_directory: Path) -> None:
    """Verifies that get_data_root returns the cached directory path."""
    set_data_root(path=clean_working_directory)

    assert get_data_root() == clean_working_directory


def test_get_data_root_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_data_root raises FileNotFoundError if not configured."""
    application_directory = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_data_root()


def test_get_data_root_raises_error_if_directory_missing(clean_working_directory: Path) -> None:
    """Verifies that get_data_root raises an error if the cached directory does not exist."""
    set_data_root(path=clean_working_directory)

    # Simulates an out-of-date cache.
    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError, match=r"currently configured"):
        get_data_root()


def test_get_data_root_preserves_trailing_whitespace(clean_working_directory: Path) -> None:
    """Verifies that get_data_root preserves a trailing space in a newline-terminated path record."""
    spaced_directory = clean_working_directory.parent / "data root "
    spaced_directory.mkdir()
    path_file = clean_working_directory.parent / "app_data" / "data_root_path.txt"
    path_file.write_text(f"{spaced_directory}\n")

    assert get_data_root() == spaced_directory


def test_get_data_root_raises_error_if_record_is_whitespace(clean_working_directory: Path) -> None:
    """Verifies that get_data_root raises FileNotFoundError for a newline-only path record."""
    set_data_root(path=clean_working_directory)

    path_file = clean_working_directory.parent / "app_data" / "data_root_path.txt"
    path_file.write_text("\n")

    with pytest.raises(FileNotFoundError, match=r"cached path record\s+is empty"):
        get_data_root()


def test_set_task_templates_directory_creates_cache_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory caches the directory path."""
    application_directory = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    templates_directory = tmp_path / "templates"
    templates_directory.mkdir()

    set_task_templates_directory(path=templates_directory)

    cache_file = application_directory / "task_templates_directory_path.txt"
    assert cache_file.exists()
    assert cache_file.read_text() == str(templates_directory.resolve())


def test_set_task_templates_directory_raises_error_not_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that set_task_templates_directory raises an error for non-existent directory."""
    application_directory = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    nonexistent = tmp_path / "missing_dir"

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        set_task_templates_directory(path=nonexistent)


def test_set_task_templates_directory_raises_error_not_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that set_task_templates_directory raises an error when the path is a file."""
    application_directory = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    file_path = tmp_path / "a_file.txt"
    file_path.write_text("content")

    with pytest.raises(ValueError, match=r"does not point to a\s+directory"):
        set_task_templates_directory(path=file_path)


def test_get_task_templates_directory_returns_cached_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_task_templates_directory returns the cached directory path."""
    application_directory = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    templates_directory = tmp_path / "templates"
    templates_directory.mkdir()

    set_task_templates_directory(path=templates_directory)
    retrieved = get_task_templates_directory()

    assert retrieved == templates_directory.resolve()


def test_get_task_templates_directory_raises_error_if_not_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_task_templates_directory raises an error if not configured."""
    application_directory = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    with pytest.raises(FileNotFoundError, match=r"has not been set"):
        get_task_templates_directory()


def test_get_task_templates_directory_raises_error_if_directory_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_task_templates_directory raises an error if the cached directory was deleted."""
    application_directory = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    templates_directory = tmp_path / "templates"
    templates_directory.mkdir()

    set_task_templates_directory(path=templates_directory)
    shutil.rmtree(templates_directory)

    with pytest.raises(FileNotFoundError, match=r"does not exist"):
        get_task_templates_directory()


def test_get_task_templates_directory_preserves_trailing_whitespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_task_templates_directory preserves a trailing space in a newline-terminated path record."""
    application_directory = tmp_path / "app_data"
    application_directory.mkdir()
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    templates_directory = tmp_path / "task templates "
    templates_directory.mkdir()
    (application_directory / "task_templates_directory_path.txt").write_text(f"{templates_directory}\n")

    assert get_task_templates_directory() == templates_directory


def test_get_task_templates_directory_raises_error_if_record_is_whitespace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_task_templates_directory raises FileNotFoundError for a newline-only path record."""
    application_directory = tmp_path / "app_data"
    application_directory.mkdir()
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(application_directory))

    (application_directory / "task_templates_directory_path.txt").write_text("\n")

    with pytest.raises(FileNotFoundError, match=r"cached path record\s+is empty"):
        get_task_templates_directory()
