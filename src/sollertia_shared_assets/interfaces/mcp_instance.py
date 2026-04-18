"""Provides the shared FastMCP server instance, constants, and helper functions for MCP tool modules.

All tool modules import the ``mcp`` instance from this module and register tools via the ``@mcp.tool()``
decorator. The helper functions in this module are shared across all tool modules.
"""

from __future__ import annotations

from enum import Enum
import uuid
from typing import TYPE_CHECKING, Any, get_type_hints
from pathlib import Path
import contextlib
from dataclasses import MISSING, fields, is_dataclass

import yaml  # type: ignore[import-untyped]
from mcp.server.fastmcp import FastMCP

from ..data_classes import (
    SessionTypes,
    RunTrainingDescriptor,
    LickTrainingDescriptor,
    WindowCheckingDescriptor,
    MesoscopeExperimentDescriptor,
)

if TYPE_CHECKING:
    from ataraxis_data_structures import YamlConfig

SESSION_MARKER_FILENAME: str = "session_data.yaml"
"""Marker filename used to identify session directories during recursive discovery walks."""

DATASET_MARKER_FILENAME: str = "dataset.yaml"
"""Marker filename used to identify dataset directories during recursive discovery walks."""

INCOMPLETE_SESSION_MARKER: str = "nk.bin"
"""Marker file present in raw_data while a session is incomplete; removed when runtime initializes."""

CONFIGURATION_DIR: str = "configuration"
"""Subdirectory under each project that holds experiment configuration YAML files."""

DESCRIPTOR_REGISTRY: dict[SessionTypes, tuple[str, type[YamlConfig]]] = {
    SessionTypes.LICK_TRAINING: ("lick_training_descriptor.yaml", LickTrainingDescriptor),
    SessionTypes.RUN_TRAINING: ("run_training_descriptor.yaml", RunTrainingDescriptor),
    SessionTypes.MESOSCOPE_EXPERIMENT: ("experiment_descriptor.yaml", MesoscopeExperimentDescriptor),
    SessionTypes.WINDOW_CHECKING: ("window_checking_descriptor.yaml", WindowCheckingDescriptor),
}
"""Maps each session type to its canonical descriptor filename and dataclass."""

# Initializes the MCP server with JSON response mode for structured output.
mcp = FastMCP(name="sollertia-shared-assets", json_response=True)


def ok_response(**payload: Any) -> dict[str, Any]:  # noqa: ANN401
    """Constructs a successful response dict with a ``success`` flag set to True."""
    return {"success": True, **payload}


def error_response(message: str) -> dict[str, Any]:
    """Constructs a failure response dict with a ``success`` flag set to False and the provided error message."""
    return {"success": False, "error": message}


def serialize(value: Any) -> Any:  # noqa: ANN401 - recursive helper accepts any serializable value.
    """Recursively converts a dataclass, Path, Enum, mapping, or sequence into JSON-friendly Python.

    Args:
        value: The value to convert.

    Returns:
        A plain Python representation suitable for JSON serialization.
    """
    if value is None:
        return None
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field_definition.name: serialize(value=getattr(value, field_definition.name))
            for field_definition in fields(value)
        }
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): serialize(value=item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize(value=item) for item in value]
    return value


def _describe_type(type_hint: Any) -> str:  # noqa: ANN401 - introspection helper accepts arbitrary type hints.
    """Returns a human-readable string for the given type hint."""
    if type_hint is None:
        return "None"
    if isinstance(type_hint, type):
        return type_hint.__name__
    return str(type_hint).replace("typing.", "")


def describe_dataclass(cls: type, *, recurse: bool = True) -> dict[str, Any]:
    """Returns a structured schema description of a dataclass type.

    The returned dict has shape ``{"class": <name>, "fields": {<field_name>: {"type", "default"|"required",
    "nested"?}}}`` where ``nested`` recursively describes nested dataclass types. The recursion guard prevents
    infinite recursion when a dataclass references itself either directly or transitively.

    Args:
        cls: The dataclass type to describe.
        recurse: Determines whether to recursively describe nested dataclass fields.

    Returns:
        A structured schema dict.
    """

    def _describe_inner(target: type, seen: frozenset[type]) -> dict[str, Any]:
        # Guards against infinite recursion from self-referential or cyclic dataclass hierarchies.
        if target in seen:
            return {"class": target.__name__, "recursive_reference": True}
        next_seen = seen | {target}

        if not is_dataclass(target):
            return {"type": _describe_type(type_hint=target)}

        try:
            hints = get_type_hints(target)
        except Exception:
            hints = {}

        schema: dict[str, Any] = {"class": target.__name__, "fields": {}}
        # Builds the per-field schema with type, default or required status, and optional nested recursion.
        # noinspection PyDataclass
        for field_definition in fields(target):
            type_hint = hints.get(field_definition.name, field_definition.type)
            field_schema: dict[str, Any] = {"type": _describe_type(type_hint=type_hint)}
            if field_definition.default is not MISSING:
                field_schema["default"] = serialize(value=field_definition.default)
            elif field_definition.default_factory is not MISSING:
                try:
                    field_schema["default"] = serialize(value=field_definition.default_factory())
                except Exception:
                    field_schema["required"] = True
            else:
                field_schema["required"] = True
            if recurse and isinstance(type_hint, type) and is_dataclass(type_hint):
                field_schema["nested"] = _describe_inner(target=type_hint, seen=next_seen)
            schema["fields"][field_definition.name] = field_schema

        return schema

    return _describe_inner(target=cls, seen=frozenset())


