"""Provides the MCP server for agentic configuration of Sollertia platform data workflow components.

This module exposes tools that enable AI agents to manage shared configuration assets that work across all data
acquisition systems.
"""

import os
import uuid
from typing import Literal
from pathlib import Path
import contextlib

from mcp.server.fastmcp import FastMCP
from ataraxis_base_utilities import ensure_directory_exists

from ..configuration import (
    TaskTemplate,
    WaterRewardTrial,
    ServerConfiguration,
    MesoscopeExperimentConfiguration,
    get_working_directory,
    set_working_directory as _set_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    set_google_credentials_path as _set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory as _set_task_templates_directory,
    get_system_configuration_data,
    create_experiment_configuration,
    populate_default_experiment_states,
)

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sollertia-shared-assets", json_response=True)


@mcp.tool()
def get_working_directory_tool() -> str:
    """Returns the current Sollertia platform working directory path.

    Returns:
        The absolute path to the working directory, or an error message if not configured.
    """
    try:
        path = get_working_directory()
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return f"Working directory: {path}"


@mcp.tool()
def set_working_directory_tool(directory: str) -> str:
    """Sets the Sollertia platform working directory.

    Args:
        directory: The absolute path to set as the working directory.

    Returns:
        A confirmation message or error description.
    """
    try:
        path = Path(directory)
        _set_working_directory(path=path)
    except Exception as e:
        return f"Error: {e}"
    else:
        return f"Working directory set to: {path}"


@mcp.tool()
def get_google_credentials_tool() -> str:
    """Returns the path to the Google service account credentials file.

    Returns:
        The credentials file path, or an error message if not configured.
    """
    try:
        path = get_google_credentials_path()
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return f"Google credentials: {path}"


@mcp.tool()
def get_task_templates_directory_tool() -> str:
    """Returns the path to the sollertia-unity-tasks project's Configurations (Template) directory.

    Returns:
        The task templates directory path, or an error message if not configured.
    """
    try:
        path = get_task_templates_directory()
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        return f"Task templates directory: {path}"


@mcp.tool()
def list_available_templates_tool() -> str:
    """Lists all available task templates in the configured templates directory.

    Returns:
        A formatted list of available template names, or an error message if not configured.
    """
    try:
        templates_dir = get_task_templates_directory()
        templates = sorted([f.stem for f in templates_dir.glob("*.yaml")])
    except FileNotFoundError as e:
        return f"Error: {e}"
    else:
        if not templates:
            return f"No templates found in {templates_dir}"
        return "Available templates:\n- " + "\n- ".join(templates)


@mcp.tool()
def get_template_info_tool(template_name: str) -> str:
    """Returns detailed information about a specific task template.

    Args:
        template_name: The name of the template (without .yaml extension).

    Returns:
        A summary of the template contents including cues, segments, and trial structures.
    """
    try:
        templates_dir = get_task_templates_directory()
        template_path = templates_dir.joinpath(f"{template_name}.yaml")
        if not template_path.exists():
            available = sorted([f.stem for f in templates_dir.glob("*.yaml")])
            return f"Error: Template '{template_name}' not found. Available: {', '.join(available)}"

        template = TaskTemplate.from_yaml(file_path=template_path)

        cue_summary = ", ".join([f"{c.name}(code={c.code})" for c in template.cues])
        segment_summary = ", ".join([s.name for s in template.segments])
        trial_summary = []
        for name, trial in template.trial_structures.items():
            trial_summary.append(f"{name} ({trial.trigger_type}): segment={trial.segment_name}")
    except FileNotFoundError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error loading template: {e}"
    else:
        return (
            f"Template: {template_name}\n"
            f"Cue offset: {template.cue_offset_cm}cm\n"
            f"Cues: {cue_summary}\n"
            f"Segments: {segment_summary}\n"
            f"Trial structures:\n  - " + "\n  - ".join(trial_summary)
        )


@mcp.tool()
def set_google_credentials_tool(credentials_path: str) -> str:
    """Sets the path to the Google service account credentials file.

    Args:
        credentials_path: The absolute path to the credentials JSON file.

    Returns:
        A confirmation message or error description.
    """
    try:
        path = Path(credentials_path)
        _set_google_credentials_path(path=path)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Google credentials path set to: {path}"


