"""Provides the Command-Line Interface installed into the Python environment together with the library."""

from __future__ import annotations

from typing import Literal
from pathlib import Path

import click
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists
from ataraxis_data_structures import delete_directory

from ..enums import CredentialsTypes
from .mcp_server import run_server
from ..credentials import get_credentials, set_credentials
from ..configuration import (
    NAME_COMPONENT_PATTERN,
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

_TEMPLATE_SUFFIXES: tuple[str, str] = (".yaml", ".yml")
"""The filename suffixes that make a YAML file a task template. The Unity catalog preflight scans both suffixes and
the Editor's template picker offers both as its file filter, so both name a live catalog member."""


@click.group("slsa", context_settings=_CONTEXT_SETTINGS)
def slsa_cli() -> None:
    """Provides the entry point for all interactive sollertia-shared-assets library components."""


@slsa_cli.command("mcp", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-t",
    "--transport",
    type=click.Choice(["stdio", "streamable-http"], case_sensitive=False),
    default="stdio",
    show_default=True,
    help="The MCP transport type to use.",
)
def run_mcp_server(transport: Literal["stdio", "streamable-http"]) -> None:
    """Starts the MCP server for agentic management of configuration, session, dataset, and Unity assets."""
    # The stdio transport carries the JSON-RPC message stream over stdout, which is also where the console writes
    # every message up to the WARNING level. Silencing the console keeps library output out of that stream, as a
    # single logged line renders the message it interleaves with unparsable for the connected client.
    if transport == "stdio":
        console.disable()
    else:
        console.echo(
            message=f"Starting the sollertia-shared-assets MCP server with the {transport} transport.",
            level=LogLevel.INFO,
        )

    run_server(transport=transport)


@slsa_cli.group("get", context_settings=_CONTEXT_SETTINGS)
def get_group() -> None:
    """Reports the configured paths and the composition of the local Sollertia platform data hierarchy."""


@get_group.command("directory", context_settings=_CONTEXT_SETTINGS)
def get_directory() -> None:
    """Reports the configured local Sollertia platform working directory."""
    console.echo(message=f"Working directory: {get_working_directory()}.")


@get_group.command("data-root", context_settings=_CONTEXT_SETTINGS)
def get_data_root_path() -> None:
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
def get_credentials_path(category: str) -> None:
    """Reports the path to the requested credentials file stored in the platform credentials directory."""
    console.echo(message=f"The '{category}' credentials path: {get_credentials(credentials=category)}.")


@get_group.command("templates", context_settings=_CONTEXT_SETTINGS)
def get_templates_directory() -> None:
    """Reports the configured sollertia-virtual-reality task templates directory."""
    console.echo(message=f"Task templates directory: {get_task_templates_directory()}.")


@get_group.command("projects", context_settings=_CONTEXT_SETTINGS)
def get_projects() -> None:
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
def get_experiments(project: str) -> None:
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
def configure_group() -> None:
    """Configures major components of the Sollertia platform data workflow."""


@configure_group.command("directory", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory in which to cache Sollertia platform configuration and runtime data.",
)
def configure_directory(directory: Path) -> None:
    """Sets the input directory as the local Sollertia platform working directory."""
    ensure_directory_exists(path=directory, is_file=False)
    set_working_directory(path=directory)


@configure_group.command("data-root", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory under which all project directories are stored on this machine.",
)
def configure_data_root(directory: Path) -> None:
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
def configure_credentials(category: str, file: Path) -> None:
    """Copies the input credentials file into the platform credentials directory under its canonical name."""
    set_credentials(credentials=category, path=file)


@configure_group.command("templates", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the sollertia-virtual-reality project's Assets/InfiniteCorridorTask/Configurations "
    "directory.",
)
def configure_task_templates_directory(directory: Path) -> None:
    """Sets the path to the sollertia-virtual-reality task templates directory."""
    set_task_templates_directory(path=directory)


@configure_group.command("project", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project to be created.",
)
def configure_project(project: str) -> None:
    """Creates the data structure for a new project under the configured Sollertia platform data root."""
    ProjectData(root=get_data_root(), project_name=project).create()
    console.echo(message=f"Project {project} data structure: generated.", level=LogLevel.SUCCESS)


@slsa_cli.group("delete", context_settings=_CONTEXT_SETTINGS)
def delete_group() -> None:
    """Removes Sollertia platform configuration assets from the local data hierarchy."""


@delete_group.command("template", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-f",
    "--file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    required=True,
    help="The absolute path to the sollertia-virtual-reality task template file to remove. The file must be stored "
    "under the configured task templates directory.",
)
def delete_template(file: Path) -> None:
    """Removes the target sollertia-virtual-reality task template file from the local filesystem.

    The removal is confined to a task template file stored under the configured task templates directory, which keeps
    the per-session frozen vr_configuration.yaml snapshot, an immutable acquisition record, out of reach.
    """
    templates_directory = get_task_templates_directory().resolve()

    # Both sides are resolved before the containment test, because Path.is_relative_to compares path components
    # without normalizing the '..' entries away while the kernel resolves the removal itself.
    template_path = file.resolve()
    if template_path == templates_directory or not template_path.is_relative_to(templates_directory):
        message = (
            f"Unable to remove the task template at {template_path}. The path must name a live template nested under "
            f"the configured task templates directory {templates_directory}, because a per-session "
            f"vr_configuration.yaml snapshot is an immutable acquisition record."
        )
        console.error(message=message, error=ValueError)

    if template_path.suffix not in _TEMPLATE_SUFFIXES:
        message = (
            f"Unable to remove the task template at {template_path}. The path must carry one of the task template "
            f"suffixes {', '.join(_TEMPLATE_SUFFIXES)}, but got '{template_path.suffix}'."
        )
        console.error(message=message, error=ValueError)

    if not template_path.is_file():
        message = f"Unable to remove the task template at {template_path}. No file is found at the resolved path."
        console.error(message=message, error=FileNotFoundError)

    template_path.unlink()
    console.echo(message=f"Task template {template_path.stem}: removed.", level=LogLevel.SUCCESS)


@delete_group.command("experiment", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project that stores the experiment configuration to remove.",
)
@click.option(
    "-e",
    "--experiment",
    type=str,
    required=True,
    help="The name of the experiment configuration to remove.",
)
def delete_experiment(project: str, experiment: str) -> None:
    """Removes the target experiment configuration from the project's configuration directory.

    Both names are joined onto the configured data root as path components, so each is required to be a single
    component, which confines the removal to the project's own configuration directory.
    """
    _verify_name_component(name=project, role="project name")
    _verify_name_component(name=experiment, role="experiment configuration name")

    configuration_path = ProjectData(root=get_data_root(), project_name=project).configuration_directory.joinpath(
        f"{experiment}.yaml"
    )
    if not configuration_path.is_file():
        message = (
            f"Unable to remove the '{experiment}' experiment configuration of the '{project}' project. The "
            f"configuration must be stored as a .yaml file under the project's configuration directory, but no file "
            f"is found at {configuration_path}."
        )
        console.error(message=message, error=FileNotFoundError)

    configuration_path.unlink()
    console.echo(
        message=f"Experiment configuration {experiment} of the {project} project: removed.", level=LogLevel.SUCCESS
    )


@delete_group.command("project", context_settings=_CONTEXT_SETTINGS)
@click.option(
    "-p",
    "--project",
    type=str,
    required=True,
    help="The name of the project to remove.",
)
def delete_project(project: str) -> None:
    """Removes the target project directory and all of its contents from the Sollertia platform data root.

    The removal is irreversible and takes every animal, session, and experiment configuration stored under the project
    with it, so the command blocks on an interactive confirmation prompt before it deletes anything. The project name
    is joined onto the configured data root as a path component, so it is required to be a single component, which
    keeps the removal on a project directory rather than an animal or session subtree nested inside one.
    """
    _verify_name_component(name=project, role="project name")

    project_data = ProjectData(root=get_data_root(), project_name=project)
    if not project_data.exists():
        message = (
            f"Unable to remove the '{project}' project. The project directory must exist under the configured "
            f"Sollertia platform data root, but no directory is found at {project_data.path}."
        )
        console.error(message=message, error=FileNotFoundError)

    click.confirm(
        text=(
            f"Deleting the '{project}' project irreversibly removes the {project_data.path} directory with every "
            f"animal, session, and experiment configuration stored under it. Continue?"
        ),
        default=False,
        abort=True,
    )

    delete_directory(directory_path=project_data.path)

    # Verifies the removal, since delete_directory reports an exhausted removal attempt as a warning and returns with
    # the directory still in place.
    if project_data.path.exists() or project_data.path.is_symlink():
        message = (
            f"Unable to remove the '{project}' project. The project directory must no longer exist once it is "
            f"deleted, but it is still present at {project_data.path}."
        )
        console.error(message=message, error=RuntimeError)

    console.echo(message=f"Project {project} data structure: removed.", level=LogLevel.SUCCESS)


def _verify_name_component(name: str, role: str) -> None:
    """Verifies that the input name is usable as a single directory or file name component.

    A name carrying a path separator or a parent-directory entry resolves to a location other than the one the
    command reports, so it is refused before any path is built from it.

    Args:
        name: The name supplied on the command line.
        role: The role the name plays in the command, used to build the error message.

    Raises:
        ValueError: If the name carries any character outside the ASCII letters, digits, and underscores.
    """
    if not NAME_COMPONENT_PATTERN.match(name):
        message = (
            f"Unable to resolve the {role} '{name}'. The name must be a single path component containing only ASCII "
            f"letters, digits, and underscores, because it is joined onto the data root as a directory or file name."
        )
        console.error(message=message, error=ValueError)