def write_yaml_validated(
    file_path: Path,
    payload: dict[str, Any],
    validator_cls: type[YamlConfig],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Writes a payload as YAML to ``file_path`` and validates it by loading through ``validator_cls``.

    Notes:
        Writes the payload to a temporary sibling file first, validates by instantiating ``validator_cls`` from
        that file (which triggers the dataclass ``__post_init__`` validation), and only on success re-serializes
        through the canonical ``to_yaml`` method to produce the final file. Re-runs ``__post_init__`` after
        loading so that any ``init=False`` derived fields whose values may have been overwritten by missing YAML
        keys are recomputed correctly.

    Args:
        file_path: The destination file path.
        payload: The dict payload to serialize as YAML.
        validator_cls: The YamlConfig dataclass used to validate the payload.
        overwrite: Determines whether to overwrite an existing destination file.

    Returns:
        A response dict with the file path and serialized data on success, or an error dict on failure.
    """
    if file_path.exists() and not overwrite:
        return error_response(message=f"File already exists: {file_path}. Pass overwrite=True to replace.")

    file_path.parent.mkdir(parents=True, exist_ok=True)
    # Writes the payload to a temporary sibling file and validates by round-tripping through the dataclass.
    # Keeps the temp file ending in .yaml because YamlConfig.from_yaml rejects non-.yaml paths.
    temp_path = file_path.with_name(f".{file_path.stem}.{uuid.uuid4().hex[:8]}.tmp.yaml")

    try:
        temp_path.write_text(yaml.safe_dump(data=payload, sort_keys=False))
        instance: YamlConfig = validator_cls.from_yaml(file_path=temp_path)
        if hasattr(instance, "__post_init__"):
            instance.__post_init__()
    except Exception as exception:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()
        return error_response(message=f"Validation failed for {validator_cls.__name__}: {exception}")
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()

    # Persists the validated instance to the final destination using the canonical serialization method.
    try:
        instance.to_yaml(file_path=file_path)
    except Exception as exception:
        return error_response(message=f"Failed to persist {validator_cls.__name__} to {file_path}: {exception}")

    return ok_response(file_path=str(file_path), data=serialize(value=instance))


def read_yaml(file_path: Path, validator_cls: type[YamlConfig]) -> dict[str, Any]:
    """Loads a YAML file via ``validator_cls`` and returns its serialized form.

    Args:
        file_path: The path to the YAML file to load.
        validator_cls: The YamlConfig dataclass to use for validation.

    Returns:
        A response dict with ``file_path`` and ``data`` (the serialized payload) on success, or an error dict
        on failure.
    """
    if not file_path.exists():
        return error_response(message=f"File not found: {file_path}")
    try:
        instance = validator_cls.from_yaml(file_path=file_path)
    except Exception as exception:
        return error_response(message=f"Failed to load {file_path} as {validator_cls.__name__}: {exception}")
    return ok_response(file_path=str(file_path), data=serialize(value=instance))


def resolve_root_directory(root_directory: str | None) -> tuple[Path | None, dict[str, Any] | None]:
    """Resolves the root data directory from an explicit override.

    Args:
        root_directory: An explicit path to the root data directory. Required; the previous fallback to the
            active system configuration's root directory was removed when the system configuration moved out of
            this package and into the acquisition runtime package (sl-experiment).

    Returns:
        A tuple of the resolved Path and an error dict. Exactly one element is non-None.
    """
    if root_directory is None:
        return None, error_response(
            message=(
                "Unable to resolve the root data directory. The 'root_directory' argument is now required — the "
                "active system configuration no longer lives in this package, so it cannot be auto-resolved here. "
                "Pass the root directory explicitly, or query it from the acquisition runtime's own MCP/CLI."
            ),
        )
    path = Path(root_directory)
    if not path.exists():
        return None, error_response(message=f"Root directory does not exist: {path}")
    if not path.is_dir():
        return None, error_response(message=f"Root directory is not a directory: {path}")
    return path, None


def session_root_from_marker(marker: Path) -> Path:
    """Returns the session root directory given a session_data.yaml marker file.

    The marker is expected at ``<session_root>/raw_data/session_data.yaml``, so the session root is two
    directory levels above the marker.

    Args:
        marker: The path to the ``session_data.yaml`` marker file.

    Returns:
        The session root directory two levels above the marker.
    """
    return marker.parents[1]


def safe_iterdir(directory: Path) -> list[Path]:
    """Returns immediate non-hidden children of a directory, ignoring permission errors.

    Args:
        directory: The directory whose children to list.

    Returns:
        A list of non-hidden child paths, or an empty list if a permission error occurs.
    """
    try:
        return [child for child in directory.iterdir() if not child.name.startswith(".")]
    except OSError:
        return []
