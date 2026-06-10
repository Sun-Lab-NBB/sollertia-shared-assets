"""Collects every sollertia-shared-assets dispatch registry in one place and runs the import-time checks that guard
them.

This module is the single canonical surface for wiring new capabilities into the library, and it holds two governance
tiers. The system registries — descriptor, hardware state, experiment configuration, system raw data, the
system/session-type association, and the corridor-task gate — form the designed extension point: they grow whenever a
new acquisition system or session type is added, following the recipe owned by the /library-extension skill. The
contract registries — read assets and credentials — are durable translation contracts curated by Sollertia platform
maintainers; adding an entry there is a platform-contract decision, not a routine extension.

The module imports each acquisition system's subpackage (``mesoscope_vr`` and its future siblings) and wires the
system's classes into the registries, so the shared configuration and data modules never import from a system
subpackage. The keying enumerations live in the leaf ``enums`` module, which keeps this module importable by every
registry consumer without circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
from dataclasses import fields

from ataraxis_base_utilities import console

from .enums import (
    ReadAssets,
    SessionTypes,
    CredentialsTypes,
    AcquisitionSystems,
)
from .data_classes import SurgeryData
from .mesoscope_vr import (
    MesoscopeRawData,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
    MesoscopeExperimentConfiguration,
)

if TYPE_CHECKING:
    from enum import StrEnum
    from pathlib import Path

    from ataraxis_data_structures import YamlConfig

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
    """Structural type for system-specific raw data dataclasses registered in ``SYSTEM_RAW_DATA_REGISTRY``."""

    @classmethod
    def build(cls, root: Path) -> Any:  # noqa: ANN401
        """Resolves all system-specific raw-asset paths under the session's ``raw_data`` directory.

        Conforming implementations construct and return a dataclass instance whose fields hold absolute paths
        anchored on ``root``. The concrete return type is the implementing class itself (e.g., ``MesoscopeRawData``).

        Args:
            root: The session's ``raw_data`` directory absolute path.

        Returns:
            An instance of the conforming dataclass with every system-specific raw-asset path resolved.
        """
        ...  # pragma: no cover


DESCRIPTOR_REGISTRY: dict[SessionTypes, type[YamlConfig]] = {
    SessionTypes.LICK_TRAINING: LickTrainingDescriptor,
    SessionTypes.RUN_TRAINING: RunTrainingDescriptor,
    SessionTypes.MESOSCOPE_EXPERIMENT: MesoscopeExperimentDescriptor,
    SessionTypes.WINDOW_CHECKING: WindowCheckingDescriptor,
}
"""Maps each session type to its descriptor dataclass. The canonical on-disk filename is always the flat
``session_descriptor.yaml`` (``RawDataFiles.SESSION_DESCRIPTOR``) regardless of session type — the only thing that
varies per type is the parsing class. The registry is deliberately flat: a session type maps to exactly one descriptor
platform-wide, so an acquisition system that needs a different descriptor must mint a new ``SessionTypes`` member."""

HARDWARE_STATE_REGISTRY: dict[AcquisitionSystems, type[YamlConfig]] = {
    AcquisitionSystems.MESOSCOPE_VR: MesoscopeHardwareState,
}
"""Maps each acquisition system to its hardware-state dataclass. The canonical on-disk filename is always
``hardware_state.yaml`` (``RawDataFiles.HARDWARE_STATE``) regardless of system — only the parsing class varies."""

EXPERIMENT_CONFIGURATION_REGISTRY: dict[AcquisitionSystems, type[YamlConfig]] = {
    AcquisitionSystems.MESOSCOPE_VR: MesoscopeExperimentConfiguration,
}
"""Maps each acquisition system to its experiment configuration dataclass. Every registered class satisfies the
experiment-configuration contract; the configuration and template-creation tools dispatch through this registry."""

# noinspection PyTypeChecker
SYSTEM_RAW_DATA_REGISTRY: dict[AcquisitionSystems, type[_SystemRawDataBuilder]] = {
    AcquisitionSystems.MESOSCOPE_VR: MesoscopeRawData,
}
"""Maps each acquisition system to the dataclass that captures its system-specific raw assets. The registered class
exposes a ``build(root: Path) -> Self`` classmethod that resolves all system-specific paths under the session's
``raw_data`` directory."""

SYSTEM_SESSION_TYPES: dict[AcquisitionSystems, frozenset[SessionTypes]] = {
    AcquisitionSystems.MESOSCOPE_VR: frozenset(
        {
            SessionTypes.LICK_TRAINING,
            SessionTypes.RUN_TRAINING,
            SessionTypes.MESOSCOPE_EXPERIMENT,
            SessionTypes.WINDOW_CHECKING,
        }
    ),
}
"""Maps each acquisition system to the set of session types it can run. ``SessionData.create()`` rejects a session
type that is not paired with the session's acquisition system."""

