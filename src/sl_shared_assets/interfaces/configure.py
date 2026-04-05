"""Provides the Command-Line Interface (CLI) for configuring major components of the Sun lab data workflow."""

from __future__ import annotations

from pathlib import Path  # pragma: no cover

import click  # pragma: no cover
from ataraxis_base_utilities import LogLevel, console, ensure_directory_exists  # pragma: no cover

from .mcp_server import run_server  # pragma: no cover
from ..configuration import (
    set_working_directory,
)  # pragma: no cover

CONTEXT_SETTINGS = {"max_content_width": 120}  # pragma: no cover
"""Ensures that displayed CLICK help messages are formatted according to the lab standard."""


@click.group("configure", context_settings=CONTEXT_SETTINGS)
def configure() -> None:  # pragma: no cover
    """Configures major components of the Sun lab data workflow."""


@configure.command("directory")
@click.option(
    "-d",
    "--directory",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="The absolute path to the directory where to cache Sun lab configuration and local runtime data.",
)
def configure_directory(directory: Path) -> None:  # pragma: no cover
    """Sets the input directory as the local Sun lab's working directory."""
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
