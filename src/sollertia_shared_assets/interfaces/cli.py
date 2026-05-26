"""Provides the Command-Line Interface installed into the Python environment together with the library."""

from __future__ import annotations

from typing import Literal
from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from .mcp_server import run_server
from ..data_classes import CONFIGURATION_DIRECTORY, ProjectData, discover_projects
from ..configuration import (
    TaskTemplate,
    AcquisitionSystems,
    get_data_root,
    set_data_root,
    get_working_directory,
    set_working_directory,
    get_google_credentials_path,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    create_experiment_configuration,
    populate_default_experiment_states,
)

_CONTEXT_SETTINGS: dict[str, int] = {"max_content_width": 120}
"""Ensures that displayed Click help messages are formatted according to the lab standard."""


@click.group("slsa", context_settings=_CONTEXT_SETTINGS)
def slsa_cli() -> None:  # pragma: no cover
    """Provides the entry point for all interactive sollertia-shared-assets (SLSA) library components."""


@slsa_cli.command("mcp", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"], case_sensitive=False),
    default="stdio",
    show_default=True,
    help="The MCP transport type to use.",
)
def run_mcp_server(transport: Literal["stdio", "sse", "streamable-http"]) -> None:  # pragma: no cover
    """Starts the MCP server for agentic configuration management."""
    run_server(transport=transport)


@slsa_cli.group("get", context_settings=_CONTEXT_SETTINGS)
def get_group() -> None:  # pragma: no cover
    """Reports the configured paths and the composition of the local Sollertia platform data hierarchy."""


@get_group.command("directory", context_settings=_CONTEXT_SETTINGS)
def get_directory() -> None:  # pragma: no cover
    """Reports the configured local Sollertia platform working directory."""
    console.echo(message=f"Working directory: {get_working_directory()}.")


@get_group.command("data-root", context_settings=_CONTEXT_SETTINGS)
def get_data_root_path() -> None:  # pragma: no cover
    """Reports the configured local Sollertia platform data root."""
    console.echo(message=f"Data root: {get_data_root()}.")


@get_group.command("google", context_settings=_CONTEXT_SETTINGS)
def get_google_credentials() -> None:  # pragma: no cover
    """Reports the configured Google service account credentials file path."""
    console.echo(message=f"Google credentials path: {get_google_credentials_path()}.")


@get_group.command("templates", context_settings=_CONTEXT_SETTINGS)
def get_templates_directory() -> None:  # pragma: no cover
    """Reports the configured sollertia-unity-tasks task templates directory."""
    console.echo(message=f"Task templates directory: {get_task_templates_directory()}.")


@get_group.command("projects", context_settings=_CONTEXT_SETTINGS)
def get_projects() -> None:  # pragma: no cover
    """Lists the projects stored under the local Sollertia platform data root."""
    projects = [
        project.project_name for project in discover_projects(root_path=get_data_root(), strategy="directories")
    ]
    if projects:
        console.echo(message=f"Projects under the data root: {', '.join(projects)}.")
    else:
        console.echo(message="No projects are stored under the data root. Use 'slsa configure project' to create one.")


@get_group.command("experiments", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project for which to list the available experiment configurations.",
)
def get_experiments(project: str) -> None:  # pragma: no cover
    """Lists the experiment configurations available for the target project."""
    experiments = [
        configuration.stem
        for configuration in ProjectData(root=get_data_root(), project_name=project).experiment_configs()
    ]
    if experiments:
        console.echo(message=f"Experiment configurations for the '{project}' project: {', '.join(experiments)}.")
    else:
        console.echo(
            message=(
                f"No experiment configurations are available for the '{project}' project. Use "
                f"'slsa configure experiment' to create one."
            )
        )


@slsa_cli.group("configure", context_settings=_CONTEXT_SETTINGS)
def configure_group() -> None:  # pragma: no cover
    """Configures major components of the Sollertia platform data workflow."""


@configure_group.command("directory", context_settings=_CONTEXT_SETTINGS)
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


@configure_group.command("data-root", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory under which all project directories are stored on this machine.",
)
def configure_data_root(directory: Path) -> None:  # pragma: no cover
    """Sets the input directory as the local Sollertia platform data root."""
    set_data_root(path=directory)


@configure_group.command("google", context_settings=_CONTEXT_SETTINGS)
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


@configure_group.command("templates", context_settings=_CONTEXT_SETTINGS)
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


@configure_group.command("project", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project to be created.",
)
@click.option(
    "-r",
    "--root-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the root data directory under which to create the project.",
)
def configure_project(project: str, root_directory: Path) -> None:  # pragma: no cover
    """Creates the data structure for a new project under the provided root data directory."""
    project_path = root_directory.joinpath(project, CONFIGURATION_DIRECTORY)
    ensure_directory_exists(path=project_path)
    console.echo(message=f"Project {project} data structure: generated.", level=LogLevel.SUCCESS)


@configure_group.command("experiment", context_settings=_CONTEXT_SETTINGS)
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
    "-r",
    "--root-directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the root data directory that contains the project.",
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
    root_directory: Path,
    state_count: int,
    reward_size: float,
    reward_tone_duration: int,
    puff_duration: int,
    occupancy_duration: int,
) -> None:  # pragma: no cover
    """Creates an experiment configuration from a task template under the provided root data directory."""
    project_path = root_directory.joinpath(project)
    if not project_path.exists():
        message = (
            f"Unable to generate the {experiment} experiment's configuration file: the project '{project}' does not "
            f"exist under the provided root directory {root_directory}. Use 'slsa configure project' first."
        )
        console.error(message=message, error=ValueError)

    file_path = project_path.joinpath(CONFIGURATION_DIRECTORY, f"{experiment}.yaml")

    templates_directory = get_task_templates_directory()
    template_path = templates_directory.joinpath(f"{template}.yaml")
    if not template_path.exists():
        available_templates = sorted([template_file.stem for template_file in templates_directory.glob("*.yaml")])
        message = (
            f"Unable to generate the '{experiment}' experiment configuration. The template '{template}' was "
            f"not found in {templates_directory}. Available templates: "
            f"{', '.join(available_templates) if available_templates else 'none'}."
        )
        console.error(message=message, error=FileNotFoundError)

    task_template = TaskTemplate.from_yaml(file_path=template_path)

    experiment_configuration = create_experiment_configuration(
        template=task_template,
        system=AcquisitionSystems.MESOSCOPE_VR,
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
