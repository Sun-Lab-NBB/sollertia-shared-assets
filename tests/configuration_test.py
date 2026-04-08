"""Contains tests for classes and methods provided by the configuration module."""

from pathlib import Path

import pytest
import platformdirs

from sollertia_shared_assets.configuration import (
    AcquisitionSystems,
    Cue,
    Segment,
    VREnvironment,
    GasPuffTrial,
    WaterRewardTrial,
    ExperimentState,
    MesoscopeExperimentConfiguration,
    MesoscopeFileSystem,
    MesoscopeCameras,
    MesoscopeMicroControllers,
    MesoscopeExternalAssets,
    MesoscopeSystemConfiguration,
    MesoscopeGoogleSheets,
    ServerConfiguration,
    get_working_directory,
    set_working_directory,
    get_system_configuration_data,
    get_google_credentials_path,
    set_google_credentials_path,
    get_server_configuration,
    create_system_configuration_file,
    create_server_configuration_file,
)


@pytest.fixture
def sample_mesoscope_config() -> MesoscopeSystemConfiguration:
    """Creates a sample MesoscopeSystemConfiguration for testing."""
    config = MesoscopeSystemConfiguration()
    config.filesystem.root_directory = Path("/data/projects")
    config.filesystem.server_directory = Path("/mnt/server/projects")
    config.filesystem.nas_directory = Path("/mnt/nas/backup")
    config.filesystem.mesoscope_directory = Path("/mnt/mesoscope/data")
    config.sheets.surgery_sheet_id = "abc123"
    config.sheets.water_log_sheet_id = "xyz789"
    return config


