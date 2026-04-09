"""Provides the MCP server for agentic management of Sollertia platform configuration and runtime data assets.

Exposes the canonical MCP tool surface that all sibling Sollertia libraries (sollertia-experiment,
sollertia-unity-tasks, sollertia-forgery, and downstream agents) use to discover, read, write, validate, and
introspect the configuration and runtime data files defined in this library.

Importing this module triggers tool registration in all tool sub-modules.
"""

from __future__ import annotations

from typing import Literal

from . import (
    data_tools,
    unity_tools,
    configuration_tools,
)
from .mcp_instance import mcp

# References to suppress F811/F401 on the trigger imports above.
__all__ = ["configuration_tools", "data_tools", "unity_tools"]


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
    mcp.run(transport=transport)
