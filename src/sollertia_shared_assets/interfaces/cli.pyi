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
    create_experiment_configuration as create_experiment_configuration,
    populate_default_experiment_states as populate_default_experiment_states,
)

_CONTEXT_SETTINGS: dict[str, int]

def slsa_cli() -> None: ...
def run_mcp_server(transport: Literal["stdio", "sse", "streamable-http"]) -> None: ...
def configure_group() -> None: ...
def configure_directory(directory: Path) -> None: ...
def configure_google_credentials(credentials: Path) -> None: ...
def configure_task_templates_directory(directory: Path) -> None: ...
def configure_project(project: str, root_directory: Path) -> None: ...
def generate_experiment_configuration_file(
    project: str,
    experiment: str,
    template: str,
    root_directory: Path,
    state_count: int,
    reward_size: float,
    reward_tone_duration: int,
    puff_duration: int,
    occupancy_duration: int,
) -> None: ...