@pytest.fixture
def sample_experiment_config() -> MesoscopeExperimentConfiguration:
    """Creates a sample MesoscopeExperimentConfiguration for testing."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
    )

    # Cues: A->50, B->75, C->50 = 175 total for Segment_abc
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=2, length_cm=75.0),
        Cue(name="C", code=3, length_cm=50.0),
    ]

    segments = [
        Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None),
    ]

    # Trial references the segment - cue_sequence and trial_length_cm are derived
    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=150.0,
        stimulus_trigger_zone_end_cm=175.0,
        stimulus_location_cm=160.0,
        show_stimulus_collision_boundary=False,
    )

    config = MesoscopeExperimentConfiguration(
        cues=cues,
        segments=segments,
        trial_structures={"trial1": trial},
        experiment_states={"state1": state},
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
        ),
        unity_scene_name="TestScene",
        cue_offset_cm=10.0,
    )

    return config


@pytest.fixture
def clean_working_directory(tmp_path, monkeypatch):
    """Sets up a clean temporary working directory for testing."""
    # Patches platformdirs to use temporary directory
    app_dir = tmp_path / "app_data"
    app_dir.mkdir()
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    working_dir = tmp_path / "working_directory"
    working_dir.mkdir()

    return working_dir


# Tests for AcquisitionSystems enumeration


def test_acquisition_systems_mesoscope_vr():
    """Verifies the MESOSCOPE_VR acquisition system enumeration value.

    This test ensures the enumeration contains the expected string value.
    """
    assert AcquisitionSystems.MESOSCOPE_VR == "mesoscope"
    assert str(AcquisitionSystems.MESOSCOPE_VR) == "mesoscope"


def test_acquisition_systems_is_string_enum():
    """Verifies that AcquisitionSystems inherits from StrEnum.

    This test ensures the enumeration members behave as strings.
    """
    assert isinstance(AcquisitionSystems.MESOSCOPE_VR, str)


# Tests for ExperimentState dataclass


def test_mesoscope_experiment_state_initialization():
    """Verifies basic initialization of ExperimentState.

    This test ensures all fields are properly assigned during initialization.
    """
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
        aversive_initial_guided_trials=5,
        aversive_recovery_failed_threshold=3,
        aversive_recovery_guided_trials=2,
    )

    assert state.experiment_state_code == 1
    assert state.system_state_code == 0
    assert state.state_duration_s == 600.0
    assert state.supports_trials is True
    assert state.reinforcing_initial_guided_trials == 10
    assert state.reinforcing_recovery_failed_threshold == 5
    assert state.reinforcing_recovery_guided_trials == 3
    assert state.aversive_initial_guided_trials == 5
    assert state.aversive_recovery_failed_threshold == 3
    assert state.aversive_recovery_guided_trials == 2


def test_mesoscope_experiment_state_types():
    """Verifies the data types of ExperimentState fields.

    This test ensures each field has the expected type.
    """
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
    )

    assert isinstance(state.experiment_state_code, int)
    assert isinstance(state.system_state_code, int)
    assert isinstance(state.state_duration_s, float)
    assert isinstance(state.supports_trials, bool)
    assert isinstance(state.reinforcing_initial_guided_trials, int)
    assert isinstance(state.reinforcing_recovery_failed_threshold, int)
    assert isinstance(state.reinforcing_recovery_guided_trials, int)
    assert isinstance(state.aversive_initial_guided_trials, int)
    assert isinstance(state.aversive_recovery_failed_threshold, int)
    assert isinstance(state.aversive_recovery_guided_trials, int)


# Tests for Trial dataclasses (WaterRewardTrial, GasPuffTrial)
#
# Note: Trials now use segment_name to reference a segment, and cue_sequence/trial_length_cm
# are derived fields populated by MesoscopeExperimentConfiguration.__post_init__.
# Zone validation requires trial_length_cm > 0, so zone tests must go through the full config.


def _create_test_config_with_trial(trial: WaterRewardTrial | GasPuffTrial) -> MesoscopeExperimentConfiguration:
    """Helper to create a MesoscopeExperimentConfiguration for testing a trial.

    The segment "TestSegment" has cues that sum to 200.0 cm.
    """
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=2, length_cm=50.0),
        Cue(name="C", code=3, length_cm=50.0),
        Cue(name="D", code=4, length_cm=50.0),
    ]
    segments = [Segment(name="TestSegment", cue_sequence=["A", "B", "C", "D"], transition_probabilities=None)]
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=60.0,
        supports_trials=True,
    )
    return MesoscopeExperimentConfiguration(
        cues=cues,
        segments=segments,
        trial_structures={"test_trial": trial},
        experiment_states={"state1": state},
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
        ),
        unity_scene_name="TestScene",
    )


def test_water_reward_trial_initialization():
    """Verifies basic initialization of WaterRewardTrial.

    This test ensures all fields are properly assigned during initialization.
    """
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    # Creates config to populate derived fields
    config = _create_test_config_with_trial(trial)
    populated_trial = config.trial_structures["test_trial"]

    assert populated_trial.segment_name == "TestSegment"
    assert populated_trial.cue_sequence == [1, 2, 3, 4]  # Derived from segment
    assert populated_trial.trial_length_cm == 200.0  # Derived from segment (4 * 50.0)
    assert populated_trial.stimulus_trigger_zone_start_cm == 180.0
    assert populated_trial.stimulus_trigger_zone_end_cm == 200.0
    assert populated_trial.stimulus_location_cm == 190.0
    assert populated_trial.show_stimulus_collision_boundary is False
    assert populated_trial.reward_size_ul == 5.0
    assert populated_trial.reward_tone_duration_ms == 300


def test_gas_puff_trial_initialization():
    """Verifies basic initialization of GasPuffTrial.

    This test ensures all fields are properly assigned during initialization.
    """
    trial = GasPuffTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    # Creates config to populate derived fields
    config = _create_test_config_with_trial(trial)
    populated_trial = config.trial_structures["test_trial"]

    assert populated_trial.segment_name == "TestSegment"
    assert populated_trial.cue_sequence == [1, 2, 3, 4]  # Derived from segment
    assert populated_trial.trial_length_cm == 200.0  # Derived from segment (4 * 50.0)
    assert populated_trial.stimulus_trigger_zone_start_cm == 180.0
    assert populated_trial.stimulus_trigger_zone_end_cm == 200.0
    assert populated_trial.stimulus_location_cm == 190.0
    assert populated_trial.show_stimulus_collision_boundary is False
    assert populated_trial.puff_duration_ms == 100
    assert populated_trial.occupancy_duration_ms == 1000


def test_trial_types():
    """Verifies the data types of trial fields.

    This test ensures each field has the expected type for both trial classes.
    """
    water_trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    # Creates config to populate derived fields
    config = _create_test_config_with_trial(water_trial)
    water_trial = config.trial_structures["test_trial"]

    assert isinstance(water_trial.segment_name, str)
    assert isinstance(water_trial.cue_sequence, list)
    assert all(isinstance(cue, int) for cue in water_trial.cue_sequence)
    assert isinstance(water_trial.trial_length_cm, float)
    assert isinstance(water_trial.stimulus_trigger_zone_start_cm, float)
    assert isinstance(water_trial.stimulus_trigger_zone_end_cm, float)
    assert isinstance(water_trial.stimulus_location_cm, float)
    assert isinstance(water_trial.show_stimulus_collision_boundary, bool)
    assert isinstance(water_trial.reward_size_ul, float)
    assert isinstance(water_trial.reward_tone_duration_ms, int)

    gas_trial = GasPuffTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )

    # Creates config to populate derived fields
    config = _create_test_config_with_trial(gas_trial)
    gas_trial = config.trial_structures["test_trial"]

    assert isinstance(gas_trial.puff_duration_ms, int)
    assert isinstance(gas_trial.occupancy_duration_ms, int)
    assert isinstance(gas_trial.show_stimulus_collision_boundary, bool)


# Tests for Trial validation


def test_trial_zone_end_less_than_start():
    """Verifies that zone_end < zone_start raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=170.0,  # Less than start
        stimulus_location_cm=175.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match="must be greater than or equal to"):
        _create_test_config_with_trial(trial)


def test_trial_zone_start_outside_trial_length():
    """Verifies that zone_start outside trial length raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=250.0,  # Outside trial length (200)
        stimulus_trigger_zone_end_cm=260.0,
        stimulus_location_cm=255.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match="stimulus_trigger_zone_start_cm.*must be within"):
        _create_test_config_with_trial(trial)


def test_trial_zone_end_outside_trial_length():
    """Verifies that zone_end outside trial length raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=250.0,  # Outside trial length (200)
        stimulus_location_cm=190.0,
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match="stimulus_trigger_zone_end_cm.*must be within"):
        _create_test_config_with_trial(trial)


