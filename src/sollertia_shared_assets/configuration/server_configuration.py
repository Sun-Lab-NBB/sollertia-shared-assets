"""Provides the server configuration dataclass used to store access credentials for the Sollertia platform remote
compute server.
"""

from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig


@dataclass
class ServerConfiguration(YamlConfig):
    """Defines the access credentials for the Sollertia platform remote compute server."""

    username: str = ""
    """The username to use for server authentication."""
    password: str = ""
    """The password to use for server authentication."""
    host: str = ""
    """The hostname or IP address of the server to connect to."""
