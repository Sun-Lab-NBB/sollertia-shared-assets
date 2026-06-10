"""Provides assets for creating, discovering, and accessing the Sollertia platform project data hierarchy across all
data acquisition and processing machines.
"""

from .session_data import (
    RAW_DATA_DIRECTORY,
    PROCESSED_DATA_DIRECTORY,
    RawData,
    Directories,
    SessionData,
    RawDataFiles,
    ProcessedData,
    ProcessingTrackers,
)
from .project_hierarchy import (
    DATASET_MARKER_FILENAME,
    PERSISTENT_DATA_DIRECTORY,
    AnimalData,
    ProjectData,
)
from .session_discovery import (
    filter_sessions,
    iterate_sessions,
    discover_projects,
    discover_sessions,
    validate_directory,
    iter_animal_sessions,
    iter_project_animals,
    get_projects_for_animal,
    parse_session_timestamp,
    get_session_root_from_marker,
)

__all__ = [
    "DATASET_MARKER_FILENAME",
    "PERSISTENT_DATA_DIRECTORY",
    "PROCESSED_DATA_DIRECTORY",
    "RAW_DATA_DIRECTORY",
    "AnimalData",
    "Directories",
    "ProcessedData",
    "ProcessingTrackers",
    "ProjectData",
    "RawData",
    "RawDataFiles",
    "SessionData",
    "discover_projects",
    "discover_sessions",
    "filter_sessions",
    "get_projects_for_animal",
    "get_session_root_from_marker",
    "iter_animal_sessions",
    "iter_project_animals",
    "iterate_sessions",
    "parse_session_timestamp",
    "validate_directory",
]