def test_trial_stimulus_location_outside_trial_length():
    """Verifies that stimulus_location outside trial length raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=250.0,  # Outside trial length (200)
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match="stimulus_location_cm.*must be within"):
        _create_test_config_with_trial(trial)


def test_trial_stimulus_location_precedes_trigger_zone():
    """Verifies that stimulus_location before trigger zone start raises ValueError during config validation."""
    trial = WaterRewardTrial(
        segment_name="TestSegment",
        stimulus_trigger_zone_start_cm=180.0,
        stimulus_trigger_zone_end_cm=200.0,
        stimulus_location_cm=170.0,  # Before trigger zone start (180)
        show_stimulus_collision_boundary=False,
    )
    with pytest.raises(ValueError, match="stimulus_location_cm.*cannot precede"):
        _create_test_config_with_trial(trial)


# Tests for MesoscopeExperimentConfiguration validation


def test_experiment_config_invalid_segment_reference():
    """Verifies that a trial referencing an unknown segment raises ValueError."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
    )

    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=2, length_cm=75.0),
    ]
    segments = [Segment(name="Segment_ab", cue_sequence=["A", "B"], transition_probabilities=None)]

    trial = WaterRewardTrial(
        segment_name="NonexistentSegment",  # Does not exist
        stimulus_trigger_zone_start_cm=100.0,
        stimulus_trigger_zone_end_cm=125.0,
        stimulus_location_cm=110.0,
        show_stimulus_collision_boundary=False,
    )

    with pytest.raises(ValueError, match="references unknown segment.*NonexistentSegment"):
        MesoscopeExperimentConfiguration(
            cues=cues,
            segments=segments,
            trial_structures={"trial1": trial},
            experiment_states={"state1": state},
            vr_environment=VREnvironment(
                corridor_spacing_cm=100.0,
                segments_per_corridor=3,
                padding_prefab_name="Padding",
                cm_per_unity_unit=10.0,
            ),
            unity_scene_name="TestScene",
        )


def test_experiment_config_invalid_cue_in_segment():
    """Verifies that a segment referencing an unknown cue raises ValueError."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
    )

    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=2, length_cm=75.0),
    ]
    # Segment references cue "C" which doesn't exist
    segments = [Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None)]

    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=100.0,
        stimulus_trigger_zone_end_cm=125.0,
        stimulus_location_cm=110.0,
        show_stimulus_collision_boundary=False,
    )

    with pytest.raises(ValueError, match="references unknown cue.*C"):
        MesoscopeExperimentConfiguration(
            cues=cues,
            segments=segments,
            trial_structures={"trial1": trial},
            experiment_states={"state1": state},
            vr_environment=VREnvironment(
                corridor_spacing_cm=100.0,
                segments_per_corridor=3,
                padding_prefab_name="Padding",
                cm_per_unity_unit=10.0,
            ),
            unity_scene_name="TestScene",
        )


def test_experiment_config_derives_trial_fields():
    """Verifies that trial cue_sequence and trial_length_cm are derived from segment."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
    )

    # Cues: A->50, B->75, C->50 = 175 total
    cues = [
        Cue(name="A", code=1, length_cm=50.0),
        Cue(name="B", code=2, length_cm=75.0),
        Cue(name="C", code=3, length_cm=50.0),
    ]
    segments = [Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None)]

    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=150.0,
        stimulus_trigger_zone_end_cm=175.0,
        stimulus_location_cm=160.0,
        show_stimulus_collision_boundary=False,
    )

    config = MesoscopeExperimentConfiguration(
        cues=cues,
        segments=segments,
        trial_structures={"trial1": trial},
        experiment_states={"state1": state},
        vr_environment=VREnvironment(
            corridor_spacing_cm=100.0,
            segments_per_corridor=3,
            padding_prefab_name="Padding",
            cm_per_unity_unit=10.0,
        ),
        unity_scene_name="TestScene",
        cue_offset_cm=10.0,
    )

    # Verify derived fields
    assert config.trial_structures["trial1"].cue_sequence == [1, 2, 3]
    assert config.trial_structures["trial1"].trial_length_cm == 175.0


# Tests for MesoscopeFileSystem dataclass


def test_mesoscope_filesystem_default_initialization():
    """Verifies default initialization of MesoscopeFileSystem.

    This test ensures all fields have default Path() values.
    """
    filesystem = MesoscopeFileSystem()

    assert filesystem.root_directory == Path()
    assert filesystem.server_directory == Path()
    assert filesystem.nas_directory == Path()
    assert filesystem.mesoscope_directory == Path()


def test_mesoscope_filesystem_custom_initialization():
    """Verifies custom initialization of MesoscopeFileSystem.

    This test ensures all fields accept custom Path values.
    """
    filesystem = MesoscopeFileSystem(
        root_directory=Path("/data/root"),
        server_directory=Path("/mnt/server"),
        nas_directory=Path("/mnt/nas"),
        mesoscope_directory=Path("/mnt/mesoscope"),
    )

    assert filesystem.root_directory == Path("/data/root")
    assert filesystem.server_directory == Path("/mnt/server")
    assert filesystem.nas_directory == Path("/mnt/nas")
    assert filesystem.mesoscope_directory == Path("/mnt/mesoscope")


# Tests for MesoscopeGoogleSheets dataclass


def test_mesoscope_google_sheets_default_initialization():
    """Verifies default initialization of MesoscopeGoogleSheets.

    This test ensures all fields have appropriate default values.
    """
    sheets = MesoscopeGoogleSheets()

    assert sheets.surgery_sheet_id == ""
    assert sheets.water_log_sheet_id == ""


def test_mesoscope_google_sheets_custom_initialization():
    """Verifies custom initialization of MesoscopeGoogleSheets.

    This test ensures all fields accept custom values.
    """
    sheets = MesoscopeGoogleSheets(
        surgery_sheet_id="abc123xyz",
        water_log_sheet_id="def456uvw",
    )

    assert sheets.surgery_sheet_id == "abc123xyz"
    assert sheets.water_log_sheet_id == "def456uvw"


