"""Provides configuration assets for data acquisition and processing runtimes in the Sollertia platform."""

from .vr_configuration import (
    Cue,
    Segment,
    TriggerType,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
)
from .configuration_utilities import (
    AcquisitionSystems,
    get_working_directory,
    set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    create_experiment_configuration,
    populate_default_experiment_states,
)
from .mesoscope_configuration import MesoscopeExperimentConfiguration
from .experiment_configuration import (
    BaseTrial,
    GasPuffTrial,
    ExperimentState,
    WaterRewardTrial,
)

__all__ = [
    "AcquisitionSystems",
    "BaseTrial",
    "Cue",
    "ExperimentState",
    "GasPuffTrial",
    "MesoscopeExperimentConfiguration",
    "Segment",
    "TaskTemplate",
    "TrialStructure",
    "TriggerType",
    "VREnvironment",
    "WaterRewardTrial",
    "create_experiment_configuration",
    "get_google_credentials_path",
    "get_task_templates_directory",
    "get_working_directory",
    "populate_default_experiment_states",
    "set_google_credentials_path",
    "set_task_templates_directory",
    "set_working_directory",
]
