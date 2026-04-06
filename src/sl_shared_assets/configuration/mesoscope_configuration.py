"""Provides configuration assets specific to the Mesoscope-VR data acquisition system.

This module contains the experiment configuration dataclass for the 2-Photon Random Access Mesoscope (2P-RAM)
with Virtual Reality (VR) environments running in Unity game engine.
"""

from dataclasses import dataclass

from ataraxis_base_utilities import console
from ataraxis_data_structures import YamlConfig

from .vr_configuration import Cue, Segment, VREnvironment  # noqa: TC001 (used in dataclass fields)
from .experiment_configuration import (  # noqa: TC001 (used in dataclass fields)
    GasPuffTrial,
    ExperimentState,
    WaterRewardTrial,
)


# noinspection PyArgumentList
@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    """Defines an experiment session that uses the Mesoscope_VR data acquisition system.

    This is the unified configuration that serves both the data acquisition system (sl-experiment),
    the analysis pipeline (sl-forgery), and the Unity VR environment (sl-unity-tasks).
    """

    # Virtual Reality building block configuration
    cues: list[Cue]
    """Defines the Virtual Reality environment wall cues used in the experiment."""
    segments: list[Segment]
    """Defines the Virtual Reality environment segments (sequences of wall cues) for the Unity corridor system."""

    # Task configuration
    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial]
    """Defines experiment's structure by specifying the types of trials used by the phases (states) of the
    experiment."""
    experiment_states: dict[str, ExperimentState]
    """Defines the experiment's flow by specifying the sequence of experiment and data acquisition system states
    executed during runtime."""

    # VR environment configuration
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
        return {seg.name: seg for seg in self.segments}

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
            duplicate_codes = [c for c in codes if codes.count(c) > 1]
            message = (
                f"Duplicate cue codes found: {set(duplicate_codes)} in the {self.vr_environment} VR environment "
                f"definition. Each cue must use a unique integer code."
            )
            console.error(message=message, error=ValueError)

        # Ensures cue names are unique.
        names = [cue.name for cue in self.cues]
        if len(names) != len(set(names)):
            duplicate_names = [n for n in names if names.count(n) > 1]
            message = (
                f"Duplicate cue names found: {set(duplicate_names)} in the {self.vr_environment} VR environment "
                f"definition. Each cue must use a unique name."
            )
            console.error(message=message, error=ValueError)

        # Ensures segment cue sequences reference valid cues.
        cue_names = {cue.name for cue in self.cues}
        for seg in self.segments:
            for cue_name in seg.cue_sequence:
                if cue_name not in cue_names:
                    message = (
                        f"Segment '{seg.name}' references unknown cue '{cue_name}'. "
                        f"Available cues: {', '.join(sorted(cue_names))}."
                    )
                    console.error(message=message, error=ValueError)

        # Populates the derived trial fields and validates them.
        segment_names = {seg.name for seg in self.segments}
        for trial_name, trial in self.trial_structures.items():
            # Validates segment reference.
            if trial.segment_name not in segment_names:
                message = (
                    f"Trial '{trial_name}' references unknown segment '{trial.segment_name}'. "
                    f"Available segments: {', '.join(sorted(segment_names))}."
                )
                console.error(message=message, error=ValueError)

            # Populates cue_sequence from segment.
            trial.cue_sequence = self._get_segment_cue_codes(trial.segment_name)

            # Populates trial_length_cm from segment.
            trial.trial_length_cm = self._get_segment_length_cm(trial.segment_name)

            # Validates zone positions with populated trial_length_cm.
            trial.validate_zones()
