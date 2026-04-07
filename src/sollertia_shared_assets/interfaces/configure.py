"""Provides the Command-Line Interface (CLI) for configuring major components of the Sollertia platform data
workflow.
"""

from __future__ import annotations

from pathlib import Path  # pragma: no cover

import click  # pragma: no cover
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists  # pragma: no cover

from .mcp_server import run_server  # pragma: no cover
from ..configuration import (  # pragma: no cover
    GasPuffTrial,
    TaskTemplate,
    ExperimentState,
    WaterRewardTrial,
    AcquisitionSystems,
    set_working_directory,
    set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
    create_server_configuration_file,
    create_system_configuration_file,
)

CONTEXT_SETTINGS = {"max_content_width": 120}  # pragma: no cover
"""Ensures that displayed CLICK help messages are formatted according to the lab standard."""


@click.group("configure", context_settings=CONTEXT_SETTINGS)
def configure() -> None:  # pragma: no cover
    """Configures major components of the Sollertia platform data workflow."""


@configure.command("directory")
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to cache Sollertia platform configuration and local runtime data.",
)
def configure_directory(directory: Path) -> None:  # pragma: no cover
    """Sets the input directory as the local Sollertia platform working directory."""
    # Creates the directory if it does not exist
    ensure_directory_exists(directory)

    # Sets the directory as the local working directory
    set_working_directory(path=directory)


@configure.command("mcp")
@click.option(
    "-t",
    "--transport",
    type=str,
    default="stdio",
    show_default=True,
    help="The MCP transport type to use ('stdio', 'sse', or 'streamable-http').",
)
def start_mcp_server(transport: str) -> None:  # pragma: no cover
    """Starts the MCP server for agentic configuration management."""
    run_server(transport=transport)  # type: ignore[arg-type]


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

    console.echo(
        message=f"Google Sheets credentials path set to: {credentials.resolve()}.",
        level=LogLevel.SUCCESS,
    )


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

    ensure_directory_exists(project_path)
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
    required=True,
    default=1,
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
            f"'sl-configure project' CLI command to create the project before creating new experiment configuration(s)."
        )
        console.error(message=message, error=ValueError)

    templates_dir = get_task_templates_directory()
    template_path = templates_dir.joinpath(f"{template}.yaml")
    if not template_path.exists():
        available = sorted([f.stem for f in templates_dir.glob("*.yaml")])
        message = (
            f"Template '{template}' not found in {templates_dir}. "
            f"Available templates: {', '.join(available) if available else 'none'}."
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

    water_reward_count = sum(
        1 for t in experiment_configuration.trial_structures.values() if isinstance(t, WaterRewardTrial)
    )
    gas_puff_count = sum(1 for t in experiment_configuration.trial_structures.values() if isinstance(t, GasPuffTrial))

    for state_num in range(state_count):
        state_name = f"state_{state_num + 1}"
        experiment_configuration.experiment_states[state_name] = ExperimentState(
            experiment_state_code=state_num + 1,
            system_state_code=0,
            state_duration_s=60,
            supports_trials=True,
            reinforcing_initial_guided_trials=3 if water_reward_count > 0 else 0,
            reinforcing_recovery_failed_threshold=9 if water_reward_count > 0 else 0,
            reinforcing_recovery_guided_trials=3 if water_reward_count > 0 else 0,
            aversive_initial_guided_trials=3 if gas_puff_count > 0 else 0,
            aversive_recovery_failed_threshold=9 if gas_puff_count > 0 else 0,
            aversive_recovery_guided_trials=3 if gas_puff_count > 0 else 0,
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
    required=True,
    help="The password to use for server authentication.",
)
@click.option(
    "-h",
    "--host",
    type=str,
    required=True,
    show_default=True,
    default="cbsuwsun.biohpc.cornell.edu",
    help="The host name or IP address of the server.",
)
@click.option(
    "-sr",
    "--storage-root",
    type=str,
    required=True,
    show_default=True,
    default="/local/storage",
    help="The absolute path to to the server's slow HDD RAID volume.",
)
@click.option(
    "-wr",
    "--working-root",
    type=str,
    required=True,
    show_default=True,
    default="/local/workdir",
    help="The absolute path to to the server's fast NVME RAID volume.",
)
@click.option(
    "-sd",
    "--shared-directory",
    type=str,
    required=True,
    show_default=True,
    default="sun_data",
    help="The name of the shared directory used to store all Sollertia platform projects on both server's volumes.",
)
def generate_server_configuration_file(
    username: str,
    password: str,
    host: str,
    storage_root: str,
    working_root: str,
    shared_directory: str,
) -> None:  # pragma: no cover
    """Creates the remote compute server configuration file."""
    create_server_configuration_file(
        username=username,
        password=password,
        host=host,
        storage_root=storage_root,
        working_root=working_root,
        shared_directory_name=shared_directory,
    )
