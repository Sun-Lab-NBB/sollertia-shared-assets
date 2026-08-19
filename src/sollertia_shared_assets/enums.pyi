from enum import StrEnum

class AcquisitionSystems(StrEnum):
    MESOSCOPE_VR = "mesoscope"

class SessionTypes(StrEnum):
    LICK_TRAINING = "lick training"
    RUN_TRAINING = "run training"
    MESOSCOPE_EXPERIMENT = "mesoscope experiment"
    WINDOW_CHECKING = "window checking"

class ReadAssets(StrEnum):
    SURGERY_DATA = "surgery_data"

class CredentialsTypes(StrEnum):
    GOOGLE = "google"