# Tests for MesoscopeCameras dataclass


def test_mesoscope_cameras_default_initialization():
    """Verifies default initialization of MesoscopeCameras.

    This test ensures all fields have appropriate default values.
    """
    cameras = MesoscopeCameras()

    assert cameras.face_camera_index == 0
    assert cameras.body_camera_index == 1
    assert cameras.face_camera_quantization == 20
    assert cameras.face_camera_preset == 7
    assert cameras.body_camera_quantization == 20
    assert cameras.body_camera_preset == 7


def test_mesoscope_cameras_custom_initialization():
    """Verifies custom initialization of MesoscopeCameras.

    This test ensures all fields accept custom values.
    """
    cameras = MesoscopeCameras(
        face_camera_index=2,
        body_camera_index=3,
        face_camera_quantization=18,
        face_camera_preset=7,
        body_camera_quantization=20,
        body_camera_preset=8,
    )

    assert cameras.face_camera_index == 2
    assert cameras.body_camera_index == 3
    assert cameras.face_camera_quantization == 18
    assert cameras.face_camera_preset == 7
    assert cameras.body_camera_quantization == 20
    assert cameras.body_camera_preset == 8


# Tests for MesoscopeMicroControllers dataclass


def test_mesoscope_microcontrollers_default_initialization():
    """Verifies default initialization of MesoscopeMicroControllers.

    This test ensures all fields have appropriate default values.
    """
    mcu = MesoscopeMicroControllers()

    assert mcu.actor_port == "/dev/ttyACM0"
    assert mcu.sensor_port == "/dev/ttyACM1"
    assert mcu.encoder_port == "/dev/ttyACM2"
    assert mcu.wheel_diameter_cm == 15.0333
    assert mcu.lick_threshold_adc == 600
    assert len(mcu.valve_calibration_data) == 4


def test_mesoscope_microcontrollers_valve_calibration_tuple():
    """Verifies valve_calibration_data is stored as a tuple of tuples.

    This test ensures the valve calibration data has the correct structure.
    """
    mcu = MesoscopeMicroControllers()

    assert isinstance(mcu.valve_calibration_data, tuple)
    assert all(isinstance(item, tuple) for item in mcu.valve_calibration_data)
    assert all(len(item) == 2 for item in mcu.valve_calibration_data)
    assert all(
        isinstance(item[0], (int, float)) and isinstance(item[1], (int, float)) for item in mcu.valve_calibration_data
    )


def test_mesoscope_microcontrollers_custom_valve_calibration():
    """Verifies custom valve_calibration_data initialization.

    This test ensures custom calibration data can be provided during initialization.
    """
    custom_calibration = ((10000, 0.5), (20000, 1.5), (30000, 3.0))
    mcu = MesoscopeMicroControllers(valve_calibration_data=custom_calibration)

    assert mcu.valve_calibration_data == custom_calibration
    assert len(mcu.valve_calibration_data) == 3


# Tests for MesoscopeExternalAssets dataclass


def test_mesoscope_external_assets_default_initialization():
    """Verifies default initialization of MesoscopeExternalAssets.

    This test ensures all fields have appropriate default values.
    """
    assets = MesoscopeExternalAssets()

    assert assets.headbar_port == "/dev/ttyUSB0"
    assert assets.lickport_port == "/dev/ttyUSB1"
    assert assets.wheel_port == "/dev/ttyUSB2"
    assert assets.unity_ip == "127.0.0.1"
    assert assets.unity_port == 1883


def test_mesoscope_external_assets_custom_initialization():
    """Verifies custom initialization of MesoscopeExternalAssets.

    This test ensures all fields accept custom values.
    """
    assets = MesoscopeExternalAssets(
        headbar_port="/dev/ttyUSB3",
        lickport_port="/dev/ttyUSB4",
        wheel_port="/dev/ttyUSB5",
        unity_ip="192.168.1.100",
        unity_port=1884,
    )

    assert assets.headbar_port == "/dev/ttyUSB3"
    assert assets.lickport_port == "/dev/ttyUSB4"
    assert assets.wheel_port == "/dev/ttyUSB5"
    assert assets.unity_ip == "192.168.1.100"
    assert assets.unity_port == 1884


# Tests for MesoscopeSystemConfiguration dataclass


def test_mesoscope_system_configuration_default_initialization():
    """Verifies default initialization of MesoscopeSystemConfiguration.

    This test ensures the class initializes with default nested dataclasses.
    """
    config = MesoscopeSystemConfiguration()

    assert config.name == str(AcquisitionSystems.MESOSCOPE_VR)
    assert isinstance(config.filesystem, MesoscopeFileSystem)
    assert isinstance(config.sheets, MesoscopeGoogleSheets)
    assert isinstance(config.cameras, MesoscopeCameras)
    assert isinstance(config.microcontrollers, MesoscopeMicroControllers)
    assert isinstance(config.assets, MesoscopeExternalAssets)


def test_mesoscope_system_configuration_post_init_path_conversion():
    """Verifies that __post_init__ converts string paths to Path objects.

    This test ensures path fields are properly converted during initialization.
    """
    config = MesoscopeSystemConfiguration()
    # noinspection PyTypeChecker
    config.filesystem.root_directory = "/data/projects"
    # noinspection PyTypeChecker
    config.filesystem.server_directory = "/mnt/server"

    # Simulates re-initialization (would happen during YAML loading)
    config.__post_init__()

    assert isinstance(config.filesystem.root_directory, Path)
    assert isinstance(config.filesystem.server_directory, Path)


