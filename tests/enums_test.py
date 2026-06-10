"""Contains tests for the cross-system enumerations provided by the ``enums`` module."""

from __future__ import annotations

from sollertia_shared_assets.enums import (
    ReadAssets,
    SessionTypes,
    CredentialsTypes,
    AcquisitionSystems,
)


def test_acquisition_systems_mesoscope_vr_value() -> None:
    """Verifies the MESOSCOPE_VR acquisition system enumeration value."""
    assert AcquisitionSystems.MESOSCOPE_VR == "mesoscope"
    assert str(AcquisitionSystems.MESOSCOPE_VR) == "mesoscope"


def test_acquisition_systems_is_string_enum() -> None:
    """Verifies that AcquisitionSystems inherits from StrEnum."""
    assert isinstance(AcquisitionSystems.MESOSCOPE_VR, str)


def test_session_types_values() -> None:
    """Verifies all SessionTypes enumeration values."""
    assert SessionTypes.LICK_TRAINING == "lick training"
    assert SessionTypes.RUN_TRAINING == "run training"
    assert SessionTypes.MESOSCOPE_EXPERIMENT == "mesoscope experiment"
    assert SessionTypes.WINDOW_CHECKING == "window checking"


def test_session_types_is_string_enum() -> None:
    """Verifies that SessionTypes inherits from StrEnum."""
    assert isinstance(SessionTypes.LICK_TRAINING, str)
    assert isinstance(SessionTypes.RUN_TRAINING, str)
    assert isinstance(SessionTypes.MESOSCOPE_EXPERIMENT, str)
    assert isinstance(SessionTypes.WINDOW_CHECKING, str)


def test_read_assets_surgery_data_value() -> None:
    """Verifies the SURGERY_DATA read-asset enumeration value."""
    assert ReadAssets.SURGERY_DATA == "surgery_data"
    assert isinstance(ReadAssets.SURGERY_DATA, str)


def test_credentials_types_google_value() -> None:
    """Verifies the GOOGLE credentials category enumeration value."""
    assert CredentialsTypes.GOOGLE == "google"
    assert isinstance(CredentialsTypes.GOOGLE, str)
