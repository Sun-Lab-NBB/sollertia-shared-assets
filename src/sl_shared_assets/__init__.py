"""Provides data acquisition and processing assets shared between Sun (NeuroAI) lab libraries.

See https://github.com/Sun-Lab-NBB/sl-shared-assets for more details.
API documentation: https://sl-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .data_classes import (
    RawData,
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    SessionTypes,
    InjectionData,
    ProcedureData,
    ProcessedData,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)
from .configuration import (
    Cue,
    Segment,
    BaseTrial,
    TriggerType,
    GasPuffTrial,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
    ExperimentState,
    MesoscopeCameras,
    WaterRewardTrial,
    AcquisitionSystems,
    MesoscopeFileSystem,
    ServerConfiguration,
    MesoscopeGoogleSheets,
    MesoscopeExternalAssets,
    MesoscopeMicroControllers,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    get_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
)

# Ensures console is enabled when this library is imported.
if not console.enabled:
    console.enable()

__all__ = [
    "AcquisitionSystems",
    "BaseTrial",
    "Cue",
    "DrugData",
    "ExperimentState",
    "GasPuffTrial",
    "ImplantData",
    "InjectionData",
    "LickTrainingDescriptor",
    "MesoscopeCameras",
    "MesoscopeExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "MesoscopeExternalAssets",
    "MesoscopeFileSystem",
    "MesoscopeGoogleSheets",
    "MesoscopeHardwareState",
    "MesoscopeMicroControllers",
    "MesoscopeSystemConfiguration",
    "ProcedureData",
    "ProcessedData",
    "RawData",
    "RunTrainingDescriptor",
    "Segment",
    "ServerConfiguration",
    "SessionData",
    "SessionTypes",
    "SubjectData",
    "SurgeryData",
    "TaskTemplate",
    "TrialStructure",
    "TriggerType",
    "VREnvironment",
    "WaterRewardTrial",
    "WindowCheckingDescriptor",
    "create_experiment_configuration",
    "get_google_credentials_path",
    "get_server_configuration",
    "get_system_configuration_data",
    "get_task_templates_directory",
    "get_working_directory",
]