@mcp.tool()
def set_task_templates_directory_tool(directory: str) -> str:
    """Sets the path to the sollertia-unity-tasks project's Configurations (Template) directory.

    Args:
        directory: The absolute path to the task templates directory.

    Returns:
        A confirmation message or error description.
    """
    try:
        path = Path(directory)
        _set_task_templates_directory(path=path)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Task templates directory set to: {path}"


@mcp.tool()
def get_server_configuration_tool() -> str:
    """Returns the current compute server configuration (password masked for security).

    Returns:
        The server configuration summary, or an error message if not configured.
    """
    try:
        config = get_server_configuration()
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return f"Server: {config.host} | User: {config.username} | Storage: {config.storage_root}"


@mcp.tool()
def create_server_configuration_template_tool(
    username: str,
    host: str,
    storage_root: str,
    working_root: str,
    shared_directory: str,
) -> str:
    """Creates a server configuration template with a placeholder password.

    The user must manually edit the generated file to add their password, then call get_server_configuration_tool
    to validate the configuration.

    Args:
        username: The username for server authentication.
        host: The server hostname or IP address.
        storage_root: The path to the server directory dedicated to general data storage.
        working_root: The path to the server directory dedicated to data processing operations.
        shared_directory: The name of the shared directory for Sollertia platform data.

    Returns:
        The path to the created template file and instructions for the user.
    """
    try:
        output_directory = get_working_directory().joinpath("configuration")
        config_path = output_directory.joinpath("server_configuration.yaml")

        ServerConfiguration(
            username=username,
            password="ENTER_YOUR_PASSWORD_HERE",  # noqa: S106
            host=host,
            storage_root=Path(storage_root),
            working_root=Path(working_root),
            shared_directory_name=shared_directory,
        ).to_yaml(file_path=config_path)
    except (FileNotFoundError, ValueError) as e:
        return f"Error: {e}"
    else:
        return (
            f"Server configuration template created at: {config_path}\n"
            f"ACTION REQUIRED: Edit the file to replace 'ENTER_YOUR_PASSWORD_HERE' with your actual password.\n"
            f"After editing, use get_server_configuration_tool to validate the configuration."
        )


@mcp.tool()
def get_projects_tool() -> str:
    """Lists all projects accessible to the data acquisition system.

    Discovers projects by scanning the immediate children of the data acquisition system's root directory, excluding
    hidden directories.

    Returns:
        A comma-separated list of project names, or a message indicating that no projects are configured.
    """
    try:
        system_configuration = get_system_configuration_data()
        projects = sorted(
            directory.name
            for directory in system_configuration.filesystem.root_directory.iterdir()
            if directory.is_dir() and not directory.name.startswith(".")
        )
    except (FileNotFoundError, OSError, ValueError) as exception:
        return f"Error: {exception}"
    else:
        if projects:
            return f"Projects: {', '.join(projects)}"
        return f"No projects configured for {system_configuration.name} data acquisition system."


@mcp.tool()
def create_project_tool(project: str) -> str:
    """Creates a new project directory structure for the data acquisition system.

    Creates the project directory and its 'configuration' subdirectory under the system's root directory. If the
    project already exists, returns an informational message without modifying anything.

    Args:
        project: The name of the project to create.

    Returns:
        A success message if the project was created, or an informational message if it already exists.
    """
    try:
        system_configuration = get_system_configuration_data()
        project_path = system_configuration.filesystem.root_directory.joinpath(project)
        configuration_path = project_path.joinpath("configuration")

        if project_path.exists():
            return f"Project '{project}' already exists at {project_path}"

        ensure_directory_exists(configuration_path)
    except (FileNotFoundError, OSError, ValueError) as exception:
        return f"Error: {exception}"
    else:
        return f"Project created: {project} at {project_path}"


