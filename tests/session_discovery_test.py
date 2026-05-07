"""Contains tests for the session-discovery helpers in ``data_classes.session_discovery``."""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from sollertia_shared_assets.data_classes import (
    SessionData,
    SessionTypes,
    filter_sessions,
    iterate_sessions,
    discover_sessions,
    validate_directory,
    session_root_from_marker,
)
from sollertia_shared_assets.data_classes.session_discovery import (
    _parse_session_date,
    _parse_date_boundary,
)

if TYPE_CHECKING:
    from pathlib import Path


_SESSION_YAML_TEMPLATE = """\
project_name: {project}
animal_id: {animal}
session_name: {session}
session_type: {session_type}
acquisition_system: mesoscope
python_version: "3.14.4"
sollertia_experiment_version: "5.0.0"
raw_data: null
processed_data: null
"""


def _write_session(
    root: Path,
    project: str,
    animal: str,
    session: str,
    session_type: str = "lick training",
) -> Path:
    """Writes a minimal ``session_data.yaml`` marker and returns the session root directory."""
    session_root = root / project / animal / session
    raw_data = session_root / "raw_data"
    raw_data.mkdir(parents=True)
    (raw_data / "session_data.yaml").write_text(
        _SESSION_YAML_TEMPLATE.format(project=project, animal=animal, session=session, session_type=session_type)
    )
    return session_root


@pytest.fixture
def populated_project_tree(tmp_path: Path) -> Path:
    """Creates a small multi-animal project tree with several sessions and returns the data root."""
    root = tmp_path / "data"
    _write_session(root, "proj_a", "1", "2026-03-01-12-00-00-000000", "lick training")
    _write_session(root, "proj_a", "1", "2026-03-05-12-00-00-000000", "run training")
    _write_session(root, "proj_a", "2", "2026-03-10-12-00-00-000000", "mesoscope experiment")
    _write_session(root, "proj_b", "3", "2026-03-15-12-00-00-000000", "window checking")
    return root


def test_validate_directory_returns_none_for_existing_directory(tmp_path: Path) -> None:
    """Verifies that validate_directory returns None when the path points to a real directory."""
    assert validate_directory(directory=str(tmp_path)) is None


def test_validate_directory_reports_missing_path(tmp_path: Path) -> None:
    """Verifies that validate_directory returns a ``does not exist`` error for a missing path."""
    missing = tmp_path / "does_not_exist"

    result = validate_directory(directory=str(missing))

    assert result is not None
    assert "does not exist" in result
    assert str(missing) in result


def test_validate_directory_reports_non_directory_path(tmp_path: Path) -> None:
    """Verifies that validate_directory returns a ``not a directory`` error for a file path."""
    file_path = tmp_path / "a_file.txt"
    file_path.write_text("")

    result = validate_directory(directory=str(file_path))

    assert result is not None
    assert "not a directory" in result
    assert str(file_path) in result


def test_session_root_from_marker_returns_grandparent(tmp_path: Path) -> None:
    """Verifies that session_root_from_marker strips the ``raw_data/session_data.yaml`` suffix."""
    marker = tmp_path / "proj" / "animal" / "2026-03-01-12-00-00-000000" / "raw_data" / "session_data.yaml"
    marker.parent.mkdir(parents=True)
    marker.touch()

    assert session_root_from_marker(marker=marker) == marker.parent.parent


def test_discover_sessions_returns_sorted_roots(populated_project_tree: Path) -> None:
    """Verifies that discover_sessions returns the session root directories in sorted order."""
    paths = discover_sessions(root_path=populated_project_tree)

    assert len(paths) == 4
    assert paths == sorted(paths)
    assert all(path.is_dir() for path in paths)
    assert all(path.name.startswith("2026-03") for path in paths)


def test_discover_sessions_empty_root_returns_empty_list(tmp_path: Path) -> None:
    """Verifies that discover_sessions handles a root with no session markers."""
    assert discover_sessions(root_path=tmp_path) == []


def test_iterate_sessions_yields_loaded_session_data(populated_project_tree: Path) -> None:
    """Verifies that iterate_sessions lazily loads each SessionData instance it finds."""
    sessions = list(iterate_sessions(root_path=populated_project_tree))

    assert len(sessions) == 4
    assert all(isinstance(session, SessionData) for session in sessions)
    session_types = {session.session_type for session in sessions}
    assert session_types == {
        SessionTypes.LICK_TRAINING,
        SessionTypes.RUN_TRAINING,
        SessionTypes.MESOSCOPE_EXPERIMENT,
        SessionTypes.WINDOW_CHECKING,
    }


def test_filter_sessions_preserves_input_when_no_filters_applied() -> None:
    """Verifies that filter_sessions is a no-op when every filter is None / empty."""
    keys = {
        ("2026-03-01-12-00-00-000000", "1"),
        ("2026-03-05-12-00-00-000000", "2"),
    }

    assert filter_sessions(sessions=keys) == keys


def test_filter_sessions_exclude_animals_takes_precedence_over_include_animals() -> None:
    """Verifies that exclude_animals overrides include_animals for the same animal id."""
    keys = {
        ("2026-03-01-12-00-00-000000", "1"),
        ("2026-03-02-12-00-00-000000", "2"),
    }

    result = filter_sessions(sessions=keys, include_animals={"1", "2"}, exclude_animals={"1"})

    assert result == {("2026-03-02-12-00-00-000000", "2")}


