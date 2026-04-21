from typing import Any

from .mcp_instance import (
    CONFIGURATION_DIR as CONFIGURATION_DIR,
    DESCRIPTOR_REGISTRY as DESCRIPTOR_REGISTRY,
    DATASET_MARKER_FILENAME as DATASET_MARKER_FILENAME,
    INCOMPLETE_SESSION_MARKER as INCOMPLETE_SESSION_MARKER,
    mcp as mcp,
    read_yaml as read_yaml,
    serialize as serialize,
    ok_response as ok_response,
    safe_iterdir as safe_iterdir,
    error_response as error_response,
    describe_dataclass as describe_dataclass,
    write_yaml_validated as write_yaml_validated,
    resolve_root_directory as resolve_root_directory,
    session_root_from_marker as session_root_from_marker,
)
from ..data_classes import (
    SessionData as SessionData,
    RawDataFiles as RawDataFiles,
    SessionTypes as SessionTypes,
)
from ..configuration import (
    Cue as Cue,
    Segment as Segment,
    BaseTrial as BaseTrial,
    TriggerType as TriggerType,
    GasPuffTrial as GasPuffTrial,
    TaskTemplate as TaskTemplate,
    VREnvironment as VREnvironment,
    TrialStructure as TrialStructure,
    ExperimentState as ExperimentState,
    WaterRewardTrial as WaterRewardTrial,
    AcquisitionSystems as AcquisitionSystems,
    MesoscopeExperimentConfiguration as MesoscopeExperimentConfiguration,
    get_working_directory as get_working_directory,
    get_google_credentials_path as get_google_credentials_path,
    get_task_templates_directory as get_task_templates_directory,
    create_experiment_configuration as create_experiment_configuration,
    populate_default_experiment_states as populate_default_experiment_states,
)

_TRIAL_CLASSES: dict[str, type[BaseTrial]]

def discover_experiments_tool(root_directory: str | None = None, project: str | None = None) -> dict[str, Any]: ...
def discover_templates_tool() -> dict[str, Any]: ...
def read_experiment_configuration_tool(project: str, experiment: str, root_directory: str) -> dict[str, Any]: ...
def read_template_tool(template_name: str) -> dict[str, Any]: ...
def read_working_directory_tool() -> dict[str, Any]: ...
def read_google_credentials_tool() -> dict[str, Any]: ...
def read_task_templates_directory_tool() -> dict[str, Any]: ...
def write_template_tool(
    template_name: str, template_payload: dict[str, Any], *, overwrite: bool = False
) -> dict[str, Any]: ...
def write_experiment_configuration_tool(
    project: str,
    experiment: str,
    configuration_payload: dict[str, Any],
    root_directory: str,
    *,
    overwrite: bool = False,
) -> dict[str, Any]: ...
def create_project_tool(project: str, root_directory: str) -> dict[str, Any]: ...
def create_experiment_config_tool(
    project: str, experiment: str, template: str, root_directory: str, state_count: int = 1, *, overwrite: bool = False
) -> dict[str, Any]: ...
def set_working_directory_tool(directory: str) -> dict[str, Any]: ...
def set_google_credentials_tool(credentials_path: str) -> dict[str, Any]: ...
def set_task_templates_directory_tool(directory: str) -> dict[str, Any]: ...
def describe_template_schema_tool() -> dict[str, Any]: ...
def describe_experiment_configuration_schema_tool(acquisition_system: str = "mesoscope") -> dict[str, Any]: ...
def validate_template_tool(template_name: str) -> dict[str, Any]: ...
def validate_experiment_configuration_tool(project: str, experiment: str, root_directory: str) -> dict[str, Any]: ...
def get_project_overview_tool(project: str, root_directory: str) -> dict[str, Any]: ...
def get_platform_environment_status_tool() -> dict[str, Any]: ...
def list_supported_session_types_tool() -> dict[str, Any]: ...
def list_supported_acquisition_systems_tool() -> dict[str, Any]: ...
def list_supported_trial_types_tool() -> dict[str, Any]: ...
def list_supported_trigger_types_tool() -> dict[str, Any]: ...