def test_mesoscope_system_configuration_post_init_valve_calibration_dict():
    """Verifies that __post_init__ converts valve_calibration_data dict to tuple.

    This test ensures valve calibration data is converted from dict to tuple format.
    """
    config = MesoscopeSystemConfiguration()
    config.microcontrollers.valve_calibration_data = {
        10000: 0.5,
        20000: 1.5,
        30000: 3.0,
    }

    config.__post_init__()

    assert isinstance(config.microcontrollers.valve_calibration_data, tuple)
    assert len(config.microcontrollers.valve_calibration_data) == 3
    assert (10000, 0.5) in config.microcontrollers.valve_calibration_data


def test_mesoscope_system_configuration_post_init_invalid_valve_calibration():
    """Verifies that __post_init__ raises TypeError for invalid valve calibration data.

    This test ensures improper calibration data structure is detected and rejected.
    """
    config = MesoscopeSystemConfiguration()
    # noinspection PyTypeChecker
    config.microcontrollers.valve_calibration_data = ((10000, "invalid"), (20000, 1.5))

    with pytest.raises(TypeError):
        config.__post_init__()


def test_mesoscope_system_configuration_save_yaml(tmp_path, sample_mesoscope_config):
    """Verifies that save() correctly writes configuration to YAML file.

    This test ensures configuration data is properly saved as YAML.
    """
    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    assert yaml_path.exists()
    assert yaml_path.stat().st_size > 0

    # Verifies file contains YAML content
    content = yaml_path.read_text()
    assert "name:" in content
    assert "filesystem:" in content
    assert "mesoscope" in content


def test_mesoscope_system_configuration_save_converts_paths(tmp_path, sample_mesoscope_config):
    """Verifies that save() converts Path objects to strings in YAML.

    This test ensures Path objects are serialized as strings in the YAML file.
    """
    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    content = yaml_path.read_text()

    # Verifies paths are stored as strings (not Path objects)
    assert "/data/projects" in content
    assert "/mnt/server/projects" in content
    assert "Path(" not in content


def test_mesoscope_system_configuration_save_converts_valve_calibration(tmp_path, sample_mesoscope_config):
    """Verifies that save() converts valve calibration tuple to dict in YAML.

    This test ensures valve calibration data is serialized as a dictionary.
    """
    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    content = yaml_path.read_text()

    # Verifies valve calibration is stored as key-value pairs
    assert "15000:" in content or "15000.0:" in content
    assert "valve_calibration_data:" in content


def test_mesoscope_system_configuration_save_does_not_modify_original(tmp_path, sample_mesoscope_config):
    """Verifies that save() does not modify the original configuration instance.

    This test ensures the original instance remains unchanged after saving.
    """
    original_root = sample_mesoscope_config.filesystem.root_directory
    original_valve_data = sample_mesoscope_config.microcontrollers.valve_calibration_data

    yaml_path = tmp_path / "test_config.yaml"
    sample_mesoscope_config.save(path=yaml_path)

    # Verifies original data is unchanged
    assert isinstance(sample_mesoscope_config.filesystem.root_directory, Path)
    assert sample_mesoscope_config.filesystem.root_directory == original_root
    assert isinstance(sample_mesoscope_config.microcontrollers.valve_calibration_data, tuple)
    assert sample_mesoscope_config.microcontrollers.valve_calibration_data == original_valve_data


def test_mesoscope_system_configuration_yaml_round_trip(tmp_path, sample_mesoscope_config):
    """Verifies that configuration can be saved and loaded without data loss.

    This test ensures YAML serialization/deserialization preserves all data.
    """
    yaml_path = tmp_path / "test_config.yaml"

    # Saves configuration
    sample_mesoscope_config.save(path=yaml_path)

    # Loads configuration
    loaded_config = MesoscopeSystemConfiguration.from_yaml(file_path=yaml_path)

    # Verifies data integrity
    assert loaded_config.name == sample_mesoscope_config.name
    assert loaded_config.filesystem.root_directory == sample_mesoscope_config.filesystem.root_directory
    assert loaded_config.sheets.surgery_sheet_id == sample_mesoscope_config.sheets.surgery_sheet_id
    assert loaded_config.cameras.face_camera_index == sample_mesoscope_config.cameras.face_camera_index
    assert (
        loaded_config.microcontrollers.valve_calibration_data
        == sample_mesoscope_config.microcontrollers.valve_calibration_data
    )


# Tests for MesoscopeExperimentConfiguration


def test_mesoscope_experiment_configuration_initialization(sample_experiment_config):
    """Verifies basic initialization of MesoscopeExperimentConfiguration.

    This test ensures all fields are properly assigned during initialization.
    """
    assert len(sample_experiment_config.cues) == 3
    assert len(sample_experiment_config.segments) == 1
    assert sample_experiment_config.cue_offset_cm == 10.0
    assert sample_experiment_config.unity_scene_name == "TestScene"
    assert "state1" in sample_experiment_config.experiment_states
    assert "trial1" in sample_experiment_config.trial_structures


def test_mesoscope_experiment_configuration_nested_structures(sample_experiment_config):
    """Verifies nested dataclass structures in MesoscopeExperimentConfiguration.

    This test ensures nested experiment states and trials are properly initialized.
    """
    state = sample_experiment_config.experiment_states["state1"]
    assert isinstance(state, ExperimentState)
    assert state.experiment_state_code == 1

    trial = sample_experiment_config.trial_structures["trial1"]
    assert isinstance(trial, WaterRewardTrial)
    assert trial.cue_sequence == [1, 2, 3]  # Derived from Segment_abc


