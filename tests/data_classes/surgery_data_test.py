"""Contains tests for the surgery dataclasses provided by the ``data_classes.surgery_data`` module."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sollertia_shared_assets.data_classes import (
    DrugData,
    ImplantData,
    SubjectData,
    SurgeryData,
    InjectionData,
    ProcedureData,
)

if TYPE_CHECKING:
    from pathlib import Path


def _make_subject() -> SubjectData:
    """Returns a fully populated SubjectData instance suitable for round-trip tests."""
    return SubjectData(
        id=42,
        ear_punch="left-1",
        sex="F",
        genotype="C57BL/6J",
        date_of_birth_us=1_700_000_000_000_000,
        weight_g=24.5,
        cage=7,
        location_housed="Vivarium A, Room 12",
        status="alive",
    )


def _make_procedure() -> ProcedureData:
    """Returns a fully populated ProcedureData instance suitable for round-trip tests."""
    return ProcedureData(
        surgery_start_us=1_700_001_000_000_000,
        surgery_end_us=1_700_001_005_400_000,
        surgeon="Dr. K. Gupta",
        protocol="2024-MESOSCOPE-001",
        surgery_notes="Bilateral implantation; minor bleeding controlled with gelfoam.",
        post_op_notes="Animal recovered within 60 minutes; ambulatory next morning.",
        surgery_quality=2,
    )


def _make_drugs() -> DrugData:
    """Returns a fully populated DrugData instance suitable for round-trip tests."""
    return DrugData(
        lactated_ringers_solution_volume_ml=1.5,
        lactated_ringers_solution_code="LRS-001",
        ketoprofen_volume_ml=0.05,
        ketoprofen_code="KETO-2024",
        buprenorphine_volume_ml=0.03,
        buprenorphine_code="BUPR-2024",
        dexamethasone_volume_ml=0.02,
        dexamethasone_code="DEXA-2024",
    )


def _make_implant() -> ImplantData:
    """Returns a fully populated ImplantData instance suitable for round-trip tests."""
    return ImplantData(
        implant="5mm cranial window",
        implant_target="primary visual cortex",
        implant_code="WIN-5MM-001",
        implant_ap_coordinate_mm=-3.5,
        implant_ml_coordinate_mm=2.5,
        implant_dv_coordinate_mm=0.0,
    )


def _make_injection() -> InjectionData:
    """Returns a fully populated InjectionData instance suitable for round-trip tests."""
    return InjectionData(
        injection="AAV9-GCaMP6s",
        injection_target="primary visual cortex layer 2/3",
        injection_volume_nl=200.0,
        injection_code="AAV-GCAMP6S-2024",
        injection_ap_coordinate_mm=-3.5,
        injection_ml_coordinate_mm=2.5,
        injection_dv_coordinate_mm=-0.4,
    )


def test_subject_data_initialization() -> None:
    """Verifies that SubjectData stores every supplied field verbatim."""
    subject = _make_subject()

    assert subject.id == 42
    assert subject.ear_punch == "left-1"
    assert subject.sex == "F"
    assert subject.genotype == "C57BL/6J"
    assert subject.date_of_birth_us == 1_700_000_000_000_000
    assert subject.weight_g == 24.5
    assert subject.cage == 7
    assert subject.location_housed == "Vivarium A, Room 12"
    assert subject.status == "alive"


def test_procedure_data_default_quality() -> None:
    """Verifies that ProcedureData.surgery_quality defaults to 0."""
    procedure = ProcedureData(
        surgery_start_us=0,
        surgery_end_us=0,
        surgeon="",
        protocol="",
        surgery_notes="",
        post_op_notes="",
    )

    assert procedure.surgery_quality == 0


def test_implant_data_initialization() -> None:
    """Verifies that ImplantData stores every supplied field verbatim."""
    implant = _make_implant()

    assert implant.implant == "5mm cranial window"
    assert implant.implant_target == "primary visual cortex"
    assert implant.implant_ap_coordinate_mm == -3.5
    assert implant.implant_ml_coordinate_mm == 2.5
    assert implant.implant_dv_coordinate_mm == 0.0


def test_injection_data_initialization() -> None:
    """Verifies that InjectionData stores every supplied field verbatim."""
    injection = _make_injection()

    assert injection.injection == "AAV9-GCaMP6s"
    assert injection.injection_volume_nl == 200.0
    assert injection.injection_code == "AAV-GCAMP6S-2024"


def test_surgery_data_yaml_round_trip(tmp_path: Path) -> None:
    """Verifies that SurgeryData round-trips through YAML with all nested sections preserved."""
    surgery = SurgeryData(
        subject=_make_subject(),
        procedure=_make_procedure(),
        drugs=_make_drugs(),
        implants=[_make_implant()],
        injections=[_make_injection()],
    )

    yaml_path = tmp_path / "surgery_metadata.yaml"
    surgery.to_yaml(file_path=yaml_path)
    loaded = SurgeryData.from_yaml(file_path=yaml_path)

    assert loaded == surgery


def test_surgery_data_round_trips_multi_implant_multi_injection(tmp_path: Path) -> None:
    """Verifies that SurgeryData preserves multiple implants and injections through YAML."""
    surgery = SurgeryData(
        subject=_make_subject(),
        procedure=_make_procedure(),
        drugs=_make_drugs(),
        implants=[
            _make_implant(),
            ImplantData(
                implant="6mm cranial window",
                implant_target="primary auditory cortex",
                implant_code="WIN-6MM-002",
                implant_ap_coordinate_mm=-2.5,
                implant_ml_coordinate_mm=4.0,
                implant_dv_coordinate_mm=0.0,
            ),
        ],
        injections=[
            _make_injection(),
            InjectionData(
                injection="AAV9-tdTomato",
                injection_target="primary auditory cortex layer 5",
                injection_volume_nl=100.0,
                injection_code="AAV-TDTOM-2024",
                injection_ap_coordinate_mm=-2.5,
                injection_ml_coordinate_mm=4.0,
                injection_dv_coordinate_mm=-0.6,
            ),
        ],
    )

    yaml_path = tmp_path / "surgery_metadata.yaml"
    surgery.to_yaml(file_path=yaml_path)
    loaded = SurgeryData.from_yaml(file_path=yaml_path)

    assert len(loaded.implants) == 2
    assert len(loaded.injections) == 2
    assert loaded == surgery
