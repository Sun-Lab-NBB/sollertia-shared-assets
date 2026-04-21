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
    Directories,
    ImplantData,
    SessionData,
    SubjectData,
    SurgeryData,
    RawDataFiles,
    SessionTypes,
    InjectionData,
    ProcedureData,
    ProcessingTrackers,
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
    WaterRewardTrial,
    AcquisitionSystems,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    create_experiment_configuration,
)

# Ensures console is enabled when this library is imported.
if not console.enabled:
    console.enable()

__all__ = [
    "AcquisitionSystems",
    "BaseTrial",
    "Cue",
    "Directories",
    "DrugData",
    "ExperimentState",
    "GasPuffTrial",
    "ImplantData",
    "InjectionData",
    "LickTrainingDescriptor",
    "MesoscopeExperimentConfiguration",
    "MesoscopeExperimentDescriptor",
    "MesoscopeHardwareState",
    "ProcedureData",
    "ProcessingTrackers",
    "RawDataFiles",
    "RunTrainingDescriptor",
    "Segment",
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
    "get_task_templates_directory",
    "get_working_directory",
    "set_google_credentials_path",
    "set_task_templates_directory",
    "set_working_directory",
]
