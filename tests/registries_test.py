"""Contains tests for the dispatch registries and import-time checks provided by the ``registries`` module."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from sollertia_shared_assets import registries
from sollertia_shared_assets import MesoscopeExperimentConfiguration
from sollertia_shared_assets.enums import (
    ReadAssets,
    SessionTypes,
    CredentialsTypes,
    AcquisitionSystems,
)
from sollertia_shared_assets.registries import (
    DESCRIPTOR_REGISTRY,
    READ_ASSET_REGISTRY,
    HARDWARE_STATE_REGISTRY,
    SYSTEM_RAW_DATA_REGISTRY,
    CREDENTIALS_FILE_REGISTRY,
    EXPERIMENT_CONFIGURATION_REGISTRY,
    resolve_read_asset,
)
from sollertia_shared_assets.data_classes import SurgeryData


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


def test_credentials_file_registry_covers_every_credentials_type() -> None:
    """Verifies CREDENTIALS_FILE_REGISTRY has an entry for every CredentialsTypes member."""
    assert set(CREDENTIALS_FILE_REGISTRY) == set(CredentialsTypes)


def test_resolve_read_asset_returns_registered_class() -> None:
    """Verifies that resolve_read_asset resolves both members and string values to the registered dataclass."""
    assert resolve_read_asset(read_asset=ReadAssets.SURGERY_DATA) is SurgeryData
    assert resolve_read_asset(read_asset="surgery_data") is SurgeryData


def test_resolve_read_asset_raises_error_unknown_format() -> None:
    """Verifies that resolve_read_asset raises ValueError for unsupported read-asset formats."""
    with pytest.raises(ValueError, match=r"Unable to resolve the read-asset format"):
        resolve_read_asset(read_asset="unsupported")


def test_assert_registry_coverage_passes_for_current_state() -> None:
    """Verifies the import-time coverage check passes for the current registry wiring."""
    registries._assert_registry_coverage()


def test_assert_registry_coverage_raises_on_missing_descriptor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the coverage check raises and names the registry when a session type lacks a descriptor entry."""
    monkeypatch.setattr(registries, "DESCRIPTOR_REGISTRY", {})
    with pytest.raises(RuntimeError, match=r"DESCRIPTOR_REGISTRY is missing"):
        registries._assert_registry_coverage()


def test_assert_registry_coverage_raises_on_missing_credentials_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the coverage check raises when a credentials category lacks a canonical filename entry."""
    monkeypatch.setattr(registries, "CREDENTIALS_FILE_REGISTRY", {})
    with pytest.raises(RuntimeError, match=r"CREDENTIALS_FILE_REGISTRY is missing"):
        registries._assert_registry_coverage()


def test_assert_descriptor_contract_passes_for_current_state() -> None:
    """Verifies every registered descriptor declares the incomplete field."""
    registries._assert_descriptor_contract()


def test_assert_descriptor_contract_raises_on_missing_incomplete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the descriptor-contract check raises when a registered descriptor omits the incomplete field."""

    @dataclass
    class _DescriptorMissingIncomplete:
        experimenter: str = ""

    monkeypatch.setattr(registries, "DESCRIPTOR_REGISTRY", {SessionTypes.LICK_TRAINING: _DescriptorMissingIncomplete})
    with pytest.raises(RuntimeError, match=r"missing the required 'incomplete' field"):
        registries._assert_descriptor_contract()


def test_assert_experiment_configuration_contract_passes_for_current_state() -> None:
    """Verifies every registered experiment configuration satisfies the contract."""
    registries._assert_experiment_configuration_contract()


