"""Provides the Command-Line Interface installed into the Python environment together with the library."""

from __future__ import annotations

from typing import Literal
from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists

from ..enums import CredentialsTypes
from .mcp_server import run_server
from ..credentials import get_credentials, set_credentials
from ..configuration import (
    get_data_root,
    set_data_root,
    get_working_directory,
    set_working_directory,
    get_task_templates_directory,
    set_task_templates_directory,
)
from ..data_hierarchy import ProjectData, discover_projects

_CONTEXT_SETTINGS: dict[str, int] = {"max_content_width": 120}
"""Ensures that displayed Click help messages are formatted according to the lab standard."""


@click.group("slsa", context_settings=_CONTEXT_SETTINGS)
def slsa_cli() -> None:  # pragma: no cover
    """Provides the entry point for all interactive sollertia-shared-assets library components."""


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


@get_group.command("credentials", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-c",
    "--category",
    type=click.Choice([member.value for member in CredentialsTypes], case_sensitive=False),
    required=True,
    help="The category of the credentials file to report.",
)
def get_credentials_path(category: str) -> None:  # pragma: no cover
    """Reports the path to the requested credentials file stored in the platform credentials directory."""
    console.echo(message=f"The '{category}' credentials path: {get_credentials(credentials=category)}.")


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
                f"No experiment configurations are available for the '{project}' project. Use your acquisition "
                f"system's CLI to create one (for Mesoscope-VR, 'sle mesoscope configure experiment')."
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


@configure_group.command("credentials", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-c",
    "--category",
    type=click.Choice([member.value for member in CredentialsTypes], case_sensitive=False),
    required=True,
    help="The category of the credentials file to configure.",
)
@click.option(
    "-f",
    "--file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="The absolute path to the credentials file to copy into the platform credentials directory.",
)
def configure_credentials(category: str, file: Path) -> None:  # pragma: no cover
    """Copies the input credentials file into the platform credentials directory under its canonical name."""
    set_credentials(credentials=category, path=file)


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
def configure_project(project: str) -> None:  # pragma: no cover
    """Creates the data structure for a new project under the configured Sollertia platform data root."""
    ProjectData(root=get_data_root(), project_name=project).create()
    console.echo(message=f"Project {project} data structure: generated.", level=LogLevel.SUCCESS)