@mcp.tool()
def get_experiments_tool(project: str) -> str:
    """Lists experiment configurations available for a specific project.

    Args:
        project: The name of the project for which to discover experiment configurations.

    Returns:
        A comma-separated list of experiment names, or a message indicating that no experiments are configured.
    """
    try:
        system_configuration = get_system_configuration_data()
        configuration_directory = system_configuration.filesystem.root_directory.joinpath(project, "configuration")
        experiments = sorted(config_file.stem for config_file in configuration_directory.glob("*.yaml"))
    except (FileNotFoundError, OSError, ValueError) as exception:
        return f"Error: {exception}"
    else:
        if experiments:
            return f"Experiments for {project}: {', '.join(experiments)}"
        return f"No experiments configured for {project} project."


@mcp.tool()
def get_experiment_info_tool(project: str, experiment: str) -> str:
    """Returns detailed information about an experiment configuration.

    Reads the experiment configuration YAML file and returns a summary of its structure including cues, segments,
    trial structures, and experiment states.

    Args:
        project: The name of the project containing the experiment.
        experiment: The name of the experiment configuration (without .yaml extension).

    Returns:
        A formatted summary of the experiment configuration, or an error message if the file cannot be read.
    """
    try:
        system_configuration = get_system_configuration_data()
        configuration_path = system_configuration.filesystem.root_directory.joinpath(
            project, "configuration", f"{experiment}.yaml"
        )

        if not configuration_path.exists():
            return f"Error: Experiment '{experiment}' not found in project '{project}'."

        experiment_configuration = MesoscopeExperimentConfiguration.from_yaml(file_path=configuration_path)

        cue_info = ", ".join(f"{cue.name}(code={cue.code})" for cue in experiment_configuration.cues)
        segment_info = ", ".join(segment.name for segment in experiment_configuration.segments)

        trial_info_parts = []
        for trial_name, trial in experiment_configuration.trial_structures.items():
            trial_type = "lick" if isinstance(trial, WaterRewardTrial) else "occupancy"
            trial_info_parts.append(f"{trial_name}({trial_type})")
        trial_info = ", ".join(trial_info_parts)

        state_info_parts = [
            f"{state_name}(code={state.experiment_state_code}, duration={state.state_duration_s}s)"
            for state_name, state in experiment_configuration.experiment_states.items()
        ]
        state_info = ", ".join(state_info_parts)
    except FileNotFoundError as exception:
        return f"Error: {exception}"
    except Exception as exception:
        return f"Error loading experiment: {exception}"
    else:
        return (
            f"Experiment: {experiment} | Unity scene: {experiment_configuration.unity_scene_name} | "
            f"Cues: [{cue_info}] | Segments: [{segment_info}] | "
            f"Trials: [{trial_info}] | States: [{state_info}]"
        )


@mcp.tool()
def create_experiment_config_tool(
    project: str,
    experiment: str,
    template: str,
    state_count: int = 1,
) -> str:
    """Creates an experiment configuration from a task template.

    Generates a new experiment configuration file using the specified task template. The configuration includes the
    VR structure from the template (cues, segments, and trials) and the requested number of default-valued runtime
    states. Trial-specific parameters use sensible defaults and should be customized via YAML editing.

    Args:
        project: The name of the project for which to create the experiment.
        experiment: The name for the new experiment configuration (used as the filename without .yaml extension).
        template: The name of the task template to use (filename without .yaml extension).
        state_count: The number of experiment states to generate. Defaults to 1.

    Returns:
        A success message with the file path, or an error description if creation fails.
    """
    try:
        system_configuration = get_system_configuration_data()
        project_path = system_configuration.filesystem.root_directory.joinpath(project)
        file_path = project_path.joinpath("configuration", f"{experiment}.yaml")

        if not project_path.exists():
            return f"Error: Project '{project}' does not exist. Use create_project_tool to create it first."

        if file_path.exists():
            return f"Error: Experiment '{experiment}' already exists in project '{project}'."

        templates_directory = get_task_templates_directory()
        template_path = templates_directory.joinpath(f"{template}.yaml")
        if not template_path.exists():
            available_templates = sorted(template_file.stem for template_file in templates_directory.glob("*.yaml"))
            return (
                f"Error: Template '{template}' not found. "
                f"Available templates: {', '.join(available_templates) if available_templates else 'none'}"
            )

        task_template = TaskTemplate.from_yaml(file_path=template_path)

        experiment_configuration = create_experiment_configuration(
            template=task_template,
            system=system_configuration.name,
            unity_scene_name=template,
        )

        populate_default_experiment_states(
            experiment_configuration=experiment_configuration,
            state_count=state_count,
        )

        experiment_configuration.to_yaml(file_path=file_path)
    except FileNotFoundError as exception:
        return f"Error: {exception}"
    except Exception as exception:
        return f"Error creating experiment: {exception}"
    else:
        return f"Experiment created: {experiment} from template '{template}' at {file_path}"


