"""Provides the data acquisition and processing assets specific to the Mesoscope-VR acquisition system."""

from .raw_data import (
    MesoscopeRawData,
    MesoscopeDirectories,
    MesoscopeRawDataFiles,
)
from .runtime_data import (
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)
from .experiment_configuration import (
    MesoscopeGasPuffTrial,
    MesoscopeWaterRewardTrial,
    MesoscopeExperimentConfiguration,
)

__all__ = [
    "LickTrainingDescriptor",
    "MesoscopeDirectories",
    "MesoscopeExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "MesoscopeGasPuffTrial",
    "MesoscopeHardwareState",
    "MesoscopeRawData",
    "MesoscopeRawDataFiles",
    "MesoscopeWaterRewardTrial",
    "RunTrainingDescriptor",
    "WindowCheckingDescriptor",
]
