"""Provides assets for storing runtime data acquired by data acquisition systems."""

from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig


@dataclass
class MesoscopeHardwareState(YamlConfig):  # pragma: no cover
    """Stores configuration parameters (states) of the Mesoscope-VR system hardware modules used during training or
    experiment runtimes.

    Notes:
        All hardware parameters are stored using the appropriate datatypes and rounding methods that ensure
        their complete equivalence to the values used by the data acquisition system during runtime.

        Any field set to 'None' indicates that the corresponding hardware module was not used by the executed data
        acquisition runtime.
    """

    cm_per_pulse: float | None = None
    """The conversion factor used to translate encoder pulses into centimeters."""
    maximum_brake_strength: float | None = None
    """The braking torque, in Newton centimeters, applied by the brake to the edge of the running wheel when it is
    maximally engaged."""
    minimum_brake_strength: float | None = None
    """The braking torque, in Newton centimeters, applied by the brake to the edge of the running wheel when it is
    completely disengaged."""
    lick_threshold: int | None = None
    """Determines the threshold, in 12-bit Analog to Digital Converter (ADC) units reported by the lick sensor, for
    considering the reported signal a lick."""
    valve_scale_coefficient: float | None = None
    """The scale coefficient of the power law equation that describes the relationship between the time the valve is
    kept open and the dispensed water volume."""
    valve_nonlinearity_exponent: float | None = None
    """The nonlinearity exponent of the power law equation that describes the relationship between the time the valve
    is kept open and the dispensed water volume."""
    torque_per_adc_unit: float | None = None
    """The conversion factor used to translate torque values reported by the sensor as 12-bit Analog to Digital
    Converter (ADC) units into Newton centimeters (N·cm)."""
    screens_initially_on: bool | None = None
    """Stores the initial state of the Virtual Reality screens at the beginning of the session's runtime."""
    recorded_mesoscope_ttl: bool | None = None
    """Tracks whether the session recorded brain activity data with the mesoscope."""
    delivered_gas_puffs: bool | None = None
    """Tracks whether the session delivered any gas puffs to the animal."""
    system_state_codes: dict[str, int] | None = None
    """Maps integer state-codes used by the Mesoscope-VR system to communicate its states (system states) to
    human-readable state names."""


@dataclass
class LickTrainingDescriptor(YamlConfig):  # pragma: no cover
    """Stores the task and outcome information specific to lick training sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    minimum_reward_delay_s: int = 6
    """The minimum delay, in seconds, that can separate the delivery of two consecutive water rewards."""
    maximum_reward_delay_s: int = 18
    """The maximum delay, in seconds, that can separate the delivery of two consecutive water rewards."""
    maximum_water_volume_ml: float = 1.0
    """The maximum volume of water the system is allowed to dispense during training."""
    maximum_training_time_min: int = 20
    """The maximum time, in minutes, the system is allowed to run the training."""
    maximum_unconsumed_rewards: int = 1
    """The maximum number of consecutive rewards that can be delivered without the animal consuming them. If
    the animal receives this many rewards without licking (consuming) them, reward delivery is paused until the animal
    consumes the delivered rewards."""
    water_reward_size_ul: float = 5.0
    """The volume of water, in microliters, dispensed to the animal when it achieves the required running speed and
    duration thresholds."""
    reward_tone_duration_ms: int = 300
    """The duration, in milliseconds, of the auditory tone played to the animal when it receives water rewards."""
    dispensed_water_volume_ml: float = 0.0
    """The total water volume, in milliliters, dispensed during runtime. This excludes the water volume
    dispensed during the paused (idle) state."""
    pause_dispensed_water_volume_ml: float = 0.0
    """The total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    preferred_session_water_volume_ml: float = 0.0
    """The volume of water, in milliliters, the animal should be receiving during the session runtime if its
    performance matches experimenter-specified threshold."""
    incomplete: bool = True
    """Tracks whether the session's data is complete and eligible for unsupervised data processing."""
    experimenter_notes: str = "Replace this with your notes."
    """Stores the experimenter's notes made during runtime."""