def test_mesoscope_experiment_configuration_yaml_serialization(tmp_path, sample_experiment_config):
    """Verifies that MesoscopeExperimentConfiguration can be saved as YAML.

    This test ensures the experiment configuration is properly serialized to YAML.
    """
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    assert yaml_path.exists()
    content = yaml_path.read_text()

    assert "cues:" in content
    assert "unity_scene_name:" in content
    assert "TestScene" in content


def test_mesoscope_experiment_configuration_yaml_deserialization(tmp_path, sample_experiment_config):
    """Verifies that MesoscopeExperimentConfiguration can be loaded from YAML.

    This test ensures the experiment configuration is properly deserialized from YAML.
    """
    yaml_path = tmp_path / "experiment_config.yaml"
    sample_experiment_config.to_yaml(file_path=yaml_path)

    loaded_config = MesoscopeExperimentConfiguration.from_yaml(file_path=yaml_path)

    assert len(loaded_config.cues) == len(sample_experiment_config.cues)
    assert loaded_config.unity_scene_name == sample_experiment_config.unity_scene_name
    assert loaded_config.cue_offset_cm == sample_experiment_config.cue_offset_cm


# Tests for set_working_directory function


def test_set_working_directory_creates_directory(clean_working_directory, monkeypatch):
    """Verifies that set_working_directory creates the directory if it does not exist.

    This test ensures the function creates missing directories.
    """
    new_dir = clean_working_directory.parent / "new_working_dir"
    assert not new_dir.exists()

    # Patches platformdirs to use our test directory
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(new_dir)

    assert new_dir.exists()


def test_set_working_directory_writes_path_file(clean_working_directory, monkeypatch):
    """Verifies that set_working_directory writes the path to the cache file.

    This test ensures the working directory path is cached correctly.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    path_file = app_dir / "working_directory_path.txt"
    assert path_file.exists()
    assert path_file.read_text() == str(clean_working_directory)


def test_set_working_directory_creates_app_directory(tmp_path, monkeypatch):
    """Verifies that set_working_directory creates the app data directory.

    This test ensures the application data directory is created if missing.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    working_dir = tmp_path / "working"
    working_dir.mkdir()

    assert not app_dir.exists()
    set_working_directory(working_dir)
    assert app_dir.exists()


def test_set_working_directory_overwrites_existing(clean_working_directory, monkeypatch):
    """Verifies that set_working_directory overwrites an existing cached path.

    This test ensures the function can update an existing working directory path.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    # Sets first directory
    first_dir = clean_working_directory / "first"
    first_dir.mkdir()
    set_working_directory(first_dir)

    # Sets a second directory
    second_dir = clean_working_directory / "second"
    second_dir.mkdir()
    set_working_directory(second_dir)

    path_file = app_dir / "working_directory_path.txt"
    assert path_file.read_text() == str(second_dir)


# Tests for get_working_directory function


def test_get_working_directory_returns_cached_path(clean_working_directory, monkeypatch):
    """Verifies that get_working_directory returns the cached directory path.

    This test ensures the function retrieves the correct cached path.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)
    retrieved_dir = get_working_directory()

    assert retrieved_dir == clean_working_directory


def test_get_working_directory_raises_error_if_not_set(tmp_path, monkeypatch):
    """Verifies that get_working_directory raises FileNotFoundError if not configured.

    This test ensures the function raises an appropriate error when unconfigured.
    """
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    with pytest.raises(FileNotFoundError):
        get_working_directory()


def test_get_working_directory_raises_error_if_directory_missing(clean_working_directory, monkeypatch):
    """Verifies that get_working_directory raises error if cached directory does not exist.

    This test ensures the function detects when the cached path no longer exists.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Deletes the working directory
    import shutil

    shutil.rmtree(clean_working_directory)

    with pytest.raises(FileNotFoundError):
        get_working_directory()


# Tests for set_google_credentials_path function


def test_set_google_credentials_path_creates_cache_file(tmp_path, monkeypatch):
    """Verifies that set_google_credentials_path creates the credentials' cache file.

    This test ensures the credentials' path is properly cached.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)

    cache_file = app_dir / "google_credentials_path.txt"
    assert cache_file.exists()
    assert cache_file.read_text() == str(credentials_file.resolve())


def test_set_google_credentials_path_raises_error_file_not_exists(tmp_path, monkeypatch):
    """Verifies that set_google_credentials_path raises error for non-existent files.

    This test ensures the function validates file existence.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    non_existent_file = tmp_path / "missing.json"

    with pytest.raises(FileNotFoundError):
        set_google_credentials_path(non_existent_file)


def test_set_google_credentials_path_raises_error_wrong_extension(tmp_path, monkeypatch):
    """Verifies that set_google_credentials_path raises error for non-JSON files.

    This test ensures the function validates the file extension.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    wrong_extension = tmp_path / "credentials.txt"
    wrong_extension.write_text("not json")

    with pytest.raises(ValueError):
        set_google_credentials_path(wrong_extension)


# Tests for get_google_credentials_path function


