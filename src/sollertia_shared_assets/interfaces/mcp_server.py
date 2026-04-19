"""Provides the MCP server for agentic management of Sollertia platform configuration and runtime data assets.

Exposes the canonical MCP tool surface that all sibling Sollertia libraries (sollertia-experiment,
sollertia-unity-tasks, sollertia-forgery, and downstream agents) use to discover, read, write, validate, and
introspect the configuration and runtime data files defined in this library.

Importing this module triggers tool registration in all tool submodules.
"""

from __future__ import annotations

from typing import Literal

# noinspection PyUnusedImports
from . import (
    data_tools,  # noqa: F401 - imported to trigger MCP tool registration.
    unity_tools,  # noqa: F401 - imported to trigger MCP tool registration.
    configuration_tools,  # noqa: F401 - imported to trigger MCP tool registration.
)
from .mcp_instance import mcp

__all__ = ["run_server"]


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
