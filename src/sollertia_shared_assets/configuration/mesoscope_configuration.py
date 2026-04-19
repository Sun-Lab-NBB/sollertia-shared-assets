"""Provides the experiment configuration dataclass used by both the acquisition runtime (sollertia-experiment) and the
processing pipeline (sollertia-forgery) for the Mesoscope-VR data acquisition system.
"""

from __future__ import annotations

from dataclasses import dataclass

from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig

from .vr_configuration import Cue, Segment, VREnvironment  # noqa: TC001 - YamlConfig resolves these at runtime.
from .experiment_configuration import (  # noqa: TC001 - YamlConfig resolves these at runtime.
    GasPuffTrial,
    ExperimentState,
    WaterRewardTrial,
)


# noinspection PyArgumentList
@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    """Defines an experiment session that uses the Mesoscope-VR data acquisition system.

    Provides the unified configuration consumed by the data acquisition system (sollertia-experiment), the
    analysis pipeline (sollertia-forgery), and the Unity VR environment (sollertia-unity-tasks).
    """

    # Configures Virtual Reality building blocks.
    cues: list[Cue]
    """Defines the Virtual Reality environment wall cues used in the experiment."""
    segments: list[Segment]
    """Defines the Virtual Reality environment segments (sequences of wall cues) for the Unity corridor system."""

    # Configures task structure.
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial]
    """Defines experiment's structure by specifying the types of trials used by the phases (states) of the
    experiment."""
    experiment_states: dict[str, ExperimentState]
    """Defines the experiment's flow by specifying the sequence of experiment and data acquisition system states
    executed during runtime."""

    # Configures the Virtual Reality environment.
    vr_environment: VREnvironment
    """Defines the Virtual Reality corridor used during the experiment."""
    unity_scene_name: str
    """The name of the Virtual Reality task (Unity Scene) used during the experiment."""
    cue_offset_cm: float = 0.0
    """Specifies the offset of the animal's starting position relative to the Virtual Reality (VR) environment's cue
    sequence origin, in centimeters."""

    @property
    def _cue_by_name(self) -> dict[str, Cue]:
        """Returns the mapping of cue names to their Cue class instances for all VR cues used in the experiment."""
        return {cue.name: cue for cue in self.cues}

    @property
    def _cue_name_to_code(self) -> dict[str, int]:
        """Returns the mapping of cue names to their unique identifier codes for all VR cues used in the experiment."""
        return {cue.name: cue.code for cue in self.cues}

    @property
    def _segment_by_name(self) -> dict[str, Segment]:
        """Returns the mapping of segment names to their Segment class instances for all VR segments used in the
        experiment.
        """
        return {segment.name: segment for segment in self.segments}

    def _get_segment_length_cm(self, segment_name: str) -> float:
        """Returns the total length of the VR segment in centimeters."""
        segment = self._segment_by_name[segment_name]
        cue_map = self._cue_by_name
        return sum(cue_map[cue_name].length_cm for cue_name in segment.cue_sequence)

    def _get_segment_cue_codes(self, segment_name: str) -> list[int]:
        """Returns the sequence of cue codes for the specified segment's cue sequence."""
        segment = self._segment_by_name[segment_name]
        return [self._cue_name_to_code[name] for name in segment.cue_sequence]

    def __post_init__(self) -> None:
        """Validates experiment configuration and populates derived trial fields."""
        # Ensures cue codes are unique.
        codes = [cue.code for cue in self.cues]
        if len(codes) != len(set(codes)):
            duplicate_codes = {code for code in codes if codes.count(code) > 1}
            message = (
                f"Unable to initialize MesoscopeExperimentConfiguration. The cue codes must each be unique, but "
                f"got duplicate codes {duplicate_codes}."
            )
            console.error(message=message, error=ValueError)

        # Ensures cue names are unique.
        names = [cue.name for cue in self.cues]
        if len(names) != len(set(names)):
            duplicate_names = {name for name in names if names.count(name) > 1}
            message = (
                f"Unable to initialize MesoscopeExperimentConfiguration. The cue names must each be unique, but "
                f"got duplicate names {duplicate_names}."
            )
            console.error(message=message, error=ValueError)

        # Ensures segment cue sequences reference valid cues.
        cue_names = {cue.name for cue in self.cues}
        for segment in self.segments:
            for cue_name in segment.cue_sequence:
                if cue_name not in cue_names:
                    message = (
                        f"Unable to initialize MesoscopeExperimentConfiguration. Segment '{segment.name}' "
                        f"references unknown cue '{cue_name}'. Available cues: {', '.join(sorted(cue_names))}."
                    )
                    console.error(message=message, error=ValueError)

        # Populates the derived trial fields and validates them.
        segment_names = {segment.name for segment in self.segments}
        for trial_name, trial in self.trial_structures.items():
            # Validates segment reference.
            if trial.segment_name not in segment_names:
                message = (
                    f"Unable to initialize MesoscopeExperimentConfiguration. Trial '{trial_name}' references "
                    f"unknown segment '{trial.segment_name}'. Available segments: "
                    f"{', '.join(sorted(segment_names))}."
                )
                console.error(message=message, error=ValueError)

            # Populates cue_sequence from segment.
            trial.cue_sequence = self._get_segment_cue_codes(segment_name=trial.segment_name)

            # Populates trial_length_cm from segment.
            trial.trial_length_cm = self._get_segment_length_cm(segment_name=trial.segment_name)

            # Validates zone positions with populated trial_length_cm.
            trial.validate_zones()