def test_filter_sessions_exclude_sessions_takes_precedence_over_include_sessions() -> None:
    """Verifies that exclude_sessions overrides include_sessions for the same session name."""
    keys = {
        ("2026-03-01-12-00-00-000000", "1"),
        ("2026-03-02-12-00-00-000000", "1"),
    }
    include = {"2026-03-01-12-00-00-000000", "2026-03-02-12-00-00-000000"}
    exclude = {"2026-03-01-12-00-00-000000"}

    result = filter_sessions(sessions=keys, include_sessions=include, exclude_sessions=exclude)

    assert result == {("2026-03-02-12-00-00-000000", "1")}


def test_filter_sessions_date_range_bounds_are_inclusive() -> None:
    """Verifies that start_date and end_date include sessions on the boundary days."""
    keys = {
        ("2026-03-01-00-00-00-000000", "1"),
        ("2026-03-05-12-00-00-000000", "1"),
        ("2026-03-10-23-59-59-999999", "1"),
        ("2026-03-15-12-00-00-000000", "1"),
    }

    result = filter_sessions(sessions=keys, start_date="2026-03-05", end_date="2026-03-10")

    assert result == {
        ("2026-03-05-12-00-00-000000", "1"),
        ("2026-03-10-23-59-59-999999", "1"),
    }


def test_filter_sessions_include_sessions_bypass_date_range() -> None:
    """Verifies that include_sessions overrides the date range filter for listed session names."""
    keys = {
        ("2026-03-01-12-00-00-000000", "1"),
        ("2026-03-20-12-00-00-000000", "1"),
    }

    result = filter_sessions(
        sessions=keys,
        start_date="2026-03-05",
        end_date="2026-03-10",
        include_sessions={"2026-03-20-12-00-00-000000"},
    )

    assert result == {("2026-03-20-12-00-00-000000", "1")}


def test_filter_sessions_drops_malformed_session_names() -> None:
    """Verifies that sessions whose names cannot be parsed as dates are dropped under a date filter."""
    keys = {
        ("2026-03-01-12-00-00-000000", "1"),
        ("not-a-real-session-name", "1"),
    }

    result = filter_sessions(sessions=keys, start_date="2026-03-01")

    assert result == {("2026-03-01-12-00-00-000000", "1")}


def test_filter_sessions_america_new_york_timezone_handling() -> None:
    """Verifies that utc_timezone=False shifts session timestamps to America/New_York for comparison.

    A session name of ``2026-03-02-03-30-00-000000`` is 03:30 UTC on March 2, which is 23:30 EST on
    March 1. With ``utc_timezone=False`` and ``end_date="2026-03-01"``, the session should fall within
    the March 1 end-of-day boundary once converted to America/New_York.
    """
    keys = {("2026-03-02-03-30-00-000000", "1")}

    included = filter_sessions(sessions=keys, end_date="2026-03-01", utc_timezone=False)
    excluded = filter_sessions(sessions=keys, end_date="2026-03-01", utc_timezone=True)

    assert included == keys
    assert excluded == set()


def test_parse_session_date_valid_utc() -> None:
    """Verifies that a well-formed session name parses to a UTC-aware datetime."""
    parsed = _parse_session_date(session_name="2026-03-15-14-30-45-123456")

    assert parsed == datetime(2026, 3, 15, 14, 30, 45, 123456, tzinfo=ZoneInfo("UTC"))


def test_parse_session_date_converts_to_new_york_when_requested() -> None:
    """Verifies that utc_timezone=False converts the parsed datetime to America/New_York."""
    parsed = _parse_session_date(session_name="2026-03-15-14-30-45-123456", utc_timezone=False)

    assert parsed is not None
    assert parsed.tzinfo == ZoneInfo("America/New_York")
    assert parsed.hour == 10  # UTC 14:30 = EDT 10:30 on March 15 2026 (DST in effect).


@pytest.mark.parametrize(
    "malformed",
    [
        "2026-03-15-14-30-45",  # Six components instead of seven.
        "2026-03-15-14-30-45-abcdef",  # Non-numeric microseconds.
        "not-a-session",  # Entirely wrong format.
    ],
)
def test_parse_session_date_returns_none_for_malformed_input(malformed: str) -> None:
    """Verifies that _parse_session_date returns None for session names that cannot be parsed."""
    assert _parse_session_date(session_name=malformed) is None


def test_parse_date_boundary_date_only_rolls_end_to_end_of_day() -> None:
    """Verifies that is_end_date=True pushes a date-only string to the end of the day."""
    parsed = _parse_date_boundary(date_string="2026-03-15", is_end_date=True)

    assert parsed.hour == 23
    assert parsed.minute == 59
    assert parsed.second == 59
    assert parsed.microsecond == 999999


def test_parse_date_boundary_date_only_keeps_start_at_midnight() -> None:
    """Verifies that is_end_date=False leaves a date-only string at midnight."""
    parsed = _parse_date_boundary(date_string="2026-03-15", is_end_date=False)

    assert parsed.hour == 0
    assert parsed.minute == 0
    assert parsed.second == 0


def test_parse_date_boundary_respects_utc_flag() -> None:
    """Verifies that utc_timezone switches the attached ZoneInfo between UTC and America/New_York."""
    utc_parsed = _parse_date_boundary(date_string="2026-03-15", utc_timezone=True)
    local_parsed = _parse_date_boundary(date_string="2026-03-15", utc_timezone=False)

    assert utc_parsed.tzinfo == ZoneInfo("UTC")
    assert local_parsed.tzinfo == ZoneInfo("America/New_York")