def test_get_google_credentials_path_returns_cached_path(tmp_path, monkeypatch):
    """Verifies that get_google_credentials_path returns the cached credentials path.

    This test ensures the function retrieves the correct cached credentials path.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)
    retrieved_path = get_google_credentials_path()

    assert retrieved_path == credentials_file.resolve()


def test_get_google_credentials_path_raises_error_if_not_set(tmp_path, monkeypatch):
    """Verifies that get_google_credentials_path raises an error if not configured.

    This test ensures the function raises an error when the credentials' path is not set.
    """
    app_dir = tmp_path / "empty_app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    with pytest.raises(FileNotFoundError):
        get_google_credentials_path()


def test_get_google_credentials_path_raises_error_if_file_missing(tmp_path, monkeypatch):
    """Verifies that get_google_credentials_path raises an error if the cached file no longer exists.

    This test ensures the function detects when the cached credentials file is missing.
    """
    app_dir = tmp_path / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    credentials_file = tmp_path / "service_account.json"
    credentials_file.write_text('{"type": "service_account"}')

    set_google_credentials_path(credentials_file)

    # Deletes the credentials' file
    credentials_file.unlink()

    with pytest.raises(FileNotFoundError):
        get_google_credentials_path()


# Tests for the create_system_configuration_file function


def test_create_system_configuration_file_mesoscope_vr(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file creates a Mesoscope-VR config file.

    This test ensures the function creates the correct configuration file.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))
    monkeypatch.setattr("builtins.input", lambda _: "")  # Mocks user input

    set_working_directory(clean_working_directory)
    create_system_configuration_file(AcquisitionSystems.MESOSCOPE_VR)

    config_file = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    assert config_file.exists()


def test_create_system_configuration_file_removes_existing(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file removes existing config files.

    This test ensures only one configuration file exists after creation.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))
    monkeypatch.setattr("builtins.input", lambda _: "")

    set_working_directory(clean_working_directory)

    # Creates an existing config file
    existing_config = clean_working_directory / "configuration" / "old_system_configuration.yaml"
    existing_config.write_text("old config")

    create_system_configuration_file(AcquisitionSystems.MESOSCOPE_VR)

    # Verifies old config is removed
    assert not existing_config.exists()

    # Verifies new config exists
    new_config = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    assert new_config.exists()


def test_create_system_configuration_file_invalid_system(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file raises ValueError for invalid systems.

    This test ensures the function rejects unsupported acquisition systems.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    with pytest.raises(ValueError):
        create_system_configuration_file("invalid-system")


def test_create_system_configuration_file_creates_valid_yaml(clean_working_directory, monkeypatch):
    """Verifies that create_system_configuration_file creates valid YAML content.

    This test ensures the created configuration file has a valid YAML structure.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))
    monkeypatch.setattr("builtins.input", lambda _: "")

    set_working_directory(clean_working_directory)
    create_system_configuration_file(AcquisitionSystems.MESOSCOPE_VR)

    config_file = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    content = config_file.read_text()

    # Verifies basic YAML structure
    assert "name:" in content
    assert "filesystem:" in content
    assert "cameras:" in content
    assert "microcontrollers:" in content


# Tests for get_system_configuration_data function