SESSION_TYPES_USING_VR_TASK: frozenset[SessionTypes] = frozenset({SessionTypes.MESOSCOPE_EXPERIMENT})
"""The session types that run the linear infinite corridor task and therefore write a ``vr_configuration.yaml``
task-template snapshot. ``SessionData.required_raw_assets`` consults this set to decide whether a session of a given
type requires the snapshot. Training and window-checking sessions run no task and are absent here."""

READ_ASSET_REGISTRY: dict[ReadAssets, type[YamlConfig]] = {
    ReadAssets.SURGERY_DATA: SurgeryData,
}
"""Maps each read-asset format to the dataclass that represents it on disk. This contract registry is curated by
Sollertia platform maintainers; each entry is a durable contract for translating an external data shape into the
uniform on-disk format the downstream Sollertia libraries consume."""

CREDENTIALS_FILE_REGISTRY: dict[CredentialsTypes, str] = {
    CredentialsTypes.GOOGLE: "google_credentials.json",
}
"""Maps each credentials category to the canonical filename under which its credentials file is stored inside the
working directory's credentials subdirectory. This contract registry is curated by Sollertia platform maintainers;
the credentials toolset that consumes it lives in the top-level ``credentials`` module."""


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


def _assert_registry_coverage() -> None:
    """Verifies at import time that every ``SessionTypes``, ``AcquisitionSystems``, ``ReadAssets``, and
    ``CredentialsTypes`` member has an entry in each dispatch registry. Also verifies that ``SYSTEM_SESSION_TYPES``
    pairs every acquisition system with at least one session type and claims every session type under at least one
    system.

    Raises:
        RuntimeError: If any registry is missing entries for known enum members, or if ``SYSTEM_SESSION_TYPES`` leaves
            an acquisition system or a session type unpaired. The error message names the offending registry and the
            missing members so extenders can immediately locate the unwired touch point.
    """
    coverage_checks: tuple[tuple[str, frozenset[StrEnum], frozenset[StrEnum]], ...] = (
        ("DESCRIPTOR_REGISTRY", frozenset(SessionTypes), frozenset(DESCRIPTOR_REGISTRY)),
        ("HARDWARE_STATE_REGISTRY", frozenset(AcquisitionSystems), frozenset(HARDWARE_STATE_REGISTRY)),
        (
            "EXPERIMENT_CONFIGURATION_REGISTRY",
            frozenset(AcquisitionSystems),
            frozenset(EXPERIMENT_CONFIGURATION_REGISTRY),
        ),
        ("SYSTEM_RAW_DATA_REGISTRY", frozenset(AcquisitionSystems), frozenset(SYSTEM_RAW_DATA_REGISTRY)),
        ("READ_ASSET_REGISTRY", frozenset(ReadAssets), frozenset(READ_ASSET_REGISTRY)),
        ("CREDENTIALS_FILE_REGISTRY", frozenset(CredentialsTypes), frozenset(CREDENTIALS_FILE_REGISTRY)),
    )
    for registry_name, expected, actual in coverage_checks:
        missing = expected - actual
        if missing:
            missing_names = ", ".join(sorted(member.name for member in missing))
            message = (
                f"{registry_name} is missing entries for {missing_names}. Every enum member must have a registered "
                f"dispatch class. See the README's 'Adding New Session Types' / 'Adding New Acquisition Systems' / "
                f"'Adding a New Read Asset' sections for the full extension touch list."
            )
            console.error(message=message, error=RuntimeError)

    # SYSTEM_SESSION_TYPES is an association (system -> session-type set), not a dispatch registry, so it is checked
    # separately. Every acquisition system must declare at least one session type, and every session type must be
    # claimed by at least one system; either gap would let SessionData.create reject a legitimate session or admit an
    # unrunnable one.
    systems_missing_session_types = frozenset(AcquisitionSystems) - frozenset(SYSTEM_SESSION_TYPES)
    if systems_missing_session_types:
        missing_names = ", ".join(sorted(member.name for member in systems_missing_session_types))
        message = (
            f"SYSTEM_SESSION_TYPES is missing entries for {missing_names}. Every acquisition system must declare the "
            f"session types it can run. See the README's 'Adding New Acquisition Systems' section."
        )
        console.error(message=message, error=RuntimeError)
    claimed_session_types: frozenset[SessionTypes] = frozenset().union(*SYSTEM_SESSION_TYPES.values())
    orphan_session_types = frozenset(SessionTypes) - claimed_session_types
    if orphan_session_types:
        orphan_names = ", ".join(sorted(member.name for member in orphan_session_types))
        message = (
            f"SYSTEM_SESSION_TYPES does not claim {orphan_names}. Every session type must be supported by at least one "
            f"acquisition system. See the README's 'Adding New Session Types' section."
        )
        console.error(message=message, error=RuntimeError)


