"""Provides the Mesoscope-VR trial classes and the experiment configuration dataclass used by both the acquisition
runtime (sollertia-experiment) and the processing pipeline (sollertia-forgery) for the Mesoscope-VR data acquisition
system.
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any
from dataclasses import fields, dataclass

from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig

from ..configuration import TriggerType, ExperimentState

if TYPE_CHECKING:
    from pathlib import Path

    from ..configuration import TaskTemplate

_DEFAULT_STATE_DURATION_S: int = 60
"""Default duration in seconds for each runtime state seeded by ``from_task_template``."""

_DEFAULT_INITIAL_GUIDED_TRIALS: int = 3
"""Default number of guided trials issued at the start of each reinforcing or aversive runtime state."""

_DEFAULT_RECOVERY_FAILED_THRESHOLD: int = 9
"""Default number of consecutive failed trials that triggers recovery guided trial issuance."""

_DEFAULT_RECOVERY_GUIDED_TRIALS: int = 3
"""Default number of guided trials issued when the recovery threshold is crossed."""

_DISCRIMINATOR_FIELD: str = "trial_kind"
"""Name of the field each runtime trial class declares to identify which class a stored trial belongs to."""


class TrialKind(StrEnum):
    """Defines the discriminators that identify which Mesoscope-VR runtime trial class a stored trial belongs to.

    Notes:
        Each trial class declares this discriminator with its own member as the default and rejects every other member
        at initialization. Deserialization tries the members of the trial union in order and skips an arm whose
        initialization raises, so the enforced discriminator is what routes a stored trial back to the class that wrote
        it.
    """

    WATER = "water"
    """Indicates a trial that delivers a water reward, which is a MesoscopeWaterRewardTrial."""
    PUFF = "puff"
    """Indicates a trial that delivers a gas puff, which is a MesoscopeGasPuffTrial."""


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
    trial_kind: TrialKind = TrialKind.WATER
    """The discriminator that identifies this trial as a water reward trial when it is read back from a YAML file."""

    def __post_init__(self) -> None:
        """Validates the trial kind discriminator."""
        if self.trial_kind != TrialKind.WATER:
            message = (
                f"Unable to initialize MesoscopeWaterRewardTrial. The trial_kind must be '{TrialKind.WATER.value}', "
                f"but got '{self.trial_kind}'."
            )
            console.error(message=message, error=ValueError)


@dataclass(frozen=True, slots=True)
class MesoscopeGasPuffTrial:
    """Defines a Mesoscope-VR trial that delivers a gas puff (an aversive stimulus) when the animal fails the trial's
    avoidance condition.

    The animal avoids the puff by satisfying the task's occupancy condition. Failing to do so delivers a puff of the
    configured duration. The behavioral condition is defined by the task, not by this class.
    """

    puff_duration_ms: int = 100
    """The duration, in milliseconds, for which to deliver the gas puff when the animal fails the trial."""
    trial_kind: TrialKind = TrialKind.PUFF
    """The discriminator that identifies this trial as a gas puff trial when it is read back from a YAML file."""

    def __post_init__(self) -> None:
        """Validates the trial kind discriminator."""
        if self.trial_kind != TrialKind.PUFF:
            message = (
                f"Unable to initialize MesoscopeGasPuffTrial. The trial_kind must be '{TrialKind.PUFF.value}', but "
                f"got '{self.trial_kind}'."
            )
            console.error(message=message, error=ValueError)


@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    """Defines an experiment session that uses the Mesoscope-VR data acquisition system.

    Implements the full experiment-configuration contract shared by every Sollertia acquisition system: the
    ``experiment_states`` state machine, the ``trial_structures`` table, the ``unity_scene_name`` of the linear
    infinite corridor task the experiment runs, and the ``from_task_template`` builder.
    """

    trial_structures: dict[str, MesoscopeWaterRewardTrial | MesoscopeGasPuffTrial]
    """The trials the experiment runs, keyed by trial name. This contract field is required by every experiment
    configuration. ``MesoscopeWaterRewardTrial`` and ``MesoscopeGasPuffTrial`` are Mesoscope-VR's trial classes."""
    experiment_states: dict[str, ExperimentState]
    """The experiment state machine, keyed by state name. This contract field is required by every experiment
    configuration."""
    unity_scene_name: str
    """The Unity scene (VR task) the experiment runs in the linear infinite corridor, identifying the paired task
    template by filename stem. This contract field is required by every experiment configuration."""

    def __post_init__(self) -> None:
        """Verifies that every stored trial resolved to one of the runtime trial classes.

        Notes:
            Deserialization matches a stored trial against each member of the trial union in turn and yields the
            unconverted mapping when no member accepts it, because the loader runs with per-field type checking
            disabled. An unconverted trial reaches the acquisition runtime as a mapping and fails there instead of
            here, so it is rejected at load.

        Raises:
            ValueError: If any stored trial did not resolve to a runtime trial class.
        """
        unresolved = sorted(
            trial_name
            for trial_name, trial in self.trial_structures.items()
            if not isinstance(trial, (MesoscopeWaterRewardTrial, MesoscopeGasPuffTrial))
        )
        if unresolved:
            message = (
                f"Unable to initialize MesoscopeExperimentConfiguration. Every trial must resolve to a Mesoscope-VR "
                f"runtime trial class, but the following did not: {', '.join(unresolved)}. Check the fields and the "
                f"'{_DISCRIMINATOR_FIELD}' value each of them declares."
            )
            console.error(message=message, error=ValueError)

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
            state_count: The number of default-valued runtime states to generate. Must be at least one, since an
                experiment with no runtime states cannot be executed.
            default_reward_size_ul: Water reward volume in microliters for interaction-type trials.
            default_reward_tone_duration_ms: Reward tone duration in milliseconds for interaction-type trials.
            default_puff_duration_ms: Gas puff duration in milliseconds for occupancy-disarm trials.

        Returns:
            The experiment configuration populated with the template's trial structures and the requested number
            of default-valued runtime states.

        Raises:
            ValueError: If state_count is less than one, or if any of the template's trial structures uses a
                TriggerType that is not mapped to a Mesoscope-VR runtime trial class. Only TriggerType.INTERACTION and
                TriggerType.OCCUPANCY_DISARM are mapped to runtime trial classes.
        """
        if state_count < 1:
            message = (
                f"Unable to build a MesoscopeExperimentConfiguration from the task template. The state_count must be "
                f"at least 1, but got {state_count}."
            )
            console.error(message=message, error=ValueError)

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
                    f"in MesoscopeExperimentConfiguration.from_task_template. Mesoscope-VR maps the INTERACTION and "
                    f"OCCUPANCY_DISARM trigger types. Use one of them in the template, or add a branch here if "
                    f"Mesoscope-VR should support this trigger type."
                )
                console.error(message=message, error=ValueError)

        has_water_reward = any(isinstance(trial, MesoscopeWaterRewardTrial) for trial in trial_structures.values())
        has_gas_puff = any(isinstance(trial, MesoscopeGasPuffTrial) for trial in trial_structures.values())
        experiment_states: dict[str, ExperimentState] = {
            f"state_{state_index + 1}": ExperimentState(
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
            for state_index in range(state_count)
        }

        return cls(
            trial_structures=trial_structures,
            experiment_states=experiment_states,
            unity_scene_name=unity_scene_name,
        )

    @classmethod
    def restore_excluded_fields(cls, data: dict[Any, Any], file_path: Path) -> dict[Any, Any]:  # noqa: ARG003
        """Returns the loaded mapping with a trial kind discriminator supplied for every trial that omits one.

        Notes:
            An omitted field takes its class default, so a trial carrying no discriminator would resolve to the water
            reward class whatever fields it declares. Resolving the discriminator from those fields instead routes the
            trial to the class that accommodates them, which lets a configuration authored without the discriminator
            load as written.

        Args:
            data: The mapping loaded from the configuration file.
            file_path: The path the mapping was loaded from.

        Returns:
            The loaded mapping whose every stored trial carries a trial kind discriminator.

        Raises:
            ValueError: If a stored trial declares an unrecognized discriminator, or declares fields that identify a
                different runtime trial class than its discriminator names, or that identify two classes at once.
        """
        trial_structures = data.get("trial_structures")
        if not isinstance(trial_structures, dict):
            return data

        return {
            **data,
            "trial_structures": {
                trial_name: _restore_trial_kind(trial_name=trial_name, trial=trial)
                for trial_name, trial in trial_structures.items()
            },
        }


_TRIAL_CLASSES: tuple[tuple[TrialKind, type], ...] = (
    (TrialKind.WATER, MesoscopeWaterRewardTrial),
    (TrialKind.PUFF, MesoscopeGasPuffTrial),
)
"""Pairs each trial kind with the runtime trial class that declares it as its discriminator default. The pairs are
declared below the classes they name, since a constant cannot reference a class defined after it."""


def _restore_trial_kind(trial_name: str, trial: Any) -> Any:
    """Returns the stored trial with its trial kind discriminator supplied and checked against the fields it declares.

    Notes:
        A trial that omits the ``trial_kind`` field takes its class default, which would route every such trial to the
        water reward class. The fields unique to one runtime trial class identify the class instead. A trial declaring
        none of them takes the water reward kind. Fields belonging to neither class are ignored, matching how the loader
        treats a field it does not recognize.

    Args:
        trial_name: The name the trial is stored under.
        trial: The stored trial, which is a mapping for every trial a configuration file declares.

    Returns:
        The stored trial unchanged when it already carries a discriminator consistent with its fields, otherwise a
        copy carrying the resolved discriminator.

    Raises:
        ValueError: If the trial declares an unrecognized discriminator, or declares fields unique to a different
            runtime trial class than its discriminator names, or declares fields unique to two classes at once.
    """
    if not isinstance(trial, dict):
        return trial

    declared_fields = frozenset(trial)
    identified = {kind for kind, unique_fields in _unique_trial_fields().items() if declared_fields & unique_fields}
    if len(identified) > 1:
        message = (
            f"Unable to resolve the trial kind for the '{trial_name}' trial. The trial declares fields unique to more "
            f"than one Mesoscope-VR runtime trial class, identifying "
            f"{', '.join(sorted(kind.value for kind in identified))}. Remove the fields that do not belong to the "
            f"trial's own class."
        )
        console.error(message=message, error=ValueError)

    if _DISCRIMINATOR_FIELD not in trial:
        resolved = next(iter(identified)) if identified else TrialKind.WATER
        return {**trial, _DISCRIMINATOR_FIELD: resolved.value}

    declared_kind = trial[_DISCRIMINATOR_FIELD]
    valid_kinds = ", ".join(kind.value for kind, _ in _TRIAL_CLASSES)
    if all(declared_kind != kind.value for kind, _ in _TRIAL_CLASSES):
        message = (
            f"Unable to resolve the trial kind for the '{trial_name}' trial. The '{_DISCRIMINATOR_FIELD}' field must "
            f"be one of: {valid_kinds}, but got '{declared_kind}'."
        )
        console.error(message=message, error=ValueError)

    if identified and TrialKind(declared_kind) not in identified:
        message = (
            f"Unable to resolve the trial kind for the '{trial_name}' trial. The '{_DISCRIMINATOR_FIELD}' field names "
            f"'{declared_kind}', but the trial declares fields unique to "
            f"{', '.join(sorted(kind.value for kind in identified))}. Correct whichever of the two is wrong, since "
            f"the discriminator alone decides the class and the fields it disagrees with would be dropped."
        )
        console.error(message=message, error=ValueError)

    return trial


def _unique_trial_fields() -> dict[TrialKind, frozenset[str]]:
    """Returns the fields each runtime trial class declares that no sibling trial class declares.

    Returns:
        The mapping from each trial kind to the field names unique to its runtime trial class, excluding the
        discriminator itself.
    """
    declared = {
        kind: frozenset(field_definition.name for field_definition in fields(trial_class)) - {_DISCRIMINATOR_FIELD}
        for kind, trial_class in _TRIAL_CLASSES
    }
    return {
        kind: field_names.difference(*(other for sibling, other in declared.items() if sibling != kind))
        for kind, field_names in declared.items()
    }
