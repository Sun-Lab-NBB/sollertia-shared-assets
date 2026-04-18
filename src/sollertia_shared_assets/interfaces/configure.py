"""Provides the Command-Line Interface for configuring major components of the Sollertia platform data workflow."""

from __future__ import annotations

from typing import Literal
from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .mcp_server import run_server
from ..configuration import (
    TaskTemplate,
    AcquisitionSystems,
    set_working_directory,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
    create_server_configuration_file,
    create_system_configuration_file,
    populate_default_experiment_states,
)

CONTEXT_SETTINGS: dict[str, int] = {"max_content_width": 120}
"""Ensures that displayed Click help messages are formatted according to the lab standard."""


@click.group("configure", context_settings=CONTEXT_SETTINGS)
def configure() -> None:  # pragma: no cover
    """Configures major components of the Sollertia platform data workflow."""


@configure.command("directory", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to cache Sollertia platform configuration and local runtime data.",
)
def configure_directory(directory: Path) -> None:  # pragma: no cover
    """Sets the input directory as the local Sollertia platform working directory."""
    ensure_directory_exists(path=directory)
    set_working_directory(path=directory)


@configure.command("mcp", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"], case_sensitive=False),
    default="stdio",
    show_default=True,
    help="The MCP transport type to use.",
)
def start_mcp_server(transport: Literal["stdio", "sse", "streamable-http"]) -> None:  # pragma: no cover
    """Starts the MCP server for agentic configuration management."""
    run_server(transport=transport)


@configure.command("system", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-s",
    "--system",
    type=click.Choice(AcquisitionSystems, case_sensitive=False),
    show_default=True,
    required=True,
    default=AcquisitionSystems.MESOSCOPE_VR,
    help="The type (name) of the data acquisition system for which to create the configuration file.",
)
def generate_system_configuration_file(system: AcquisitionSystems) -> None:  # pragma: no cover
    """Creates the specified data acquisition system's configuration file."""
    create_system_configuration_file(system=system)


@configure.command("google", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-c",
    "--credentials",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="The absolute path to the Google service account credentials .JSON file.",
)
def configure_google_credentials(credentials: Path) -> None:  # pragma: no cover
    """Sets the path to the Google service account credentials file."""
    set_google_credentials_path(path=credentials)


@configure.command("templates", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the sollertia-unity-tasks project's Configurations (Template) directory.",
)
def configure_task_templates_directory(directory: Path) -> None:  # pragma: no cover
    """Sets the path to the sollertia-unity-tasks task templates directory."""
    set_task_templates_directory(path=directory)


@configure.command("project", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project to be created.",
)
def configure_project(project: str) -> None:  # pragma: no cover
    """Configures the local data acquisition system to acquire data for the specified project."""
    system_configuration = get_system_configuration_data()
    project_path = system_configuration.filesystem.root_directory.joinpath(project, "configuration")

    ensure_directory_exists(path=project_path)
    console.echo(message=f"Project {project} data structure: generated.", level=LogLevel.SUCCESS)


@configure.command("experiment", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project for which to generate the new experiment configuration file.",
)
@click.option(
    "-e",
    "--experiment",
    type=str,
    required=True,
    help="The name of the experiment for which to create the configuration file.",
)
@click.option(
    "-t",
    "--template",
    type=str,
    required=True,
    help="The name of the task template to use (filename without .yaml extension).",
)
@click.option(
    "-sc",
    "--state-count",
    type=int,
    default=1,
    show_default=True,
    help="The number of runtime states supported by the experiment.",
)
@click.option(
    "--reward-size",
    type=float,
    default=5.0,
    show_default=True,
    help="Default water reward volume in microliters for lick-type trials.",
)
@click.option(
    "--reward-tone-duration",
    type=int,
    default=300,
    show_default=True,
    help="Default reward tone duration in milliseconds for lick-type trials.",
)
@click.option(
    "--puff-duration",
    type=int,
    default=100,
    show_default=True,
    help="Default gas puff duration in milliseconds for occupancy-type trials.",
)
@click.option(
    "--occupancy-duration",
    type=int,
    default=1000,
    show_default=True,
    help="Default occupancy threshold duration in milliseconds for occupancy-type trials.",
)
def generate_experiment_configuration_file(
    project: str,
    experiment: str,
    template: str,
    state_count: int,
    reward_size: float,
    reward_tone_duration: int,
    puff_duration: int,
    occupancy_duration: int,
) -> None:  # pragma: no cover
    """Creates an experiment configuration from a task template."""
    acquisition_system = get_system_configuration_data()
    file_path = acquisition_system.filesystem.root_directory.joinpath(project, "configuration", f"{experiment}.yaml")

    if not acquisition_system.filesystem.root_directory.joinpath(project).exists():
        message = (
            f"Unable to generate the {experiment} experiment's configuration file as the {acquisition_system.name} "
            f"data acquisition system is currently not configured to acquire data for the {project} project. Use the "
            f"'sl-configure project' CLI command to create the project before creating a new experiment configuration."
        )
        console.error(message=message, error=ValueError)

    templates_directory = get_task_templates_directory()
    template_path = templates_directory.joinpath(f"{template}.yaml")
    if not template_path.exists():
        available_templates = sorted([template_file.stem for template_file in templates_directory.glob("*.yaml")])
        message = (
            f"Template '{template}' not found in {templates_directory}. "
            f"Available templates: {', '.join(available_templates) if available_templates else 'none'}."
        )
        console.error(message=message, error=FileNotFoundError)

    task_template = TaskTemplate.from_yaml(file_path=template_path)

    experiment_configuration = create_experiment_configuration(
        template=task_template,
        system=acquisition_system.name,
        unity_scene_name=template,
        default_reward_size_ul=reward_size,
        default_reward_tone_duration_ms=reward_tone_duration,
        default_puff_duration_ms=puff_duration,
        default_occupancy_duration_ms=occupancy_duration,
    )

    populate_default_experiment_states(
        experiment_configuration=experiment_configuration,
        state_count=state_count,
    )

    experiment_configuration.to_yaml(file_path=file_path)
    console.echo(
        message=f"{experiment} experiment's configuration file: created from template '{template}'.",
        level=LogLevel.SUCCESS,
    )


@configure.command("server", context_settings=CONTEXT_SETTINGS)
@click.option(
    "-u",
    "--username",
    type=str,
    required=True,
    help="The username to use for server authentication.",
)
@click.option(
    "-p",
    "--password",
    type=str,
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="The password to use for server authentication. Prompted interactively (with hidden input) if not provided.",
)
@click.option(
    "-h",
    "--host",
    type=str,
    required=True,
    help="The host name or IP address of the server.",
)
def generate_server_configuration_file(
    username: str,
    password: str,
    host: str,
) -> None:  # pragma: no cover
    """Creates the remote compute server configuration file."""
    create_server_configuration_file(
        username=username,
        password=password,
        host=host,
    )
