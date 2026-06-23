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


def run_server(transport: Literal["stdio", "sse", "streamable-http"] = "stdio") -> None:
    """Starts the MCP server with the specified transport.

    Args:
        transport: The transport type to use ('stdio', 'sse', or 'streamable-http').
    """
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
