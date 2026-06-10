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
