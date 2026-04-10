from typing import Any
from pathlib import Path

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig as YamlConfig

from ..data_classes import (
    SessionTypes as SessionTypes,
    RunTrainingDescriptor as RunTrainingDescriptor,
    LickTrainingDescriptor as LickTrainingDescriptor,
    WindowCheckingDescriptor as WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor as MesoscopeExperimentDescriptor,
)
from ..configuration import get_system_configuration_data as get_system_configuration_data

SESSION_MARKER_FILENAME: str
DATASET_MARKER_FILENAME: str
INCOMPLETE_SESSION_MARKER: str
CONFIGURATION_DIR: str
DESCRIPTOR_REGISTRY: dict[SessionTypes, tuple[str, type[YamlConfig]]]
mcp: Incomplete

def ok_response(**payload: Any) -> dict[str, Any]: ...
def error_response(message: str) -> dict[str, Any]: ...
def serialize(value: Any) -> Any: ...
def _describe_type(type_hint: Any) -> str: ...
def describe_dataclass(cls, *, recurse: bool = True) -> dict[str, Any]: ...
def write_yaml_validated(
    file_path: Path,
    payload: dict[str, Any],
    validator_cls: type[YamlConfig],
    *,
    overwrite: bool = False,
    use_save_method: bool = False,
) -> dict[str, Any]: ...
def read_yaml(file_path: Path, validator_cls: type[YamlConfig]) -> dict[str, Any]: ...
def resolve_root_directory(root_directory: str | None) -> tuple[Path | None, dict[str, Any] | None]: ...
def session_root_from_marker(marker: Path) -> Path: ...
def safe_iterdir(directory: Path) -> list[Path]: ...