def _assert_descriptor_contract() -> None:
    """Verifies at import time that every descriptor dataclass registered in ``DESCRIPTOR_REGISTRY`` declares the
    ``incomplete`` field.

    The session-inspection tooling reads ``incomplete`` (via ``read_descriptor_incomplete``) to decide whether a
    session's data is complete and eligible for unsupervised processing. The dispatch-registry coverage check only
    confirms a key is present, not that the descriptor satisfies this field contract. A new descriptor that omits
    ``incomplete`` would otherwise fail only at runtime when the inspection tooling reads a session of its type.

    Raises:
        RuntimeError: If any registered descriptor dataclass omits the ``incomplete`` field, naming the offending
            session types so extenders can locate the descriptor to fix.
    """
    missing = sorted(
        session_type.name
        for session_type, descriptor_class in DESCRIPTOR_REGISTRY.items()
        if "incomplete" not in {field_definition.name for field_definition in fields(descriptor_class)}
    )
    if missing:
        missing_names = ", ".join(missing)
        message = (
            f"DESCRIPTOR_REGISTRY descriptors are missing the required 'incomplete' field for {missing_names}. Every "
            f"session descriptor must declare 'incomplete: bool = True'; the session-inspection tooling reads this "
            f"field to decide whether a session's data is complete and eligible for unsupervised processing."
        )
        console.error(message=message, error=RuntimeError)


def _assert_experiment_configuration_contract() -> None:
    """Verifies at import time that every class in ``EXPERIMENT_CONFIGURATION_REGISTRY`` satisfies the
    experiment-configuration contract: the ``experiment_states``, ``trial_structures``, and ``unity_scene_name``
    fields and a ``from_task_template`` classmethod. Without it a half-wired configuration would fail only at runtime
    when ``create_experiment_from_vr_template_tool`` builds a configuration for its system.

    Raises:
        RuntimeError: If any registered configuration class omits a required contract field or the
            ``from_task_template`` builder, naming the offending acquisition systems.
    """
    required_fields: tuple[str, ...] = ("experiment_states", "trial_structures", "unity_scene_name")
    offenders: list[str] = []
    for system, configuration_class in EXPERIMENT_CONFIGURATION_REGISTRY.items():
        declared_fields = {field_definition.name for field_definition in fields(configuration_class)}
        gaps = [field_name for field_name in required_fields if field_name not in declared_fields]
        if not callable(getattr(configuration_class, "from_task_template", None)):
            gaps.append("from_task_template builder")
        if gaps:
            offenders.append(f"{system.name} (missing {', '.join(gaps)})")
    if offenders:
        offender_names = "; ".join(sorted(offenders))
        message = (
            f"EXPERIMENT_CONFIGURATION_REGISTRY classes do not satisfy the experiment-configuration contract for "
            f"{offender_names}. Every experiment configuration must declare the 'experiment_states', "
            f"'trial_structures', and 'unity_scene_name' fields and provide a 'from_task_template' classmethod. See "
            f"the README's 'Adding New Acquisition Systems' section."
        )
        console.error(message=message, error=RuntimeError)


_assert_registry_coverage()
_assert_descriptor_contract()
_assert_experiment_configuration_contract()
