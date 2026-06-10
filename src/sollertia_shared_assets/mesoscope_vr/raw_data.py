"""Provides the Mesoscope-VR raw-data layout assets: the canonical filename and subdirectory enumerations and the
dataclass that resolves the system-specific raw-asset paths of a session.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from pathlib import Path


class MesoscopeRawDataFiles(StrEnum):
    """Enumerates the canonical filenames at the root of a session's ``raw_data`` directory that are written
    exclusively by the Mesoscope-VR acquisition system.
    """

    ZABER_POSITIONS = "zaber_positions.yaml"
    """The Zaber motor position snapshot written at session start by the Mesoscope-VR acquisition runtime."""
    MESOSCOPE_POSITIONS = "mesoscope_positions.yaml"
    """The Mesoscope objective position snapshot written at session start by the Mesoscope-VR acquisition runtime."""
    WINDOW_SCREENSHOT = "window_screenshot.png"
    """The cranial imaging window screenshot captured at session start by the Mesoscope-VR acquisition runtime."""


class MesoscopeDirectories(StrEnum):
    """Enumerates the canonical names of subdirectories under a session's ``raw_data`` directory that are written
    exclusively by the Mesoscope-VR acquisition system.
    """

    MESOSCOPE_DATA = "mesoscope_data"
    """Persistent mesoscope data directory under ``raw_data``. Stores LERC-compressed TIFF stacks and acquisition
    metadata written by sollertia-experiment's preprocessing."""


@dataclass(slots=True)
class MesoscopeRawData:
    """Stores the absolute paths to the Mesoscope-VR-specific raw assets of a single data acquisition session.

    Notes:
        Instances are constructed by ``SessionData._build_sub_dataclasses`` when the session's acquisition_system is
        AcquisitionSystems.MESOSCOPE_VR. The ``build`` classmethod is the single source of truth for the
        enum-to-field mapping.
    """

    zaber_positions_path: Path
    """Captures the states of the Zaber motorized stages used by the Mesoscope-VR system at the start of the
    session."""
    mesoscope_positions_path: Path
    """Records the 2-Photon Random Access Mesoscope (2P-RAM) objective position used to image the cranial window
    during the session, allowing the same imaging field of view to be recovered in follow-up sessions."""
    window_screenshot_path: Path
    """Provides a visual reference of the cranial imaging window taken at the start of the session, used for
    downstream registration and quality assessment."""
    mesoscope_data_path: Path
    """Holds the compressed 2-Photon Random Access Mesoscope (2P-RAM) acquisition output and accompanying metadata
    produced by sollertia-experiment's preprocessing, which serves as the input to cindra's neural imaging analysis
    pipelines."""

    @classmethod
    def build(cls, root: Path) -> MesoscopeRawData:
        """Builds a MesoscopeRawData instance with every field resolved against the input raw data root.

        Args:
            root: The path to the session's ``raw_data`` directory.

        Returns:
            A MesoscopeRawData instance whose fields are absolute paths under the input root.
        """
        return cls(
            zaber_positions_path=root.joinpath(MesoscopeRawDataFiles.ZABER_POSITIONS),
            mesoscope_positions_path=root.joinpath(MesoscopeRawDataFiles.MESOSCOPE_POSITIONS),
            window_screenshot_path=root.joinpath(MesoscopeRawDataFiles.WINDOW_SCREENSHOT),
            mesoscope_data_path=root.joinpath(MesoscopeDirectories.MESOSCOPE_DATA),
        )
