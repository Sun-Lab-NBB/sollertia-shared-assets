"""Provides the registry of external data assets the platform READS and caches as on-disk dataclasses."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from ataraxis_base_utilities import console

from .surgery_data import SurgeryData

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig


class ReadAssets(StrEnum):
    """Enumerates the external data-asset formats the platform reads and caches as on-disk dataclasses.

    Each member's string value is the canonical identifier for the read-asset format. Downstream consumers extend
    this enumeration (together with ``READ_ASSET_REGISTRY``) to wire additional external read assets into the
    platform.
    """

    SURGERY_DATA = "surgery_data"
    """The animal's surgical-intervention record read from the platform surgery log and stored on disk as
    ``SurgeryData`` (canonical filename ``surgery_metadata.yaml``)."""


READ_ASSET_REGISTRY: dict[ReadAssets, type[YamlConfig]] = {
    ReadAssets.SURGERY_DATA: SurgeryData,
}
"""Maps each read-asset format to the dataclass that represents it on disk.

This is the single extension point for the read-asset system: register a new format by adding its ``ReadAssets``
member and the dataclass it resolves to here. The import-time parity check (``_assert_registry_coverage`` in
``interfaces/mcp_instance.py``) enforces that every ``ReadAssets`` member has a registered dataclass, so a half-wired
extension fails fast at import.
"""


def resolve_read_asset(read_asset: str | ReadAssets) -> type[YamlConfig]:
    """Resolves a read-asset format identifier to the dataclass that represents it on disk.

    Args:
        read_asset: A ``ReadAssets`` member or its string value (e.g., ``"surgery_data"``).

    Returns:
        The dataclass registered for the format in ``READ_ASSET_REGISTRY``.

    Raises:
        ValueError: If the identifier is not a valid ``ReadAssets`` member.
    """
    if read_asset not in ReadAssets:
        valid = ", ".join(member.value for member in ReadAssets)
        message = (
            f"Unable to resolve the read-asset format '{read_asset}'. Expected one of the supported ReadAssets "
            f"members: {valid}."
        )
        console.error(message=message, error=ValueError)
        # Unreachable: console.error() is NoReturn, but ruff cannot trace NoReturn through method calls (RET503).
        # noinspection PyUnreachableCode
        raise ValueError(message)  # pragma: no cover

    return READ_ASSET_REGISTRY[ReadAssets(read_asset)]
