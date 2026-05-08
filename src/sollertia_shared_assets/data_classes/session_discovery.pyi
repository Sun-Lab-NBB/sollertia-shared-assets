from pathlib import Path
from datetime import datetime
from collections.abc import Iterable, Iterator

from .session_data import (
    SessionData as SessionData,
    RawDataFiles as RawDataFiles,
)

_SESSION_NAME_COMPONENTS: int

def validate_directory(directory: str) -> str | None: ...
def iterate_sessions(root_path: Path) -> Iterator[SessionData]: ...
def discover_sessions(root_path: Path) -> list[Path]: ...
def session_root_from_marker(marker: Path) -> Path: ...
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
) -> set[tuple[str, str]]: ...
def _parse_date_boundary(date_string: str, *, is_end_date: bool = False, utc_timezone: bool = True) -> datetime: ...
def _parse_session_date(session_name: str, *, utc_timezone: bool = True) -> datetime | None: ...
