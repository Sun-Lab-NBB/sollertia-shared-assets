"""Provides the MCP server for agentic management of Sollertia platform configuration and runtime data assets.

Exposes the canonical MCP tool surface that all sibling Sollertia libraries (sollertia-experiment,
sollertia-virtual-reality, sollertia-forgery, and downstream agents) use to discover, read, write, validate, and
introspect the configuration and runtime data files defined in this library.

Importing this module auto-discovers every ``*_tools`` submodule and imports it, triggering its tool registration.
"""

from __future__ import annotations

from typing import Literal
from pathlib import Path
import importlib

from .mcp_instance import mcp

__all__ = ["run_server"]


def run_server(transport: Literal["stdio", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio' or 'streamable-http').
    """
    # Delegates to the MCPServer run loop, which blocks until the transport connection is closed. For 'stdio' this
    # means the server runs until the parent process closes stdin. For 'streamable-http' it runs an HTTP server that
    # accepts connections until explicitly terminated.
    if transport == "streamable-http":
        # Frames each response as a single JSON body instead of an event stream. Only the streamable-http transport
        # accepts this flag, so it stays out of the call below.
        mcp.run(transport=transport, json_response=True)
        return

    mcp.run(transport=transport)


def _register_tool_modules() -> None:
    """Imports every ``*_tools`` module in this package so its ``@mcp.tool()`` decorators register on import.

    Tool modules register their MCP tools purely as an import side effect. Discovering them by the ``_tools``
    filename suffix means each tool module (``configuration_tools``, ``data_tools``, ``unity_tools``) registers
    automatically, so adding a new tool module requires no edit to this module.
    """
    package_name = __name__.rpartition(".")[0]
    for module_path in sorted(Path(__file__).parent.glob("*_tools.py")):
        importlib.import_module(f"{package_name}.{module_path.stem}")


_register_tool_modules()