@mcp.tool()
def check_mount_accessibility_tool(path: str) -> str:
    """Verifies that a filesystem path is accessible and writable.

    Checks whether the specified path exists, is a mount point, and supports write operations. Use this to verify
    that SMB or NFS mounts are properly configured before running acquisition sessions.

    Args:
        path: The filesystem path to verify (for example, "/mnt/server/data").

    Returns:
        A status message indicating existence, mount status, write capability, and any errors encountered.
    """
    target = Path(path)

    if not target.exists():
        return f"Path: {path} | Exists: No | Mount: N/A | Writable: N/A | Status: FAIL"

    is_mount = os.path.ismount(path)

    # Tests write capability by creating and removing a temporary file in the target directory.
    writable = False
    write_error: str | None = None
    try:
        test_file = target.joinpath(f".mount_test_{uuid.uuid4().hex[:8]}")
        test_file.write_text("test")
        test_file.unlink()
        writable = True
    except PermissionError:
        write_error = "Permission denied"
    except OSError as os_error:
        write_error = str(os_error)

    mount_status = "Yes" if is_mount else "No"
    write_status = "Yes" if writable else "No"
    result_status = "OK" if writable else "FAIL"
    check_result = (
        f"Path: {path} | Exists: Yes | Mount: {mount_status} | Writable: {write_status} | Status: {result_status}"
    )

    if write_error:
        check_result += f" | Error: {write_error}"

    return check_result


@mcp.tool()
def check_system_mounts_tool() -> str:
    """Verifies all filesystem paths in the system configuration are accessible and writable.

    Reads the active system configuration and checks each filesystem path (root_directory, server_directory, and
    nas_directory, plus any system-specific directories such as the mesoscope_directory) for existence, mount status,
    and write capability.

    Returns:
        A formatted report showing the status of each configured filesystem path with a summary line.
    """

    def check_path(name: str, directory: Path) -> str:
        """Checks a single path and returns a formatted status line."""
        path_str = str(directory)
        if not directory or path_str in ("", "."):
            return f"{name}: (not configured)"

        if not directory.exists():
            return f"{name}: {path_str} | Exists: No | FAIL"

        is_mount = os.path.ismount(path_str)
        mount_status = "Yes" if is_mount else "No"

        writable = False
        with contextlib.suppress(OSError):
            test_file = directory.joinpath(f".mount_test_{uuid.uuid4().hex[:8]}")
            test_file.write_text("test")
            test_file.unlink()
            writable = True

        write_status = "Yes" if writable else "No"
        result_status = "OK" if writable else "FAIL"
        return f"{name}: {path_str} | Mount: {mount_status} | Writable: {write_status} | {result_status}"

    try:
        system_configuration = get_system_configuration_data()
        filesystem = system_configuration.filesystem

        results = [
            f"System: {system_configuration.name}",
            check_path(name="root_directory", directory=filesystem.root_directory),
            check_path(name="server_directory", directory=filesystem.server_directory),
            check_path(name="nas_directory", directory=filesystem.nas_directory),
        ]

        # System-specific directories that are not common to all acquisition systems.
        if hasattr(filesystem, "mesoscope_directory"):
            results.append(check_path(name="mesoscope_directory", directory=filesystem.mesoscope_directory))

        fail_count = sum(1 for result in results[1:] if "FAIL" in result)
        ok_count = sum(1 for result in results[1:] if "OK" in result)
        not_configured_count = sum(1 for result in results[1:] if "not configured" in result)

        results.append(f"Summary: {ok_count} OK, {fail_count} FAIL, {not_configured_count} not configured")
    except (FileNotFoundError, OSError, ValueError) as exception:
        return f"Error: {exception}"
    else:
        return "\n".join(results)


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
