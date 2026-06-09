"""Contains tests for the extension-point hub and import-time checks provided by the ``data_classes.extensions``
module.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from sollertia_shared_assets.data_classes import (
    DESCRIPTOR_REGISTRY,
    READ_ASSET_REGISTRY,
    HARDWARE_STATE_REGISTRY,
    SYSTEM_RAW_DATA_REGISTRY,
    ReadAssets,
    SessionTypes,
    extensions,
)
from sollertia_shared_assets.configuration import EXPERIMENT_CONFIGURATION_REGISTRY, AcquisitionSystems


def test_descriptor_registry_covers_every_session_type() -> None:
    """Verifies DESCRIPTOR_REGISTRY has an entry for every SessionTypes member."""
    assert set(DESCRIPTOR_REGISTRY) == set(SessionTypes)


def test_per_system_registries_cover_every_acquisition_system() -> None:
    """Verifies the per-system dispatch registries cover every AcquisitionSystems member."""
    for registry in (HARDWARE_STATE_REGISTRY, EXPERIMENT_CONFIGURATION_REGISTRY, SYSTEM_RAW_DATA_REGISTRY):
        assert set(registry) == set(AcquisitionSystems)


def test_read_asset_registry_covers_every_read_asset() -> None:
    """Verifies READ_ASSET_REGISTRY has an entry for every ReadAssets member."""
    assert set(READ_ASSET_REGISTRY) == set(ReadAssets)


def test_assert_registry_coverage_passes_for_current_state() -> None:
    """Verifies the import-time coverage check passes for the current registry wiring."""
    extensions._assert_registry_coverage()


def test_assert_registry_coverage_raises_on_missing_descriptor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the coverage check raises and names the registry when a session type lacks a descriptor entry."""
    monkeypatch.setattr(extensions, "DESCRIPTOR_REGISTRY", {})
    with pytest.raises(RuntimeError, match=r"DESCRIPTOR_REGISTRY is missing"):
        extensions._assert_registry_coverage()


def test_assert_descriptor_contract_passes_for_current_state() -> None:
    """Verifies every registered descriptor declares the incomplete field."""
    extensions._assert_descriptor_contract()


def test_assert_descriptor_contract_raises_on_missing_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the descriptor-contract check raises when a registered descriptor omits the incomplete field."""

    @dataclass
    class _DescriptorMissingIncomplete:
        experimenter: str = ""

    monkeypatch.setattr(extensions, "DESCRIPTOR_REGISTRY", {SessionTypes.LICK_TRAINING: _DescriptorMissingIncomplete})
    with pytest.raises(RuntimeError, match=r"missing the required 'incomplete' field"):
        extensions._assert_descriptor_contract()


def test_assert_vr_template_registry_consistency_passes_for_current_state() -> None:
    """Verifies the VR-template registry consistency check passes for the current wiring."""
    extensions._assert_vr_template_registry_consistency()


def test_assert_vr_template_registry_consistency_raises_on_unregistered_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies the consistency check raises when a from_task_template builder is not registered for its system."""
    monkeypatch.setattr(extensions, "VR_TEMPLATE_CONFIG_REGISTRY", {})
    with pytest.raises(RuntimeError, match=r"VR_TEMPLATE_CONFIG_REGISTRY is missing an entry"):
        extensions._assert_vr_template_registry_consistency()
