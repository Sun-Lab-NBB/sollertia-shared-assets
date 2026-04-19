"""Provides assets for storing animal surgery data extracted from the Sollertia platform surgery log."""

from __future__ import annotations

from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig


@dataclass(slots=True)
class SubjectData:  # pragma: no cover
    """Stores information about the subject of the surgical intervention."""

    id: int
    """The subject's unique identifier."""
    ear_punch: str
    """The number and the locations of ear-tags used to distinguish the subject from its cage-mates."""
    sex: str
    """The subject's sex."""
    genotype: str
    """The subject's genotype."""
    date_of_birth_us: int
    """The subject's date of birth, stored as the number of microseconds elapsed since the UTC epoch onset."""
    weight_g: float
    """The subject's pre-surgery weight, in grams."""
    cage: int
    """The unique identifier (number) of the cage used to house the subject after the surgery."""
    location_housed: str
    """The location (room) used to house the subject after the surgery."""
    status: str
    """The current subject's status (alive / deceased)."""


@dataclass(slots=True)
class ProcedureData:  # pragma: no cover
    """Stores general information about the surgical intervention."""

    surgery_start_us: int
    """The surgery's start date and time as microseconds elapsed since UTC epoch onset."""
    surgery_end_us: int
    """The surgery's stop date and time as microseconds elapsed since UTC epoch onset."""
    surgeon: str
    """The surgeon's name or ID. If the intervention was carried out by multiple surgeons, the data
    for all surgeons is stored as part of the same string."""
    protocol: str
    """The number (ID) of the experiment protocol used during the surgery."""
    surgery_notes: str
    """The surgeon's notes taken during the surgery."""
    post_op_notes: str
    """The surgeon's notes taken during the post-surgery recovery period."""
    surgery_quality: int = 0
    """The quality of the surgical intervention on a scale from 0 to 3 inclusive. 0 indicates unusable (bad) result, 1
    indicates usable result that does not meet the publication threshold, 2 indicates publication-grade
    result, 3 indicates high-tier publication grade result."""


@dataclass(slots=True)
class DrugData:  # pragma: no cover
    """Stores information about all medical substances (drugs) administered to the subject before, during, and
    immediately after the surgical intervention.
    """

    lactated_ringers_solution_volume_ml: float
    """The volume of Lactated Ringer's Solution (LRS) administered during the surgery, in milliliters."""
    lactated_ringers_solution_code: str
    """The manufacturer code or internal reference code for the administered Lactated Ringer's Solution (LRS)."""
    ketoprofen_volume_ml: float
    """The volume of diluted ketoprofen administered during the surgery, in milliliters."""
    ketoprofen_code: str
    """The manufacturer code or internal reference code for the administered ketoprofen."""
    buprenorphine_volume_ml: float
    """The volume of diluted buprenorphine administered during the surgery, in milliliters."""
    buprenorphine_code: str
    """The manufacturer code or internal reference code for the administered buprenorphine."""
    dexamethasone_volume_ml: float
    """The volume of diluted dexamethasone administered during the surgery, in milliliters."""
    dexamethasone_code: str
    """The manufacturer code or internal reference code for the administered dexamethasone."""


@dataclass(slots=True)
class ImplantData:  # pragma: no cover
    """Stores information about a single implantation procedure performed during the surgical intervention.

    Multiple ImplantData instances can be used at the same time if the surgery involved multiple implantation
    procedures.
    """

    implant: str
    """The descriptive name of the implant."""
    implant_target: str
    """The name of the brain region or cranium section targeted by the implant."""
    implant_code: str
    """The manufacturer code or internal reference code for the implant."""
    implant_ap_coordinate_mm: float
    """The implant's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    implant_ml_coordinate_mm: float
    """The implant's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    implant_dv_coordinate_mm: float
    """The implant's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass(slots=True)
class InjectionData:  # pragma: no cover
    """Stores information about a single injection performed during the surgical intervention.

    Multiple InjectionData instances can be used at the same time if the surgery involved multiple injections.
    """

    injection: str
    """The descriptive name of the injection."""
    injection_target: str
    """The name of the brain region targeted by the injection."""
    injection_volume_nl: float
    """The volume of substance, in nanoliters, delivered during the injection."""
    injection_code: str
    """The manufacturer code or internal reference code for the injected substance."""
    injection_ap_coordinate_mm: float
    """The injection's antero-posterior stereotactic coordinate, in millimeters, relative to bregma."""
    injection_ml_coordinate_mm: float
    """The injection's medial-lateral stereotactic coordinate, in millimeters, relative to bregma."""
    injection_dv_coordinate_mm: float
    """The injection's dorsal-ventral stereotactic coordinate, in millimeters, relative to bregma."""


@dataclass
class SurgeryData(YamlConfig):  # pragma: no cover
    """Stores information about a surgical intervention performed on an animal before data acquisition session(s)."""

    subject: SubjectData
    """Stores information about the subject of the surgical intervention."""
    procedure: ProcedureData
    """Stores general information about the surgical intervention."""
    drugs: DrugData
    """Stores information about all medical substances (drugs) administered to the subject before, during, and
    immediately after the surgical intervention."""
    implants: list[ImplantData]
    """Stores information about all implantation procedures performed during the surgical intervention."""
    injections: list[InjectionData]
    """Stores information about all injections (brain infusions) performed during the surgical intervention."""
