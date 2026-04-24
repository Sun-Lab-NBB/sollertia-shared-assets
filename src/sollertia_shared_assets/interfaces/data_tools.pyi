from typing import Any
from pathlib import Path

from ataraxis_data_structures import YamlConfig as YamlConfig

from .mcp_instance import (
    CONFIGURATION_DIR as CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY as DESCRIPTOR_REGISTRY,
    DATASET_MARKER_FILENAME as DATASET_MARKER_FILENAME,
    HARDWARE_STATE_REGISTRY as HARDWARE_STATE_REGISTRY,
    UNINITIALIZED_SESSION_MARKER as UNINITIALIZED_SESSION_MARKER,
    mcp as mcp,
    read_yaml as read_yaml,
    serialize as serialize,
    ok_response as ok_response,
    error_response as error_response,
    describe_dataclass as describe_dataclass,
    write_yaml_validated as write_yaml_validated,
    resolve_root_directory as resolve_root_directory,
    read_descriptor_incomplete as read_descriptor_incomplete,
)
from ..data_classes import (
    DrugData as DrugData,
    Directories as Directories,
    ImplantData as ImplantData,
    SessionData as SessionData,
    SubjectData as SubjectData,
    SurgeryData as SurgeryData,
    RawDataFiles as RawDataFiles,
    SessionTypes as SessionTypes,
    InjectionData as InjectionData,
    ProcedureData as ProcedureData,
    filter_sessions as filter_sessions,
    session_root_from_marker as session_root_from_marker,
)
from ..configuration import AcquisitionSystems as AcquisitionSystems

_STATUS_KEYS: tuple[str, ...]

def get_data_root_overview_tool(root_directory: str) -> dict[str, Any]: ...
def inspect_sessions_tool(session_paths: list[str]) -> dict[str, Any]: ...
def filter_sessions_tool(
    sessions: list[dict[str, Any]],
    start_date: str | None = None,
    end_date: str | None = None,
    include_sessions: list[str] | None = None,
    exclude_sessions: list[str] | None = None,
    include_animals: list[str] | None = None,
    exclude_animals: list[str] | None = None,
    *,
    utc_timezone: bool = True,
) -> dict[str, Any]: ...
def read_session_data_tool(file_path: str) -> dict[str, Any]: ...
def write_session_data_tool(
    file_path: str, session_data_payload: dict[str, Any], *, overwrite: bool = True
) -> dict[str, Any]: ...
def describe_session_data_schema_tool() -> dict[str, Any]: ...
def read_session_descriptor_tool(file_path: str, session_type: str) -> dict[str, Any]: ...
def write_session_descriptor_tool(
    file_path: str, session_type: str, descriptor_payload: dict[str, Any], *, overwrite: bool = True
) -> dict[str, Any]: ...
def describe_session_descriptor_schema_tool(session_type: str) -> dict[str, Any]: ...
def read_session_hardware_state_tool(file_path: str, acquisition_system: str) -> dict[str, Any]: ...
def write_session_hardware_state_tool(
    file_path: str, acquisition_system: str, hardware_state_payload: dict[str, Any], *, overwrite: bool = True
) -> dict[str, Any]: ...
def describe_session_hardware_state_schema_tool(acquisition_system: str = "mesoscope") -> dict[str, Any]: ...
def read_surgery_data_tool(file_path: str) -> dict[str, Any]: ...
def write_surgery_data_tool(
    file_path: str, surgery_payload: dict[str, Any], *, overwrite: bool = True
) -> dict[str, Any]: ...
def describe_surgery_data_schema_tool() -> dict[str, Any]: ...
def _compute_session_status(instance: SessionData) -> tuple[str, bool, bool | None, bool, str | None]: ...
def _aggregate_projects(root: Path, sessions: list[dict[str, Any]]) -> list[dict[str, Any]]: ...
def _build_session_report(instance: SessionData, session_root: Path) -> dict[str, Any]: ...
def _raw_data_inventory(instance: SessionData) -> list[dict[str, Any]]: ...
def _processed_data_inventory(instance: SessionData) -> list[dict[str, Any]]: ...
def _required_asset_inventory(instance: SessionData, session_type: SessionTypes) -> list[dict[str, Any]]: ...
def _resolve_descriptor_class(session_type: str) -> type[YamlConfig] | dict[str, Any]: ...
def _resolve_hardware_state_class(acquisition_system: str) -> type[YamlConfig] | dict[str, Any]: ...
def _resolve_session_root(session_path: str) -> tuple[Path | None, dict[str, Any] | None]: ...
