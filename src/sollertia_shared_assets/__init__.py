"""Provides data acquisition and processing assets shared between Sollertia platform libraries.

This library is part of the Sollertia AI-assisted scientific data acquisition and processing platform, built on the
Ataraxis framework and developed in the Sun (NeuroAI) lab at Cornell University.

See the `API documentation <https://sollertia-shared-assets-api-docs.netlify.app/>`_ for the description of available
assets. See the `source code repository <https://github.com/Sun-Lab-NBB/sollertia-shared-assets>`_ for more details.
See the `Sollertia platform <https://github.com/Sun-Lab-NBB/sollertia>`_ for the top-level project entry-point.

Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .data_classes import (
    DrugData,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    SessionTypes,
    InjectionData,
    ProcedureData,
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
    SystemConfiguration,
    MesoscopeGoogleSheets,
    MesoscopeExternalAssets,
    MesoscopeMicroControllers,
    MesoscopeSystemConfiguration,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
    create_system_configuration_file,
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
    "MesoscopePositions",
    "MesoscopeSystemConfiguration",
    "ProcedureData",
    "RunTrainingDescriptor",
    "Segment",
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
    "create_system_configuration_file",
    "get_google_credentials_path",
    "get_system_configuration_data",
    "get_task_templates_directory",
    "get_working_directory",
    "set_google_credentials_path",
    "set_task_templates_directory",
    "set_working_directory",
]