def test_get_system_configuration_data_loads_mesoscope_config(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that get_system_configuration_data loads MesoscopeSystemConfiguration.

    This test ensures the function correctly loads configuration data.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Saves configuration
    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    # Loads configuration
    loaded_config = get_system_configuration_data()

    assert isinstance(loaded_config, MesoscopeSystemConfiguration)
    assert loaded_config.name == sample_mesoscope_config.name


def test_get_system_configuration_data_raises_error_no_config(clean_working_directory, monkeypatch):
    """Verifies that get_system_configuration_data raises an error when no config exists.

    This test ensures the function raises an error when no configuration file is found.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    with pytest.raises(FileNotFoundError):
        get_system_configuration_data()


def test_get_system_configuration_data_raises_error_multiple_configs(clean_working_directory, monkeypatch):
    """Verifies that get_system_configuration_data raises error with multiple configs.

    This test ensures the function rejects directories with multiple configuration files.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates multiple config files
    (clean_working_directory / "config1_configuration.yaml").write_text("config1")
    (clean_working_directory / "config2_configuration.yaml").write_text("config2")

    with pytest.raises(FileNotFoundError):
        get_system_configuration_data()


def test_get_system_configuration_data_raises_error_unsupported_config(clean_working_directory, monkeypatch):
    """Verifies that get_system_configuration_data raises error for unsupported config names.

    This test ensures the function rejects unrecognized configuration file names.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Creates unsupported config file
    (clean_working_directory / "configuration" / "unsupported_system_configuration.yaml").write_text("config")

    with pytest.raises(ValueError):
        get_system_configuration_data()


def test_get_system_configuration_data_path_types(clean_working_directory, sample_mesoscope_config, monkeypatch):
    """Verifies that get_system_configuration_data returns Path objects (not strings).

    This test ensures path fields are properly converted to Path objects after loading.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    loaded_config = get_system_configuration_data()

    # Verifies all path fields are Path objects
    assert isinstance(loaded_config.filesystem.root_directory, Path)
    assert isinstance(loaded_config.filesystem.server_directory, Path)
    assert isinstance(loaded_config.filesystem.nas_directory, Path)


def test_get_system_configuration_data_valve_calibration_tuple(
    clean_working_directory, sample_mesoscope_config, monkeypatch
):
    """Verifies that get_system_configuration_data returns valve_calibration_data as a tuple.

    This test ensures valve calibration data is converted to tuple format after loading.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    config_path = clean_working_directory / "configuration" / "mesoscope_system_configuration.yaml"
    sample_mesoscope_config.save(path=config_path)

    loaded_config = get_system_configuration_data()

    # Verifies valve calibration is a tuple
    assert isinstance(loaded_config.microcontrollers.valve_calibration_data, tuple)
    assert all(isinstance(item, tuple) for item in loaded_config.microcontrollers.valve_calibration_data)


# Tests for ServerConfiguration dataclass


def test_server_configuration_default_initialization():
    """Verifies default initialization of ServerConfiguration.

    This test ensures the class initializes with expected default values.
    """
    config = ServerConfiguration()

    assert config.username == ""
    assert config.password == ""
    assert config.host == ""
    assert config.storage_root == Path()
    assert config.working_root == Path()
    assert config.shared_directory_name == ""


def test_server_configuration_post_init_resolves_paths():
    """Verifies that __post_init__ correctly resolves derived paths.

    This test ensures all paths are properly constructed.
    """
    config = ServerConfiguration(
        username="testuser",
        storage_root=Path("/mnt/storage"),
        working_root=Path("/mnt/work"),
        shared_directory_name="shared",
    )

    assert config.shared_storage_root == Path("/mnt/storage/shared")
    assert config.shared_working_root == Path("/mnt/work/shared")
    assert config.user_data_root == Path("/mnt/storage/testuser")
    assert config.user_working_root == Path("/mnt/work/testuser")


def test_server_configuration_custom_initialization():
    """Verifies custom initialization of ServerConfiguration.

    This test ensures all fields accept custom values.
    """
    config = ServerConfiguration(
        username="myuser",
        password="mypass",
        host="example.com",
        storage_root=Path("/data"),
        working_root=Path("/work"),
        shared_directory_name="lab_data",
    )

    assert config.username == "myuser"
    assert config.password == "mypass"
    assert config.host == "example.com"
    assert config.storage_root == Path("/data")
    assert config.working_root == Path("/work")
    assert config.shared_directory_name == "lab_data"


def test_server_configuration_yaml_round_trip(tmp_path):
    """Verifies that ServerConfiguration survives YAML serialization.

    This test ensures YAML round-trip preserves all data.
    """
    yaml_path = tmp_path / "server_config.yaml"

    original = ServerConfiguration(
        username="testuser",
        password="testpass",
        host="server.example.com",
    )

    original.to_yaml(file_path=yaml_path)
    loaded = ServerConfiguration.from_yaml(file_path=yaml_path)

    assert loaded.username == original.username
    assert loaded.password == original.password
    assert loaded.host == original.host
    assert loaded.shared_storage_root == original.shared_storage_root


# Tests for the create_server_configuration_file function


def test_create_server_configuration_file(clean_working_directory, monkeypatch):
    """Verifies that create_server_configuration_file creates user config.

    This test ensures the user server configuration is created correctly.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    create_server_configuration_file(
        username="testuser",
        password="testpass",
        host="server.example.com",
        storage_root=Path("/srv/storage"),
        working_root=Path("/srv/work"),
        shared_directory_name="shared",
    )

    config_file = clean_working_directory / "configuration" / "server_configuration.yaml"
    assert config_file.exists()

    # Verify content
    loaded = ServerConfiguration.from_yaml(file_path=config_file)
    assert loaded.username == "testuser"
    assert loaded.password == "testpass"


def test_create_server_configuration_file_custom_parameters(clean_working_directory, monkeypatch):
    """Verifies that create_server_configuration_file accepts custom parameters.

    This test ensures custom server parameters are preserved.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    create_server_configuration_file(
        username="myuser",
        password="mypass",
        host="custom.server.com",
        storage_root=Path("/custom/storage"),
        working_root=Path("/custom/work"),
        shared_directory_name="custom_shared",
    )

    config_file = clean_working_directory / "configuration" / "server_configuration.yaml"
    loaded = ServerConfiguration.from_yaml(file_path=config_file)

    assert loaded.host == "custom.server.com"
    assert loaded.storage_root == Path("/custom/storage")
    assert loaded.working_root == Path("/custom/work")
    assert loaded.shared_directory_name == "custom_shared"


# Tests for the get_server_configuration function


def test_get_server_configuration_user(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration loads user config.

    This test ensures user configuration can be retrieved.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Create user config
    create_server_configuration_file(
        username="testuser",
        password="testpass",
        host="server.example.com",
        storage_root=Path("/srv/storage"),
        working_root=Path("/srv/work"),
        shared_directory_name="shared",
    )

    # Load it
    config = get_server_configuration()

    assert config.username == "testuser"
    assert config.password == "testpass"


def test_get_server_configuration_raises_error_if_missing(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration raises error when config missing.

    This test ensures proper error handling for missing configurations.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Don't create any config files

    with pytest.raises(FileNotFoundError) as exc_info:
        get_server_configuration()

    assert "server_configuration.yaml" in str(exc_info.value)


def test_get_server_configuration_raises_error_if_unconfigured(clean_working_directory, monkeypatch):
    """Verifies that get_server_configuration raises an error for placeholder credentials.

    This test ensures unconfigured files are detected.
    """
    app_dir = clean_working_directory.parent / "app_data"
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda appname, appauthor: str(app_dir))

    set_working_directory(clean_working_directory)

    # Create config with empty credentials (unconfigured)
    config_file = clean_working_directory / "configuration" / "server_configuration.yaml"
    ServerConfiguration().to_yaml(file_path=config_file)

    with pytest.raises(ValueError) as exc_info:
        get_server_configuration()

    assert "unconfigured" in str(exc_info.value).lower()
