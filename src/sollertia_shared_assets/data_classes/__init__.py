"""Provides the contract dataclasses that translate external data records into the uniform on-disk formats consumed
by the Sollertia platform libraries.

Each module in this package is a durable read-asset contract: it defines the dataclasses that represent one external
data shape (for example, the surgery log) on disk. Contract modules export plain dataclasses and never consume the
dispatch registries, so the ``registries`` hub can import them without circular imports.
"""

from .surgery_data import (
    DrugData,
    ImplantData,
    SubjectData,
    SurgeryData,
    InjectionData,
    ProcedureData,
)

__all__ = [
    "DrugData",
    "ImplantData",
    "InjectionData",
    "ProcedureData",
    "SubjectData",
    "SurgeryData",
]
