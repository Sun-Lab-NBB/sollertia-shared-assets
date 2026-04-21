"""Provides helpers for discovering and filtering Sollertia sessions under a project root."""

from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime
from zoneinfo import ZoneInfo

from dateutil import parser

from .session_data import SessionData, RawDataFiles

if TYPE_CHECKING:
    from pathlib import Path
    from collections.abc import Iterable, Iterator

_SESSION_NAME_COMPONENTS: int = 7
"""The number of hyphen-separated components in a valid session name (YYYY-MM-DD-HH-MM-SS-microseconds)."""


def iterate_sessions(root_path: Path) -> Iterator[SessionData]:
    """Discovers and lazily loads every ``SessionData`` instance under the target root directory.

    Composes ``discover_sessions`` with ``SessionData.load`` so that callers can switch from
    project-wide ``rglob`` scans to typed iteration in a single call. The returned iterator yields
    sessions in the same sorted order as ``discover_sessions``.

    Args:
        root_path: The absolute path to the directory to search recursively for session markers.

    Yields:
        Each ``SessionData`` instance loaded from a session marker found under ``root_path``.
    """
    for session_root in discover_sessions(root_path=root_path):
        yield SessionData.load(session_path=session_root)


def discover_sessions(root_path: Path) -> list[Path]:
    """Discovers session root directories under a root path by locating ``session_data.yaml`` markers.

    Recursively searches for ``RawDataFiles.SESSION_DATA`` markers and derives each session's root
    directory from the marker location. Returns only the resolved paths without loading or validating
    session data, making this function suitable as a lightweight discovery primitive for both MCP
    tools and internal pipeline code.

    Args:
        root_path: The absolute path to the directory to search recursively.

    Returns:
        A sorted list of absolute paths to session root directories found under ``root_path``.

    Raises:
        PermissionError: If the search encounters a directory it cannot read.
    """
    return sorted(session_root_from_marker(marker=marker) for marker in root_path.rglob(RawDataFiles.SESSION_DATA))


def session_root_from_marker(marker: Path) -> Path:
    """Returns the session root directory from a ``session_data.yaml`` marker path.

    The marker lives at ``{session_root}/raw_data/session_data.yaml``, so the session root is two
    directory levels above the marker file.

    Args:
        marker: The absolute path to a ``session_data.yaml`` file.

    Returns:
        The path to the session root directory (the grandparent of the marker).
    """
    return marker.parents[1]


