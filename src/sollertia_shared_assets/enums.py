"""Provides the cross-system enumerations that define the Sollertia platform vocabulary: acquisition systems, session
types, external read assets, and credentials categories.

This module is a leaf: it imports nothing from the rest of the library, so every other module — shared,
system-specific, or interface — can use the enumerations without creating circular imports. The dispatch registries
keyed by these enumerations are all defined in the ``registries`` module.
"""

from enum import StrEnum


class AcquisitionSystems(StrEnum):
    """Defines the data acquisition systems supported by the Sollertia platform.

    Every Sollertia acquisition system runs in Virtual Reality, presenting a Unity task in the linear infinite
    corridor. Each acquisition runtime package owns its own system configuration classes; this enum remains the shared
    vocabulary that identifies which runtime a session or dataset was acquired on.
    """

    MESOSCOPE_VR = "mesoscope"
    """Uses the 2-Photon Random Access Mesoscope (2P-RAM) from Thor-Labs and a heavily modified Janelia / Allen
    hardware harness."""


class SessionTypes(StrEnum):
    """Defines the data acquisition session types supported by all data acquisition systems in the Sollertia
    platform.
    """

    LICK_TRAINING = "lick training"
    """Teaches animals to use the water delivery port while being head-fixed on the Mesoscope-VR system."""
    RUN_TRAINING = "run training"
    """Teaches animals to run on the treadmill while being head-fixed on the Mesoscope-VR system."""
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    """Runs virtual reality tasks using Unity game engine and collects brain activity data using the 2-Photon Random
    Access Mesoscope (2P-RAM)."""
    WINDOW_CHECKING = "window checking"
    """Evaluates the quality of the cranial window implantation procedure and the suitability of the animal for
    experiment sessions using the Mesoscope."""


class ReadAssets(StrEnum):
    """Enumerates the external data-asset formats the platform reads and caches as on-disk dataclasses.

    Each member's string value is the canonical identifier for the read-asset format. Members are durable translation
    contracts added by Sollertia platform maintainers together with a matching ``READ_ASSET_REGISTRY`` entry; this is
    a platform-contract surface, not a routine extension point.
    """

    SURGERY_DATA = "surgery_data"
    """The animal's surgical-intervention record read from the platform surgery log and stored on disk as
    ``SurgeryData`` (canonical filename ``surgery_metadata.yaml``)."""


class CredentialsTypes(StrEnum):
    """Enumerates the credentials categories supported by the Sollertia platform.

    Each member's string value is the canonical identifier for the credentials' category. Members are durable
    contracts added by Sollertia platform maintainers together with a matching ``CREDENTIALS_FILE_REGISTRY`` entry;
    this is a platform-contract surface, not a routine extension point.
    """

    GOOGLE = "google"
    """The Google service account credentials used for all interactions with the Google Sheets API (canonical
    filename ``google_credentials.json``)."""
