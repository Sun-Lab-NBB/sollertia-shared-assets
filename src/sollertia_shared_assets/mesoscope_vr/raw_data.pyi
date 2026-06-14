from enum import StrEnum
from pathlib import Path
from dataclasses import dataclass

class MesoscopeRawDataFiles(StrEnum):
    ZABER_POSITIONS = "zaber_positions.yaml"
    MESOSCOPE_POSITIONS = "mesoscope_positions.yaml"
    WINDOW_SCREENSHOT = "window_screenshot.png"

class MesoscopeDirectories(StrEnum):
    MESOSCOPE_DATA = "mesoscope_data"

@dataclass(slots=True)
class MesoscopeRawData:
    zaber_positions_path: Path
    mesoscope_positions_path: Path
    window_screenshot_path: Path
    mesoscope_data_path: Path
    @classmethod
    def build(cls, root: Path) -> MesoscopeRawData: ...
