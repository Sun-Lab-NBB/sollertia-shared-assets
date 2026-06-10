"""Provides data acquisition and processing assets shared between Sollertia platform libraries.

See the `API documentation <https://sollertia-shared-assets-api-docs.netlify.app/>`_ for the description of available
assets. See the `source code repository <https://github.com/Sun-Lab-NBB/sollertia-shared-assets>`_ for more details.

Authors: Ivan Kondratyev (Inkaros), Kushaan Gupta, Natalie Yeung
"""

from ataraxis_base_utilities import console

from .enums import (
    ReadAssets,
    SessionTypes,
    CredentialsTypes,
    AcquisitionSystems,
)
from .registries import (
    READ_ASSET_REGISTRY,
    CREDENTIALS_FILE_REGISTRY,
    resolve_read_asset,
)
from .credentials import (
    get_credentials,
    set_credentials,
    resolve_credentials_file,
)
from .data_classes import (
    DrugData,
    ImplantData,
    SubjectData,
    SurgeryData,
    InjectionData,
    ProcedureData,
)
from .mesoscope_vr import (
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    MesoscopeHardwareState,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
    MesoscopeExperimentConfiguration,
)
from .configuration import (
    CREDENTIALS_DIRECTORY,
    CONFIGURATION_DIRECTORY,
    Cue,
    TriggerType,
    GasPuffTrial,
    TaskTemplate,
    VREnvironment,
    TrialStructure,
    ExperimentState,
    WaterRewardTrial,
    get_data_root,
    set_data_root,
    get_working_directory,
    set_working_directory,
    get_task_templates_directory,
    set_task_templates_directory,
)
from .data_hierarchy import (
    RAW_DATA_DIRECTORY,
    PROCESSED_DATA_DIRECTORY,
    PERSISTENT_DATA_DIRECTORY,
    RawData,
    AnimalData,
    Directories,
    ProjectData,
    SessionData,
    RawDataFiles,
    ProcessedData,
    ProcessingTrackers,
    filter_sessions,
    iterate_sessions,
    discover_projects,
    discover_sessions,
    validate_directory,
    iter_animal_sessions,
    iter_project_animals,
    get_projects_for_animal,
    parse_session_timestamp,
)

# Ensures console is enabled when this library is imported.
if not console.enabled:
    console.enable()

__all__ = [
    "CONFIGURATION_DIRECTORY",
    "CREDENTIALS_DIRECTORY",
    "CREDENTIALS_FILE_REGISTRY",
    "PERSISTENT_DATA_DIRECTORY",
    "PROCESSED_DATA_DIRECTORY",
    "RAW_DATA_DIRECTORY",
    "READ_ASSET_REGISTRY",
    "AcquisitionSystems",
    "AnimalData",
    "CredentialsTypes",
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
    "ProcessedData",
    "ProcessingTrackers",
    "ProjectData",
    "RawData",
    "RawDataFiles",
    "ReadAssets",
    "RunTrainingDescriptor",
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
    "discover_projects",
    "discover_sessions",
    "filter_sessions",
    "get_credentials",
    "get_data_root",
    "get_projects_for_animal",
    "get_task_templates_directory",
    "get_working_directory",
    "iter_animal_sessions",
    "iter_project_animals",
    "iterate_sessions",
    "parse_session_timestamp",
    "resolve_credentials_file",
    "resolve_read_asset",
    "set_credentials",
    "set_data_root",
    "set_task_templates_directory",
    "set_working_directory",
    "validate_directory",
]
