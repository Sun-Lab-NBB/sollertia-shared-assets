from typing import Any, Protocol
from pathlib import Path

from ataraxis_data_structures import YamlConfig

from .enums import ReadAssets, SessionTypes, CredentialsTypes, AcquisitionSystems

__all__ = [
    "CREDENTIALS_FILE_REGISTRY",
    "DESCRIPTOR_REGISTRY",
    "EXPERIMENT_CONFIGURATION_REGISTRY",
    "HARDWARE_STATE_REGISTRY",
    "READ_ASSET_REGISTRY",
    "SESSION_TYPES_USING_VR_TASK",
    "SYSTEM_RAW_DATA_REGISTRY",
    "SYSTEM_SESSION_TYPES",
    "resolve_read_asset",
]

class _SystemRawDataBuilder(Protocol):
    @classmethod
    def build(cls, root: Path) -> Any: ...

DESCRIPTOR_REGISTRY: dict[SessionTypes, type[YamlConfig]]
HARDWARE_STATE_REGISTRY: dict[AcquisitionSystems, type[YamlConfig]]
EXPERIMENT_CONFIGURATION_REGISTRY: dict[AcquisitionSystems, type[YamlConfig]]
SYSTEM_RAW_DATA_REGISTRY: dict[AcquisitionSystems, type[_SystemRawDataBuilder]]
SYSTEM_SESSION_TYPES: dict[AcquisitionSystems, frozenset[SessionTypes]]
SESSION_TYPES_USING_VR_TASK: frozenset[SessionTypes]
READ_ASSET_REGISTRY: dict[ReadAssets, type[YamlConfig]]
CREDENTIALS_FILE_REGISTRY: dict[CredentialsTypes, str]

def resolve_read_asset(read_asset: str | ReadAssets) -> type[YamlConfig]: ...
