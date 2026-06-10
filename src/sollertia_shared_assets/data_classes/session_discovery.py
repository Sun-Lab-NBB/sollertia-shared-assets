"""Provides helpers for discovering and filtering Sollertia sessions under a project root."""

from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from dateutil import parser

from .session_data import SessionData, RawDataFiles
from ..configuration import CONFIGURATION_DIRECTORY
from .project_hierarchy import (
    DATASET_MARKER_FILENAME,
    AnimalData,
    ProjectData,
)

if TYPE_CHECKING:
    from typing import Literal
    from collections.abc import Iterable, Iterator

_SESSION_NAME_COMPONENTS: int = 7
"""The number of hyphen-separated components in a valid session name (YYYY-MM-DD-HH-MM-SS-microseconds)."""


def validate_directory(directory: str) -> str | None:
    """Checks that the given path string refers to an existing directory.

    Provides a lightweight existence check for MCP tool and pipeline call sites that already have a
    caller-supplied path and only need a boolean-shaped verdict. Returns ``None`` when the path is a
    valid directory, or a human-readable error string suitable for inclusion in an MCP tool response.

    Args:
        directory: The absolute path string to validate as an existing directory.

    Returns:
        ``None`` when the path points to an existing directory, otherwise a human-readable error
        message.
    """
    path = Path(directory)
    if not path.exists():
        return f"Unable to validate the input directory. The path {directory} does not exist."
    if not path.is_dir():
        return f"Unable to validate the input directory. The path {directory} is not a directory."
    return None


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
    return sorted(get_session_root_from_marker(marker=marker) for marker in root_path.rglob(RawDataFiles.SESSION_DATA))


def get_session_root_from_marker(marker: Path) -> Path:
    """Returns the session root directory from a ``session_data.yaml`` marker path.

    The marker lives at ``{session_root}/raw_data/session_data.yaml``, so the session root is two
    directory levels above the marker file.

    Args:
        marker: The absolute path to a ``session_data.yaml`` file.

    Returns:
        The path to the session root directory (the grandparent of the marker).
    """
    return marker.parents[1]


def discover_projects(root_path: Path, strategy: Literal["markers", "directories"] = "markers") -> list[ProjectData]:
    """Discovers the projects under a data root and returns them as ``ProjectData`` views.

    The ``markers`` strategy is authoritative: it loads every session marker and buckets projects by their
    ``SessionData`` identity, so only projects that hold at least one session surface and stray directories
    cannot appear as phantom projects. The ``directories`` strategy lists the project directories directly,
    which also surfaces projects that hold no sessions yet, at the cost of trusting the directory layout.

    Args:
        root_path: The absolute path to the data root to scan.
        strategy: Whether to derive projects from session markers (``markers``) or from the directory layout
            (``directories``).

    Returns:
        A list of ``ProjectData`` views anchored on the data root, sorted by project name.
    """
    if strategy == "directories":
        return _discover_projects_by_directory(root_path=root_path)

    project_names = {session.project_name for session in iterate_sessions(root_path=root_path)}
    return [ProjectData(root=root_path, project_name=name) for name in sorted(project_names)]


def iter_project_animals(project: ProjectData) -> Iterator[AnimalData]:
    """Discovers the animal directories under a project and yields them as ``AnimalData`` views.

    Enumeration is directory-based, so animals that hold no sessions yet are included. The project's
    configuration directory, dataset directories, and hidden directories are skipped because they are not
    animals.

    Args:
        project: The ``ProjectData`` view whose animal directories are discovered.

    Yields:
        Each ``AnimalData`` view for an animal directory under the project, in sorted order.
    """
    project_path = project.path
    if not project_path.is_dir():
        return
    for child in sorted(project_path.iterdir()):
        if _is_animal_directory(path=child):
            yield project.animal(animal_id=child.name)


def iter_animal_sessions(animal: AnimalData) -> Iterator[Path]:
    """Discovers the session directories under an animal and yields their root paths.

    Enumeration is directory-based: child directories whose names parse as session timestamps are yielded as
    session roots, so sessions are surfaced without reading any markers. This complements the marker-based
    ``discover_sessions`` for callers that already know the animal hierarchy and want to avoid a recursive scan.
    Non-session children, such as the persistent-data directory and hidden directories, do not parse as session
    names and are therefore skipped.

    Args:
        animal: The ``AnimalData`` view whose session directories are discovered.

    Yields:
        Each session root path under the animal, in sorted order.
    """
    animal_path = animal.path
    if not animal_path.is_dir():
        return
    for child in sorted(animal_path.iterdir()):
        if child.is_dir() and parse_session_timestamp(session_name=child.name) is not None:
            yield child


