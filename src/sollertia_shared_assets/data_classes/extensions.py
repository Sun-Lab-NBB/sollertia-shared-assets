"""Collects every sollertia-shared-assets extension point in one place and runs the import-time checks that guard them.

This module is the single canonical surface for extending the library with a new acquisition system, session type,
runtime trial, trigger type, or external read asset. It gathers — in one file — every dispatch registry, the
system/session-type association, the VR-task gate, and the enums that key them, alongside the import-time assertions
that verify each enum member is fully wired.

Several registries are *defined* next to the type they dispatch and are only re-exported here, because relocating their
definitions would create circular imports.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import fields

from ataraxis_base_utilities import console

from .read_assets import READ_ASSET_REGISTRY, ReadAssets
from .session_data import (
    SYSTEM_SESSION_TYPES,
    SYSTEM_RAW_DATA_REGISTRY,
    SESSION_TYPES_USING_VR_TASK,
    SessionTypes,
)
from ..configuration import (
    VR_TEMPLATE_CONFIG_REGISTRY,
    EXPERIMENT_CONFIGURATION_REGISTRY,
    TriggerType,
    AcquisitionSystems,
)
from .mesoscope_runtime_data import (
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)

if TYPE_CHECKING:
    from enum import StrEnum

    from ataraxis_data_structures import YamlConfig

__all__ = [
    "DESCRIPTOR_REGISTRY",
    "EXPERIMENT_CONFIGURATION_REGISTRY",
    "HARDWARE_STATE_REGISTRY",
    "READ_ASSET_REGISTRY",
    "SESSION_TYPES_USING_VR_TASK",
    "SYSTEM_RAW_DATA_REGISTRY",
    "SYSTEM_SESSION_TYPES",
    "VR_TEMPLATE_CONFIG_REGISTRY",
    "AcquisitionSystems",
    "ReadAssets",
    "SessionTypes",
    "TriggerType",
]

DESCRIPTOR_REGISTRY: dict[SessionTypes, type[YamlConfig]] = {
    SessionTypes.LICK_TRAINING: LickTrainingDescriptor,
    SessionTypes.RUN_TRAINING: RunTrainingDescriptor,
    SessionTypes.MESOSCOPE_EXPERIMENT: MesoscopeExperimentDescriptor,
    SessionTypes.WINDOW_CHECKING: WindowCheckingDescriptor,
}
"""Maps each session type to its descriptor dataclass. The canonical on-disk filename is always the flat
``session_descriptor.yaml`` (``RawDataFiles.SESSION_DESCRIPTOR``) regardless of session type — the only thing that
varies per type is the parsing class."""

HARDWARE_STATE_REGISTRY: dict[AcquisitionSystems, type[YamlConfig]] = {
    AcquisitionSystems.MESOSCOPE_VR: MesoscopeHardwareState,
}
"""Maps each acquisition system to its hardware-state dataclass. The canonical on-disk filename is always
``hardware_state.yaml`` (``RawDataFiles.HARDWARE_STATE``) regardless of system — the only thing that varies is the
parsing class. Future acquisition systems register here."""


def _assert_registry_coverage() -> None:
    """Verifies at import time that every ``SessionTypes``, ``AcquisitionSystems``, and ``ReadAssets`` member has an
    entry in each dispatch registry. Also verifies that ``SYSTEM_SESSION_TYPES`` pairs every acquisition system with
    at least one session type and claims every session type under at least one system.

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


def _assert_vr_template_registry_consistency() -> None:
    """Verifies at import time that ``VR_TEMPLATE_CONFIG_REGISTRY`` and ``EXPERIMENT_CONFIGURATION_REGISTRY`` agree on
    which acquisition systems build their experiment configuration from a Unity VR task template.

    An experiment configuration class that provides a ``from_task_template`` builder must be registered in
    ``VR_TEMPLATE_CONFIG_REGISTRY`` for ``create_experiment_from_vr_template_tool`` to dispatch to it; conversely,
    every registered system must actually provide that builder. ``VR_TEMPLATE_CONFIG_REGISTRY`` is optional and sits
    outside the dispatch-registry coverage check. Without this guard a system that implements ``from_task_template``
    but forgets to register would pass import and parity yet have its template-based creation tool silently refuse it.

    Raises:
        RuntimeError: If a system provides ``from_task_template`` but is not registered, or is registered but does not
            provide ``from_task_template``, naming the offending system so extenders can locate the mismatch.
    """
    for system, configuration_class in EXPERIMENT_CONFIGURATION_REGISTRY.items():
        provides_builder = callable(getattr(configuration_class, "from_task_template", None))
        is_registered = system in VR_TEMPLATE_CONFIG_REGISTRY
        if provides_builder and not is_registered:
            message = (
                f"VR_TEMPLATE_CONFIG_REGISTRY is missing an entry for {system.name}. Its experiment configuration "
                f"class provides a from_task_template builder, so it must be registered here for "
                f"create_experiment_from_vr_template_tool to dispatch to it. See the README's 'Adding New Acquisition "
                f"Systems' Step 6."
            )
            console.error(message=message, error=RuntimeError)
        if is_registered and not provides_builder:
            message = (
                f"VR_TEMPLATE_CONFIG_REGISTRY registers {system.name}, but its experiment configuration class does not "
                f"provide a from_task_template builder. Either implement the builder or remove the registry entry."
            )
            console.error(message=message, error=RuntimeError)


_assert_registry_coverage()
_assert_descriptor_contract()
_assert_vr_template_registry_consistency()
