"""Contains tests for the Mesoscope-VR raw-data layout assets in ``mesoscope_vr.raw_data``."""

from __future__ import annotations

from pathlib import Path

from sollertia_shared_assets.mesoscope_vr import (
    MesoscopeRawData,
    MesoscopeDirectories,
    MesoscopeRawDataFiles,
)

_SENTINEL_RAW_PATH: Path = Path("/sentinel/raw")
"""Placeholder raw_data root used by path-resolution tests; never touched on disk."""


def test_mesoscope_raw_data_build_resolves_all_paths() -> None:
    """Verifies that build() resolves every Mesoscope-VR-specific raw asset path against the input root."""
    raw_data = MesoscopeRawData.build(root=_SENTINEL_RAW_PATH)

    assert raw_data.zaber_positions_path == _SENTINEL_RAW_PATH / MesoscopeRawDataFiles.ZABER_POSITIONS
    assert raw_data.mesoscope_positions_path == _SENTINEL_RAW_PATH / MesoscopeRawDataFiles.MESOSCOPE_POSITIONS
    assert raw_data.window_screenshot_path == _SENTINEL_RAW_PATH / MesoscopeRawDataFiles.WINDOW_SCREENSHOT
    assert raw_data.mesoscope_data_path == _SENTINEL_RAW_PATH / MesoscopeDirectories.MESOSCOPE_DATA


def test_mesoscope_raw_data_files_enum_is_string_enum() -> None:
    """Verifies that MesoscopeRawDataFiles members are strings (StrEnum) carrying the canonical filenames."""
    assert isinstance(MesoscopeRawDataFiles.ZABER_POSITIONS, str)
    assert MesoscopeRawDataFiles.ZABER_POSITIONS == "zaber_positions.yaml"
    assert MesoscopeRawDataFiles.MESOSCOPE_POSITIONS == "mesoscope_positions.yaml"
    assert MesoscopeRawDataFiles.WINDOW_SCREENSHOT == "window_screenshot.png"


def test_mesoscope_directories_enum_is_string_enum() -> None:
    """Verifies that MesoscopeDirectories members are strings (StrEnum) carrying the canonical directory names."""
    assert isinstance(MesoscopeDirectories.MESOSCOPE_DATA, str)
    assert MesoscopeDirectories.MESOSCOPE_DATA == "mesoscope_data"