def test_assert_experiment_configuration_contract_raises_on_missing_field(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the contract check raises when a registered configuration omits a contract field."""

    @dataclass
    class _ConfigurationMissingScene:
        experiment_states: dict[str, object]
        trial_structures: dict[str, object]

        @classmethod
        def from_task_template(cls) -> object:
            """Stub builder so only the missing field trips the check; the contract check only verifies it is
            callable and never invokes it."""
            return cls(experiment_states={}, trial_structures={})

    monkeypatch.setattr(
        registries,
        "EXPERIMENT_CONFIGURATION_REGISTRY",
        {AcquisitionSystems.MESOSCOPE_VR: _ConfigurationMissingScene},
    )
    with pytest.raises(RuntimeError, match=r"do not satisfy the experiment-configuration contract"):
        registries._assert_experiment_configuration_contract()


def test_assert_experiment_configuration_contract_raises_on_missing_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies the contract check raises when a registered configuration omits the from_task_template builder."""

    @dataclass
    class _ConfigurationMissingBuilder:
        experiment_states: dict[str, object]
        trial_structures: dict[str, object]
        unity_scene_name: str

    monkeypatch.setattr(
        registries,
        "EXPERIMENT_CONFIGURATION_REGISTRY",
        {AcquisitionSystems.MESOSCOPE_VR: _ConfigurationMissingBuilder},
    )
    with pytest.raises(RuntimeError, match=r"from_task_template builder"):
        registries._assert_experiment_configuration_contract()


def test_experiment_builder_signature_gaps_passes_for_real_builder() -> None:
    """Verifies the real MesoscopeExperimentConfiguration builder satisfies the creation tool's call convention."""
    gaps = registries._experiment_builder_signature_gaps(
        builder=MesoscopeExperimentConfiguration.from_task_template,
        contract_parameters=("template", "unity_scene_name", "state_count"),
    )
    assert gaps == []


def test_experiment_builder_signature_gaps_flags_missing_contract_parameter() -> None:
    """Verifies the signature check flags a builder that omits a contract parameter."""

    def builder(template: object, unity_scene_name: str) -> None:
        """Stub builder missing the state_count contract parameter."""

    gaps = registries._experiment_builder_signature_gaps(
        builder=builder, contract_parameters=("template", "unity_scene_name", "state_count")
    )
    assert "the 'state_count' parameter on from_task_template" in gaps


def test_experiment_builder_signature_gaps_flags_parameter_without_default() -> None:
    """Verifies the signature check flags a system-specific parameter that declares no default."""

    def builder(template: object, unity_scene_name: str, state_count: int, reward_size: float) -> None:
        """Stub builder whose reward_size parameter has no default."""

    gaps = registries._experiment_builder_signature_gaps(
        builder=builder, contract_parameters=("template", "unity_scene_name", "state_count")
    )
    assert "a default for the 'reward_size' parameter on from_task_template" in gaps


def test_experiment_builder_signature_gaps_flags_positional_only_contract_parameter() -> None:
    """Verifies the signature check flags a contract parameter the creation tool cannot supply by keyword."""

    def builder(template: object, /, unity_scene_name: str = "", state_count: int = 1) -> None:
        """Stub builder whose template parameter is positional-only."""

    gaps = registries._experiment_builder_signature_gaps(
        builder=builder, contract_parameters=("template", "unity_scene_name", "state_count")
    )
    assert "keyword access to the 'template' parameter on from_task_template" in gaps


def test_experiment_builder_signature_gaps_accepts_variadic_keywords() -> None:
    """Verifies a builder that accepts arbitrary keyword arguments satisfies the contract-parameter requirement."""

    def builder(**parameters: object) -> None:
        """Stub builder that accepts every contract parameter through variadic keywords."""

    gaps = registries._experiment_builder_signature_gaps(
        builder=builder, contract_parameters=("template", "unity_scene_name", "state_count")
    )
    assert gaps == []


def test_assert_experiment_configuration_contract_raises_on_incompatible_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies the contract check raises when a builder cannot be called with the creation tool's keyword arguments."""

    @dataclass
    class _ConfigurationIncompatibleBuilder:
        experiment_states: dict[str, object]
        trial_structures: dict[str, object]
        unity_scene_name: str

        @classmethod
        def from_task_template(cls, template: object) -> object:
            """Stub builder missing the unity_scene_name and state_count contract parameters."""
            return cls(experiment_states={}, trial_structures={}, unity_scene_name="")

    monkeypatch.setattr(
        registries,
        "EXPERIMENT_CONFIGURATION_REGISTRY",
        {AcquisitionSystems.MESOSCOPE_VR: _ConfigurationIncompatibleBuilder},
    )
    with pytest.raises(RuntimeError, match=r"parameter on from_task_template"):
        registries._assert_experiment_configuration_contract()
