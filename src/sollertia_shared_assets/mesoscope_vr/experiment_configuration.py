"""Provides the Mesoscope-VR trial classes and the experiment configuration dataclass used by both the acquisition
runtime (sollertia-experiment) and the processing pipeline (sollertia-forgery) for the Mesoscope-VR data acquisition
system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig

from ..configuration import TriggerType, ExperimentState

if TYPE_CHECKING:
    from ..configuration import TaskTemplate

_DEFAULT_STATE_DURATION_S: int = 60
"""Default duration in seconds for each runtime state seeded by ``from_task_template``."""

_DEFAULT_INITIAL_GUIDED_TRIALS: int = 3
"""Default number of guided trials issued at the start of each reinforcing or aversive runtime state."""

_DEFAULT_RECOVERY_FAILED_THRESHOLD: int = 9
"""Default number of consecutive failed trials that triggers recovery guided trial issuance."""

_DEFAULT_RECOVERY_GUIDED_TRIALS: int = 3
"""Default number of guided trials issued when the recovery threshold is crossed."""


@dataclass(frozen=True, slots=True)
class MesoscopeWaterRewardTrial:
    """Defines a Mesoscope-VR trial that delivers a water reward (a reinforcing stimulus) when the animal meets the
    trial's success condition.

    The reward is a configured volume of water accompanied by an auditory tone. The behavioral condition that earns
    the reward is defined by the task, not by this class.
    """

    reward_size_ul: float = 5.0
    """The volume of water, in microliters, to deliver when the animal successfully completes the trial."""
    reward_tone_duration_ms: int = 300
    """The duration, in milliseconds, to sound the auditory tone when delivering the water reward."""


@dataclass(frozen=True, slots=True)
class MesoscopeGasPuffTrial:
    """Defines a Mesoscope-VR trial that delivers a gas puff (an aversive stimulus) when the animal fails the trial's
    avoidance condition.

    The animal avoids the puff by satisfying the task's occupancy condition; failing to do so delivers a puff of the
    configured duration. The behavioral condition is defined by the task, not by this class.
    """

    puff_duration_ms: int = 100
    """The duration, in milliseconds, for which to deliver the gas puff when the animal fails the trial."""


# noinspection PyArgumentList - PyCharm misreports the YamlConfig-derived dataclass __init__ signature.
@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    """Defines an experiment session that uses the Mesoscope-VR data acquisition system.

    Implements the full experiment-configuration contract shared by every Sollertia acquisition system: the
    ``experiment_states`` state machine, the ``trial_structures`` table, the ``unity_scene_name`` of the linear
    infinite corridor task the experiment runs, and the ``from_task_template`` builder. The configuration is consumed
    by the acquisition runtime (sollertia-experiment) and the analysis pipeline (sollertia-forgery).
    """

    trial_structures: dict[str, MesoscopeWaterRewardTrial | MesoscopeGasPuffTrial]
    """The trials the experiment runs, keyed by trial name. This contract field is required by every experiment
    configuration; ``MesoscopeWaterRewardTrial`` and ``MesoscopeGasPuffTrial`` are Mesoscope-VR's trial classes."""
    experiment_states: dict[str, ExperimentState]
    """The experiment state machine, keyed by state name. This contract field is required by every experiment
    configuration."""
    unity_scene_name: str
    """The Unity scene (VR task) the experiment runs in the linear infinite corridor, identifying the paired task
    template by filename stem. This contract field is required by every experiment configuration."""

    @classmethod
    def from_task_template(
        cls,
        template: TaskTemplate,
        unity_scene_name: str,
        state_count: int = 1,
        default_reward_size_ul: float = 5.0,
        default_reward_tone_duration_ms: int = 300,
        default_puff_duration_ms: int = 100,
    ) -> MesoscopeExperimentConfiguration:
        """Builds a Mesoscope-VR experiment configuration from a Unity VR task template.

        Maps each of the template's trial structures to a runtime trial class by its trigger type, pairing
        ``TriggerType.INTERACTION`` with a ``MesoscopeWaterRewardTrial`` and ``TriggerType.OCCUPANCY_DISARM`` with a
        ``MesoscopeGasPuffTrial``. Then seeds ``state_count`` sequentially numbered runtime states ('state_1',
        'state_2', and so on) whose reinforcing or aversive guidance defaults follow the trial types present in the
        template.

        Args:
            template: The task template whose VR trial structures (cues, trial zones) seed the configuration.
            unity_scene_name: The Unity scene name for the experiment. This should match the template YAML file
                name so ``SessionData.create()`` can locate the corresponding VR template during snapshot export.
                Matching is the caller's responsibility and is not validated here.
            state_count: The number of default-valued runtime states to generate.
            default_reward_size_ul: Water reward volume in microliters for interaction-type trials.
            default_reward_tone_duration_ms: Reward tone duration in milliseconds for interaction-type trials.
            default_puff_duration_ms: Gas puff duration in milliseconds for occupancy-disarm trials.

        Returns:
            The experiment configuration populated with the template's trial structures and the requested number
            of default-valued runtime states.
        """
        trial_structures: dict[str, MesoscopeWaterRewardTrial | MesoscopeGasPuffTrial] = {}
        for trial_name, trial_structure in template.trial_structures.items():
            if trial_structure.trigger_type == TriggerType.INTERACTION:
                trial_structures[trial_name] = MesoscopeWaterRewardTrial(
                    reward_size_ul=default_reward_size_ul,
                    reward_tone_duration_ms=default_reward_tone_duration_ms,
                )
            elif trial_structure.trigger_type == TriggerType.OCCUPANCY_DISARM:
                trial_structures[trial_name] = MesoscopeGasPuffTrial(puff_duration_ms=default_puff_duration_ms)
            else:
                message = (
                    f"Unable to build a MesoscopeExperimentConfiguration from the task template. Trial '{trial_name}' "
                    f"uses trigger type '{trial_structure.trigger_type}', which is not mapped to a runtime trial class "
                    f"in MesoscopeExperimentConfiguration.from_task_template. Every TriggerType the template can carry "
                    f"must have a matching branch here."
                )
                console.error(message=message, error=ValueError)

        has_water_reward = any(isinstance(trial, MesoscopeWaterRewardTrial) for trial in trial_structures.values())
        has_gas_puff = any(isinstance(trial, MesoscopeGasPuffTrial) for trial in trial_structures.values())
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