def filter_sessions(
    sessions: Iterable[tuple[str, str]],
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    include_sessions: set[str] | None = None,
    exclude_sessions: set[str] | None = None,
    include_animals: set[str] | None = None,
    exclude_animals: set[str] | None = None,
    utc_timezone: bool = True,
) -> set[tuple[str, str]]:
    """Filters ``(session_name, animal)`` pairs by date range and inclusion-exclusion criteria.

    Provides a general-purpose filtering mechanism for selecting a subset of sessions. Animal filtering
    is applied before session filtering. Exclusion filtering takes precedence over inclusion filtering.

    Notes:
        The input is intentionally a plain iterable of ``(session_name, animal)`` tuples rather than a
        richer type. Callers with domain-specific session types (e.g. forgery's ``DatasetSession``) map
        their sets to tuples on the way in and rehydrate on the way out with a one-line comprehension.

    Args:
        sessions: An iterable of ``(session_name, animal)`` string tuples. The first element is the
            canonical session name (``YYYY-MM-DD-HH-MM-SS-microseconds``); the second is the animal
            identifier.
        start_date: The start date for the date range filter. Sessions recorded on or after this date
            are included. Accepts formats like ``YYYY-MM-DD`` or ``YYYY-MM-DD HH:MM:SS``. When
            ``None``, no start bound is applied.
        end_date: The end date for the date range filter. Sessions recorded on or before this date
            are included. Date-only values include the entire day. When ``None``, no end bound is
            applied.
        include_sessions: Session names to include regardless of the date range. Sessions in this set
            are added even when they fall outside the ``start_date`` / ``end_date`` range, unless they
            are also in ``exclude_sessions``.
        exclude_sessions: Session names to exclude from the results. Takes precedence over every
            other inclusion criterion.
        include_animals: Animal identifiers to include. When provided, only sessions from these
            animals are considered. When ``None``, sessions from all animals are considered.
        exclude_animals: Animal identifiers to exclude. Takes precedence over ``include_animals``.
        utc_timezone: Determines whether to interpret date boundaries and session timestamps in UTC
            (True) or America/New_York (False). Session names reflect UTC timestamps; when this flag
            is False, timestamps are converted to America/New_York before comparison.

    Returns:
        A set of ``(session_name, animal)`` tuples matching every filter.
    """
    filtered: set[tuple[str, str]] = set(sessions)

    # Applies the animal exclusion filter first (takes precedence over animal inclusion).
    if exclude_animals:
        filtered = {(session, animal) for session, animal in filtered if animal not in exclude_animals}

    if include_animals:
        filtered = {(session, animal) for session, animal in filtered if animal in include_animals}

    # Applies the session exclusion filter (takes precedence over all session inclusion criteria).
    if exclude_sessions:
        filtered = {(session, animal) for session, animal in filtered if session not in exclude_sessions}

    # Applies date range and session inclusion filters. Sessions are included if they fall within the
    # date range OR are in include_sessions.
    if start_date is not None or end_date is not None or include_sessions:
        parsed_start = (
            _parse_date_boundary(date_string=start_date, is_end_date=False, utc_timezone=utc_timezone)
            if start_date
            else None
        )
        parsed_end = (
            _parse_date_boundary(date_string=end_date, is_end_date=True, utc_timezone=utc_timezone)
            if end_date
            else None
        )

        matched: set[tuple[str, str]] = set()
        for session, animal in filtered:
            # Explicit inclusion bypasses the date range check.
            if include_sessions and session in include_sessions:
                matched.add((session, animal))
                continue

            session_date = _parse_session_date(session_name=session, utc_timezone=utc_timezone)
            if session_date is None:
                continue
            if parsed_start is not None and session_date < parsed_start:
                continue
            if parsed_end is not None and session_date > parsed_end:
                continue
            matched.add((session, animal))

        filtered = matched

    return filtered


def _parse_date_boundary(date_string: str, *, is_end_date: bool = False, utc_timezone: bool = True) -> datetime:
    """Parses a date or datetime string into a timezone-aware boundary.

    Args:
        date_string: A date and time string in various formats (``YYYY-MM-DD`` or with time).
        is_end_date: Determines whether to set the time component to the end of the day when only a
            date (no time) is provided. Used to make the end bound inclusive of the entire day.
        utc_timezone: Determines whether to interpret the input string as UTC. When False, interprets
            it as America/New_York.

    Returns:
        A timezone-aware datetime constructed from the input string.
    """
    parsed = parser.parse(timestr=date_string)

    # Detects a date-only input so that end bounds can be rolled forward to the end of the day.
    date_only = "T" not in date_string and " " not in date_string and ":" not in date_string

    if date_only and is_end_date:
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)

    target_tz = ZoneInfo("UTC") if utc_timezone else ZoneInfo("America/New_York")

    return parsed.replace(tzinfo=target_tz) if parsed.tzinfo is None else parsed.astimezone(tz=target_tz)


def _parse_session_date(session_name: str, *, utc_timezone: bool = True) -> datetime | None:
    """Parses a Sollertia session name and returns its acquisition datetime.

    Session names follow the format ``YYYY-MM-DD-HH-MM-SS-microseconds`` and encode the acquisition
    timestamp in UTC.

    Args:
        session_name: The unique identifier of the session.
        utc_timezone: Determines whether to return the datetime in UTC. When False, converts to
            America/New_York.

    Returns:
        A timezone-aware datetime representing when the session was acquired, or ``None`` when the
        session name does not follow the expected format.
    """
    parts = session_name.split(sep="-")
    if len(parts) != _SESSION_NAME_COMPONENTS:
        return None

    try:
        year, month, day, hour, minute, second, microseconds = parts
        utc_dt = datetime(
            year=int(year),
            month=int(month),
            day=int(day),
            hour=int(hour),
            minute=int(minute),
            second=int(second),
            microsecond=int(microseconds),
            tzinfo=ZoneInfo("UTC"),
        )
    except ValueError, IndexError:
        return None

    if utc_timezone:
        return utc_dt
    return utc_dt.astimezone(tz=ZoneInfo("America/New_York"))
