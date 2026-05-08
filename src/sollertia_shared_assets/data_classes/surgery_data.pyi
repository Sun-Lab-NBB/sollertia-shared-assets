from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

@dataclass(slots=True)
class SubjectData:
    id: int
    ear_punch: str
    sex: str
    genotype: str
    date_of_birth_us: int
    weight_g: float
    cage: int
    location_housed: str
    status: str

@dataclass(slots=True)
class ProcedureData:
    surgery_start_us: int
    surgery_end_us: int
    surgeon: str
    protocol: str
    surgery_notes: str
    post_op_notes: str
    surgery_quality: int = ...

@dataclass(slots=True)
class DrugData:
    lactated_ringers_solution_volume_ml: float
    lactated_ringers_solution_code: str
    ketoprofen_volume_ml: float
    ketoprofen_code: str
    buprenorphine_volume_ml: float
    buprenorphine_code: str
    dexamethasone_volume_ml: float
    dexamethasone_code: str

@dataclass(slots=True)
class ImplantData:
    implant: str
    implant_target: str
    implant_code: str
    implant_ap_coordinate_mm: float
    implant_ml_coordinate_mm: float
    implant_dv_coordinate_mm: float

@dataclass(slots=True)
class InjectionData:
    injection: str
    injection_target: str
    injection_volume_nl: float
    injection_code: str
    injection_ap_coordinate_mm: float
    injection_ml_coordinate_mm: float
    injection_dv_coordinate_mm: float

@dataclass
class SurgeryData(YamlConfig):
    subject: SubjectData
    procedure: ProcedureData
    drugs: DrugData
    implants: list[ImplantData]
    injections: list[InjectionData]
