"""Provides the shared FastMCP server instance, constants, and helper functions for MCP tool modules."""

from __future__ import annotations

from enum import Enum
import uuid
from typing import TYPE_CHECKING, Any, get_args, get_type_hints
from pathlib import Path
import contextlib
from dataclasses import MISSING, fields, is_dataclass

import yaml
from mcp.server.fastmcp import FastMCP

from ..data_classes import (
    DESCRIPTOR_REGISTRY,
    SessionData,
    RawDataFiles,
    SessionTypes,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from ataraxis_data_structures import YamlConfig

UNINITIALIZED_SESSION_MARKER: str = RawDataFiles.NK_MARKER.value
"""Marker file present in ``raw_data`` while a session is uninitialized and holds no data of value, making it a valid
purge target. Distinct from the descriptor's ``incomplete`` field, which marks an initialized session that hit a
runtime issue but still holds usable data."""

mcp = FastMCP(name="sollertia-shared-assets", json_response=True)
"""The shared FastMCP server instance on which all tool modules register their tools via ``@mcp.tool()``."""


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

    The recursion guard prevents infinite recursion when a dataclass references itself either directly or
    transitively.

    Args:
        cls: The dataclass type to describe.
        recurse: Determines whether to recursively describe nested dataclass fields.

    Returns:
        A schema dict of shape ``{"class": <name>, "fields": {<field_name>: {"type", "default"|"required",
        "nested"?}}}``, where ``nested`` recursively describes nested dataclass types.
    """

    def _describe_inner(target: type, seen: frozenset[type]) -> dict[str, Any]:
        # Guards against infinite recursion from self-referential or cyclic dataclass hierarchies.
        if target in seen:
            return {"class": target.__name__, "recursive_reference": True}
        next_seen = seen | {target}

        if not is_dataclass(target):
            return {"type": _describe_type(type_hint=target)}

        # noinspection PyBroadException
        try:
            hints = get_type_hints(target)
        except Exception:
            hints = {}

        schema: dict[str, Any] = {"class": target.__name__, "fields": {}}
        # noinspection PyDataclass
        for field_definition in fields(target):
            type_hint = hints.get(field_definition.name, field_definition.type)
            field_schema: dict[str, Any] = {"type": _describe_type(type_hint=type_hint)}
            if field_definition.default is not MISSING:
                field_schema["default"] = serialize(value=field_definition.default)
            elif field_definition.default_factory is not MISSING:
                # noinspection PyBroadException
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


def collect_field_dataclasses(cls: type, *, field_name: str | None = None) -> dict[str, type]:
    """Returns the dataclass types referenced by a dataclass's fields, keyed by class name.

    Walks each field's type hint one level deep, unwrapping container and union arguments (for example, the value
    type of a ``dict`` or the members of an ``A | B`` union) to collect the dataclass types it references. When
    ``field_name`` is provided, only that field is inspected, and an absent field yields no types. Schema
    introspection tools use this to describe a configuration's actual nested structure instead of hardcoding it.

    Args:
        cls: The dataclass type to inspect.
        field_name: When provided, restricts the inspection to the single named field.

    Returns:
        A mapping of class name to dataclass type for every dataclass referenced by the inspected field(s).
    """

    def _iter(type_hint: Any) -> Iterator[type]:  # noqa: ANN401 - introspection recurses over arbitrary type hints.
        if isinstance(type_hint, type):
            if is_dataclass(type_hint):
                yield type_hint
            return
        for argument in get_args(type_hint):
            yield from _iter(type_hint=argument)

    # noinspection PyBroadException
    try:
        hints = get_type_hints(cls)
    except Exception:
        return {}
    if field_name is not None:
        hints = {field_name: hints[field_name]} if field_name in hints else {}
    collected: dict[str, type] = {}
    for hint in hints.values():
        for candidate in _iter(type_hint=hint):
            collected.setdefault(candidate.__name__, candidate)
    return collected


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
        message = (
            f"Unable to write {validator_cls.__name__} to {file_path}: a file already exists at this path. "
            f"Pass overwrite=True to replace it."
        )
        return error_response(message=message)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    # Keeps the temp file ending in .yaml because YamlConfig.from_yaml() rejects non-.yaml paths.
    temp_path = file_path.with_name(f".{file_path.stem}.{uuid.uuid4().hex[:8]}.tmp.yaml")

    try:
        temp_path.write_text(yaml.safe_dump(data=payload, sort_keys=False))
        instance: YamlConfig = validator_cls.from_yaml(file_path=temp_path)
        if hasattr(instance, "__post_init__"):
            instance.__post_init__()
    except Exception as exception:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()
        message = f"Unable to validate the payload as {validator_cls.__name__}: {exception}"
        return error_response(message=message)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_path.unlink()

    try:
        instance.to_yaml(file_path=file_path)
    except Exception as exception:
        message = f"Unable to persist {validator_cls.__name__} to {file_path}: {exception}"
        return error_response(message=message)

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
        message = f"Unable to read {validator_cls.__name__} from {file_path}: the file does not exist."
        return error_response(message=message)
    try:
        instance = validator_cls.from_yaml(file_path=file_path)
    except Exception as exception:
        message = f"Unable to load {file_path} as {validator_cls.__name__}: {exception}"
        return error_response(message=message)
    return ok_response(file_path=str(file_path), data=serialize(value=instance))


def resolve_root_directory(root_directory: str) -> tuple[Path | None, dict[str, Any] | None]:
    """Resolves the root data directory from an explicit path.

    Args:
        root_directory: An absolute path to the root data directory.

    Returns:
        A tuple of the resolved Path and an error dict. Exactly one element is non-None.
    """
    path = Path(root_directory)
    if not path.exists():
        message = f"Unable to resolve the root data directory. The path {path} does not exist."
        return None, error_response(message=message)
    if not path.is_dir():
        message = f"Unable to resolve the root data directory. The path {path} is not a directory."
        return None, error_response(message=message)
    return path, None


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


def read_descriptor_incomplete(session: SessionData) -> tuple[bool | None, str | None]:
    """Loads the session's descriptor YAML and returns its ``incomplete`` field.

    Resolves the correct descriptor dataclass from the session's ``session_type`` via
    ``DESCRIPTOR_REGISTRY`` and parses the descriptor at ``<session>/raw_data/session_descriptor.yaml``.
    The descriptor's ``incomplete`` field is distinct from the ``nk.bin`` uninitialized marker: it
    indicates that the session ran to completion but encountered issues that may have left data gaps,
    while ``nk.bin`` indicates the session was never initialized at all.

    Args:
        session: The SessionData instance whose descriptor to load.

    Returns:
        A tuple of ``(incomplete, error_message)``. On success, ``incomplete`` is the boolean value
        of the descriptor's ``incomplete`` field and ``error_message`` is None. On failure,
        ``incomplete`` is None and ``error_message`` describes the failure.
    """
    descriptor_class = DESCRIPTOR_REGISTRY[SessionTypes(session.session_type)]
    descriptor_path = session.raw_data.session_descriptor_path
    if not descriptor_path.exists():
        return None, f"Descriptor file not found at {descriptor_path}"
    try:
        descriptor = descriptor_class.from_yaml(file_path=descriptor_path)
    except Exception as exception:
        return None, str(exception)
    # noinspection PyUnresolvedReferences
    return bool(descriptor.incomplete), None  # type: ignore[attr-defined]
