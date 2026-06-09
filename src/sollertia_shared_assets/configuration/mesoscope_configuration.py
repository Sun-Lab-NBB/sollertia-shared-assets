"""Provides the experiment configuration dataclass used by both the acquisition runtime (sollertia-experiment) and the
processing pipeline (sollertia-forgery) for the Mesoscope-VR data acquisition system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig

from .vr_configuration import TriggerType
from .experiment_configuration import GasPuffTrial, ExperimentState, WaterRewardTrial

if TYPE_CHECKING:
    from .vr_configuration import TaskTemplate

_DEFAULT_STATE_DURATION_S: int = 60
"""Default duration in seconds for each runtime state seeded by ``from_task_template``."""

_DEFAULT_INITIAL_GUIDED_TRIALS: int = 3
"""Default number of guided trials issued at the start of each reinforcing or aversive runtime state."""

_DEFAULT_RECOVERY_FAILED_THRESHOLD: int = 9
"""Default number of consecutive failed trials that triggers recovery guided trial issuance."""

_DEFAULT_RECOVERY_GUIDED_TRIALS: int = 3
"""Default number of guided trials issued when the recovery threshold is crossed."""


# noinspection PyArgumentList - PyCharm misreports the YamlConfig-derived dataclass __init__ signature.
@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    """Defines an experiment session that uses the Mesoscope-VR data acquisition system.

    Implements the experiment-configuration contract — the ``experiment_states`` state machine and the
    ``trial_structures`` table — and adds ``unity_scene_name`` because Mesoscope-VR runs a Unity VR task. The
    configuration is consumed by the acquisition runtime (sollertia-experiment) and the analysis pipeline
    (sollertia-forgery).
    """

    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial]
    """The trials the experiment runs, keyed by trial name. This contract field is required by every experiment
    configuration; ``WaterRewardTrial`` and ``GasPuffTrial`` are Mesoscope-VR's trial classes."""
    experiment_states: dict[str, ExperimentState]
    """The experiment state machine, keyed by state name. This contract field is required by every experiment
    configuration."""
    unity_scene_name: str
    """The Unity scene (VR task) the experiment runs, identifying the paired task template by filename stem.
    Mesoscope-VR carries this field because it runs a Unity VR task."""

    @classmethod
    def from_task_template(
        cls,
        template: TaskTemplate,
        unity_scene_name: str,
        state_count: int = 1,
        default_reward_size_ul: float = 5.0,
        default_reward_tone_duration_ms: int = 300,
        default_puff_duration_ms: int = 100,
        default_occupancy_duration_ms: int = 1000,
    ) -> MesoscopeExperimentConfiguration:
        """Builds a Mesoscope-VR experiment configuration from a Unity VR task template.

        Maps each of the template's trial structures to a runtime trial class by its trigger type, pairing
        ``TriggerType.LICK`` with a ``WaterRewardTrial`` and ``TriggerType.OCCUPANCY`` with a ``GasPuffTrial``.
        Then seeds ``state_count`` sequentially numbered runtime states ('state_1', 'state_2', and so on) whose
        reinforcing or aversive guidance defaults follow the trial types present in the template.

        Args:
            template: The task template whose VR trial structures (cues, trial zones) seed the configuration.
            unity_scene_name: The Unity scene name for the experiment. This should match the template YAML file
                name so ``SessionData.create()`` can locate the corresponding VR template during snapshot export.
                Matching is the caller's responsibility and is not validated here.
            state_count: The number of default-valued runtime states to generate.
            default_reward_size_ul: Water reward volume in microliters for lick-type trials.
            default_reward_tone_duration_ms: Reward tone duration in milliseconds for lick-type trials.
            default_puff_duration_ms: Gas puff duration in milliseconds for occupancy-type trials.
            default_occupancy_duration_ms: Occupancy threshold duration in milliseconds for occupancy-type trials.

        Returns:
            The experiment configuration populated with the template's trial structures and the requested number
            of default-valued runtime states.
        """
        trial_structures: dict[str, WaterRewardTrial | GasPuffTrial] = {}
        for trial_name, trial_structure in template.trial_structures.items():
            if trial_structure.trigger_type == TriggerType.LICK:
                trial_structures[trial_name] = WaterRewardTrial(
                    reward_size_ul=default_reward_size_ul,
                    reward_tone_duration_ms=default_reward_tone_duration_ms,
                )
            elif trial_structure.trigger_type == TriggerType.OCCUPANCY:
                trial_structures[trial_name] = GasPuffTrial(
                    puff_duration_ms=default_puff_duration_ms,
                    occupancy_duration_ms=default_occupancy_duration_ms,
                )
            else:
                message = (
                    f"Unable to build a MesoscopeExperimentConfiguration from the task template. Trial '{trial_name}' "
                    f"uses trigger type '{trial_structure.trigger_type}', which is not mapped to a runtime trial class "
                    f"in MesoscopeExperimentConfiguration.from_task_template. Every TriggerType the template can carry "
                    f"must have a matching branch here."
                )
                console.error(message=message, error=ValueError)

        has_water_reward = any(isinstance(trial, WaterRewardTrial) for trial in trial_structures.values())
        has_gas_puff = any(isinstance(trial, GasPuffTrial) for trial in trial_structures.values())
        experiment_states: dict[str, ExperimentState] = {}
        for state_index in range(state_count):
            experiment_states[f"state_{state_index + 1}"] = ExperimentState(
                experiment_state_code=state_index + 1,
                system_state_code=0,
                state_duration_s=_DEFAULT_STATE_DURATION_S,
                supports_trials=True,
                reinforcing_initial_guided_trials=_DEFAULT_INITIAL_GUIDED_TRIALS if has_water_reward else 0,
                reinforcing_recovery_failed_threshold=_DEFAULT_RECOVERY_FAILED_THRESHOLD if has_water_reward else 0,
                reinforcing_recovery_guided_trials=_DEFAULT_RECOVERY_GUIDED_TRIALS if has_water_reward else 0,
                aversive_initial_guided_trials=_DEFAULT_INITIAL_GUIDED_TRIALS if has_gas_puff else 0,
                aversive_recovery_failed_threshold=_DEFAULT_RECOVERY_FAILED_THRESHOLD if has_gas_puff else 0,
                aversive_recovery_guided_trials=_DEFAULT_RECOVERY_GUIDED_TRIALS if has_gas_puff else 0,
            )

        return cls(
            trial_structures=trial_structures,
            experiment_states=experiment_states,
            unity_scene_name=unity_scene_name,
        )
