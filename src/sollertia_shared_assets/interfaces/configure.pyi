from typing import Literal
from pathlib import Path

from .mcp_server import run_server as run_server
from ..configuration import (
    TaskTemplate as TaskTemplate,
    AcquisitionSystems as AcquisitionSystems,
    set_working_directory as set_working_directory,
    set_google_credentials_path as set_google_credentials_path,
    get_task_templates_directory as get_task_templates_directory,
    set_task_templates_directory as set_task_templates_directory,
    get_system_configuration_data as get_system_configuration_data,
    create_experiment_configuration as create_experiment_configuration,
    create_server_configuration_file as create_server_configuration_file,
    create_system_configuration_file as create_system_configuration_file,
    populate_default_experiment_states as populate_default_experiment_states,
)

CONTEXT_SETTINGS: dict[str, int]

def configure() -> None: ...
def configure_directory(directory: Path) -> None: ...
def start_mcp_server(transport: Literal["stdio", "sse", "streamable-http"]) -> None: ...
def generate_system_configuration_file(system: AcquisitionSystems) -> None: ...
def configure_google_credentials(credentials: Path) -> None: ...
def configure_task_templates_directory(directory: Path) -> None: ...
def configure_project(project: str) -> None: ...
def generate_experiment_configuration_file(
    project: str,
    experiment: str,
    template: str,
    state_count: int,
    reward_size: float,
    reward_tone_duration: int,
    puff_duration: int,
    occupancy_duration: int,
) -> None: ...
def generate_server_configuration_file(
    username: str, password: str, host: str, storage_root: Path, working_root: Path, shared_directory: str
) -> None: ...
