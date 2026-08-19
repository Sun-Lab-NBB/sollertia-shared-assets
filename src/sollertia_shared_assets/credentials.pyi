from pathlib import Path

from .enums import CredentialsTypes as CredentialsTypes
from .registries import CREDENTIALS_FILE_REGISTRY as CREDENTIALS_FILE_REGISTRY
from .configuration import (
    CREDENTIALS_DIRECTORY as CREDENTIALS_DIRECTORY,
    get_working_directory as get_working_directory,
)

def resolve_credentials_file(credentials: str | CredentialsTypes) -> str: ...
def set_credentials(credentials: str | CredentialsTypes, path: Path) -> None: ...
def get_credentials(credentials: str | CredentialsTypes) -> Path: ...