@dataclass
class RunTrainingDescriptor(YamlConfig):  # pragma: no cover
    """Stores the task and outcome information specific to run training sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    final_run_speed_threshold_cm_s: float = 1.5
    """The running speed threshold, in centimeters per second, at the end of training."""
    final_run_duration_threshold_s: float = 1.5
    """The running duration threshold, in seconds, at the end of training."""
    initial_run_speed_threshold_cm_s: float = 0.8
    """The initial running speed threshold, in centimeters per second."""
    initial_run_duration_threshold_s: float = 1.5
    """The initial running duration threshold, in seconds."""
    increase_threshold_ml: float = 0.1
    """The threshold volume of water delivered to the animal, in milliliters, that triggers the increase in the running
    speed and duration thresholds."""
    run_speed_increase_step_cm_s: float = 0.05
    """The value, in centimeters per second, used by the system to increment the running speed threshold each
    time the animal receives 'increase_threshold' volume of water."""
    run_duration_increase_step_s: float = 0.1
    """The value, in seconds, used by the system to increment the duration threshold each time the animal
    receives 'increase_threshold' volume of water."""
    maximum_water_volume_ml: float = 1.0
    """The maximum volume of water the system is allowed to dispense during training."""
    maximum_training_time_min: int = 40
    """The maximum time, in minutes, the system is allowed to run the training."""
    maximum_unconsumed_rewards: int = 1
    """The maximum number of consecutive rewards that can be delivered without the animal consuming them. If
    the animal receives this many rewards without licking (consuming) them, reward delivery is paused until the animal
    consumes the delivered rewards."""
    maximum_idle_time_s: float = 0.3
    """The maximum time, in seconds, the animal can dip below the running speed threshold to still receive the
    reward. This allows animals that 'run' by taking a series of large steps, briefly dipping below speed threshold at
    the end of each step, to still get water rewards."""
    water_reward_size_ul: float = 5.0
    """The volume of water, in microliters, dispensed to the animal when it achieves the required running speed and
    duration thresholds."""
    reward_tone_duration_ms: int = 300
    """The duration, in milliseconds, of the auditory tone played to the animal when it receives water rewards."""
    dispensed_water_volume_ml: float = 0.0
    """The total water volume, in milliliters, dispensed during runtime. This excludes the water volume
    dispensed during the paused (idle) state."""
    pause_dispensed_water_volume_ml: float = 0.0
    """The total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    preferred_session_water_volume_ml: float = 0.0
    """The volume of water, in milliliters, the animal should be receiving during the session runtime if its
    performance matches experimenter-specified threshold."""
    incomplete: bool = True
    """Tracks whether the session's data is complete and eligible for unsupervised data processing."""
    experimenter_notes: str = "Replace this with your notes."
    """Stores the experimenter's notes made during runtime."""


@dataclass
class MesoscopeExperimentDescriptor(YamlConfig):  # pragma: no cover
    """Stores the task and outcome information specific to experiment sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    mouse_weight_g: float
    """The weight of the animal, in grams, at the beginning of the session."""
    maximum_unconsumed_rewards: int = 1
    """The maximum number of consecutive rewards that can be delivered without the animal consuming them. If
    the animal receives this many rewards without licking (consuming) them, reward delivery is paused until the animal
    consumes the delivered rewards."""
    dispensed_water_volume_ml: float = 0.0
    """The total water volume, in milliliters, dispensed during runtime. This excludes the water volume
    dispensed during the paused (idle) state."""
    pause_dispensed_water_volume_ml: float = 0.0
    """The total water volume, in milliliters, dispensed during the paused (idle) state."""
    experimenter_given_water_volume_ml: float = 0.0
    """The additional volume of water, in milliliters, administered by the experimenter to the animal after the session.
    """
    preferred_session_water_volume_ml: float = 0.0
    """The volume of water, in milliliters, the animal should be receiving during the session runtime if its
    performance matches experimenter-specified threshold."""
    incomplete: bool = True
    """Tracks whether the session's data is complete and eligible for unsupervised data processing."""
    experimenter_notes: str = "Replace this with your notes."
    """Stores the experimenter's notes made during runtime."""


@dataclass
class WindowCheckingDescriptor(YamlConfig):  # pragma: no cover
    """Stores the outcome information specific to window checking sessions that use the Mesoscope-VR system."""

    experimenter: str
    """The ID of the experimenter running the session."""
    surgery_quality: int = 0
    """The quality of the cranial window and surgical intervention on a scale from 0 (non-usable) to
    3 (high-tier publication grade) inclusive."""
    incomplete: bool = True
    """Tracks whether the session's data is complete and eligible for unsupervised data processing."""
    experimenter_notes: str = "Replace this with your notes."
    """Stores the experimenter's notes made during runtime."""
