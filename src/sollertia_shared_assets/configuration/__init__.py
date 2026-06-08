"""Provides configuration assets for data acquisition and processing runtimes in the Sollertia platform."""

from .vr_configuration import (
    Cue,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
)
from .configuration_utilities import (
    EXPERIMENT_CONFIGURATION_REGISTRY,
    AcquisitionSystems,
    get_data_root,
    set_data_root,
    get_working_directory,
    set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
)
from .mesoscope_configuration import MesoscopeExperimentConfiguration
from .experiment_configuration import (
    GasPuffTrial,
    ExperimentState,
    WaterRewardTrial,
)

__all__ = [
    "EXPERIMENT_CONFIGURATION_REGISTRY",
    "AcquisitionSystems",
    "Cue",
    "ExperimentState",
    "GasPuffTrial",
    "MesoscopeExperimentConfiguration",
    "TaskTemplate",
    "TrialStructure",
    "TriggerType",
    "VREnvironment",
    "WaterRewardTrial",
    "get_data_root",
    "get_google_credentials_path",
    "get_task_templates_directory",
    "get_working_directory",
    "set_data_root",
    "set_google_credentials_path",
    "set_task_templates_directory",
    "set_working_directory",
]
