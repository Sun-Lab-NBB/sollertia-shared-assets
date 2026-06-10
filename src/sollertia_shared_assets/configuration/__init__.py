"""Provides configuration assets for data acquisition and processing runtimes in the Sollertia platform."""

from .vr_configuration import (
    Cue,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
)
from .configuration_utilities import (
    CREDENTIALS_DIRECTORY,
    CONFIGURATION_DIRECTORY,
    CREDENTIALS_FILE_REGISTRY,
    EXPERIMENT_CONFIGURATION_REGISTRY,
    CredentialsTypes,
    AcquisitionSystems,
    get_data_root,
    set_data_root,
    get_credentials,
    set_credentials,
    get_working_directory,
    set_working_directory,
    resolve_credentials_file,
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
    "CONFIGURATION_DIRECTORY",
    "CREDENTIALS_DIRECTORY",
    "CREDENTIALS_FILE_REGISTRY",
    "EXPERIMENT_CONFIGURATION_REGISTRY",
    "AcquisitionSystems",
    "CredentialsTypes",
    "Cue",
    "ExperimentState",
    "GasPuffTrial",
    "MesoscopeExperimentConfiguration",
    "TaskTemplate",
    "TrialStructure",
    "TriggerType",
    "VREnvironment",
    "WaterRewardTrial",
    "get_credentials",
    "get_data_root",
    "get_task_templates_directory",
    "get_working_directory",
    "resolve_credentials_file",
    "set_credentials",
    "set_data_root",
    "set_task_templates_directory",
    "set_working_directory",
]
