"""Provides data acquisition and processing assets shared between Sollertia platform libraries.

Sollertia is an AI-assisted scientific data acquisition and processing platform built on the Ataraxis framework and
developed in the Sun (NeuroAI) lab at Cornell University.

See https://github.com/Sun-Lab-NBB/sollertia-shared-assets for more details.
API documentation: https://sollertia-shared-assets-api-docs.netlify.app/
Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .data_classes import (
    DrugData,
    DatasetData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    SessionTypes,
    InjectionData,
    ProcedureData,
    DatasetSession,
    ZaberPositions,
    MesoscopePositions,
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
    SystemConfiguration,
    MesoscopeGoogleSheets,
    MesoscopeExternalAssets,
    MesoscopeMicroControllers,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
    create_server_configuration_file,
    create_system_configuration_file,
)

# Ensures console is enabled when this library is imported.
if not console.enabled:
    console.enable()

__all__ = [
    "AcquisitionSystems",
    "BaseTrial",
    "Cue",
    "DatasetData",
    "DatasetSession",
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
    "MesoscopePositions",
    "MesoscopeSystemConfiguration",
    "ProcedureData",
    "RunTrainingDescriptor",
    "Segment",
    "ServerConfiguration",
    "SessionData",
    "SessionTypes",
    "SubjectData",
    "SurgeryData",
    "SystemConfiguration",
    "TaskTemplate",
    "TrialStructure",
    "TriggerType",
    "VREnvironment",
    "WaterRewardTrial",
    "WindowCheckingDescriptor",
    "ZaberPositions",
    "create_experiment_configuration",
    "create_server_configuration_file",
    "create_system_configuration_file",
    "get_google_credentials_path",
    "get_server_configuration",
    "get_system_configuration_data",
    "get_task_templates_directory",
    "get_working_directory",
    "set_google_credentials_path",
    "set_task_templates_directory",
    "set_working_directory",
]
