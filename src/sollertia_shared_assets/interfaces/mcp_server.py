"""Provides the MCP server for agentic configuration of Sollertia platform data workflow components.

This module exposes tools that enable AI agents to manage shared configuration assets that work across all data
acquisition systems.
"""

from typing import Literal
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..configuration import (
    TaskTemplate,
    ServerConfiguration,
    get_working_directory,
    set_working_directory as _set_working_directory,
    get_server_configuration,
    get_google_credentials_path,
    set_google_credentials_path as _set_google_credentials_path,
    get_task_templates_directory,
    set_task_templates_directory as _set_task_templates_directory,
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
    host: str = "cbsuwsun.biohpc.cornell.edu",
    storage_root: str = "/local/storage",
    working_root: str = "/local/workdir",
    shared_directory: str = "sun_data",
) -> str:
    """Creates a server configuration template with a placeholder password.

    The user must manually edit the generated file to add their password, then call get_server_configuration_tool
    to validate the configuration.

    Args:
        username: The username for server authentication.
        host: The server hostname or IP address.
        storage_root: The path to the server's slow HDD RAID volume.
        working_root: The path to the server's fast NVME RAID volume.
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
            storage_root=storage_root,
            working_root=working_root,
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


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
