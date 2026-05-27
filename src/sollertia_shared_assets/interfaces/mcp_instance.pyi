from typing import Any
from pathlib import Path

from _typeshed import Incomplete
from ataraxis_data_structures import YamlConfig as YamlConfig

from ..data_classes import (
    SYSTEM_RAW_DATA_REGISTRY as SYSTEM_RAW_DATA_REGISTRY,
    SessionData as SessionData,
    RawDataFiles as RawDataFiles,
    SessionTypes as SessionTypes,
    RunTrainingDescriptor as RunTrainingDescriptor,
    LickTrainingDescriptor as LickTrainingDescriptor,
    MesoscopeHardwareState as MesoscopeHardwareState,
    WindowCheckingDescriptor as WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor as MesoscopeExperimentDescriptor,
)
from ..configuration import (
    EXPERIMENT_CONFIGURATION_REGISTRY as EXPERIMENT_CONFIGURATION_REGISTRY,
    AcquisitionSystems as AcquisitionSystems,
)

UNINITIALIZED_SESSION_MARKER: str
DESCRIPTOR_REGISTRY: dict[SessionTypes, type[YamlConfig]]
HARDWARE_STATE_REGISTRY: dict[AcquisitionSystems, type[YamlConfig]]

def _assert_registry_coverage() -> None: ...

mcp: Incomplete

def ok_response(**payload: Any) -> dict[str, Any]: ...
def error_response(message: str) -> dict[str, Any]: ...
def serialize(value: Any) -> Any: ...
def _describe_type(type_hint: Any) -> str: ...
def describe_dataclass(cls, *, recurse: bool = True) -> dict[str, Any]: ...
def write_yaml_validated(
    file_path: Path, payload: dict[str, Any], validator_cls: type[YamlConfig], *, overwrite: bool = False
) -> dict[str, Any]: ...
def read_yaml(file_path: Path, validator_cls: type[YamlConfig]) -> dict[str, Any]: ...
def resolve_root_directory(root_directory: str) -> tuple[Path | None, dict[str, Any] | None]: ...
def safe_iterdir(directory: Path) -> list[Path]: ...
def read_descriptor_incomplete(session: SessionData) -> tuple[bool | None, str | None]: ...