def get_projects_for_animal(root_path: Path, animal_id: str) -> tuple[str, ...]:
    """Returns the names of all projects under the data root that include the given animal.

    Project membership is derived from session markers, so a project is reported only when it holds at
    least one session for the animal.

    Args:
        root_path: The absolute path to the data root to scan.
        animal_id: The unique identifier of the animal whose projects are discovered.

    Returns:
        A sorted tuple of project names that include the animal.
    """
    matching_projects = {
        session.project_name for session in iterate_sessions(root_path=root_path) if session.animal_id == animal_id
    }
    return tuple(sorted(matching_projects))


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
            (True) or the host machine's local time (False). Session names reflect UTC timestamps; when
            this flag is False, timestamps are converted to local time before comparison.

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

            session_date = parse_session_timestamp(session_name=session, utc_timezone=utc_timezone)
            if session_date is None:
                continue
            if parsed_start is not None and session_date < parsed_start:
                continue
            if parsed_end is not None and session_date > parsed_end:
                continue
            matched.add((session, animal))

        filtered = matched

    return filtered


def parse_session_timestamp(session_name: str, *, utc_timezone: bool = True) -> datetime | None:
    """Parses a Sollertia session name and returns its acquisition datetime.

    Session names follow the format ``YYYY-MM-DD-HH-MM-SS-microseconds`` and encode the acquisition
    timestamp in UTC. Returns ``None`` rather than raising when the name does not follow this format, so
    callers can skip non-conforming directory names during discovery walks.

    Args:
        session_name: The unique identifier of the session.
        utc_timezone: Determines whether to return the datetime in UTC. When False, converts to
            the host machine's local time.

    Returns:
        A timezone-aware datetime representing when the session was acquired, or ``None`` when the
        session name does not follow the expected format.
    """
    parts = session_name.split(sep="-")
    if len(parts) != _SESSION_NAME_COMPONENTS:
        return None

    try:
        year, month, day, hour, minute, second, microseconds = parts
        utc_datetime = datetime(
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
        return utc_datetime
    return utc_datetime.astimezone()


def _discover_projects_by_directory(root_path: Path) -> list[ProjectData]:
    """Lists the project directories directly under the data root.

    Args:
        root_path: The absolute path to the data root to scan.

    Returns:
        A list of ``ProjectData`` views for the non-hidden directories directly under the root, sorted by name.
    """
    if not root_path.is_dir():
        return []
    return [
        ProjectData(root=root_path, project_name=child.name)
        for child in sorted(root_path.iterdir())
        if child.is_dir() and not child.name.startswith(".")
    ]


def _is_animal_directory(path: Path) -> bool:
    """Returns whether the given path is an animal directory under a project.

    The project's configuration directory, dataset directories (those holding a dataset marker), and hidden
    directories are not animals and therefore return False.

    Args:
        path: The candidate child path of a project directory.

    Returns:
        True when the path is a directory that represents an animal rather than configuration or a dataset.
    """
    if not path.is_dir():
        return False
    if path.name.startswith("."):
        return False
    if path.name == CONFIGURATION_DIRECTORY:
        return False
    return not path.joinpath(DATASET_MARKER_FILENAME).exists()


def _parse_date_boundary(date_string: str, *, is_end_date: bool = False, utc_timezone: bool = True) -> datetime:
    """Parses a date or datetime string into a timezone-aware boundary.

    Args:
        date_string: A date and time string in various formats (``YYYY-MM-DD`` or with time).
        is_end_date: Determines whether to set the time component to the end of the day when only a
            date (no time) is provided. Used to make the end bound inclusive of the entire day.
        utc_timezone: Determines whether to interpret the input string as UTC. When False, interprets
            it as the host machine's local time.

    Returns:
        A timezone-aware datetime constructed from the input string.
    """
    parsed = parser.parse(timestr=date_string)

    # Detects a date-only input so that end bounds can be rolled forward to the end of the day.
    date_only = "T" not in date_string and " " not in date_string and ":" not in date_string

    if date_only and is_end_date:
        parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Interprets the boundary in UTC for internal comparison, or in the host machine's local time when the caller
    # requests human-facing local boundaries.
    if utc_timezone:
        utc_zone = ZoneInfo("UTC")
        return parsed.replace(tzinfo=utc_zone) if parsed.tzinfo is None else parsed.astimezone(tz=utc_zone)

    # A naive boundary is assumed to already be in local time; an aware boundary is converted to local time.
    return parsed.astimezone()
