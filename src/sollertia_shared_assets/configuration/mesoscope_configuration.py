"""Provides the experiment configuration dataclass used by both the acquisition runtime (sollertia-experiment) and the
processing pipeline (sollertia-forgery) for the Mesoscope-VR data acquisition system.
"""

from __future__ import annotations

from dataclasses import dataclass

from ataraxis_data_structures import YamlConfig

from .experiment_configuration import (  # noqa: TC001 - YamlConfig resolves these at runtime.
    GasPuffTrial,
    ExperimentState,
    WaterRewardTrial,
)


# noinspection PyArgumentList
@dataclass
class MesoscopeExperimentConfiguration(YamlConfig):
    """Defines an experiment session that uses the Mesoscope-VR data acquisition system.

    Provides the unified configuration consumed by the data acquisition system (sollertia-experiment) and the
    analysis pipeline (sollertia-forgery).
    """

    trial_structures: dict[str, WaterRewardTrial | GasPuffTrial]
    """Defines experiment's structure by specifying the types of trials used by the phases (states) of the
    experiment."""
    experiment_states: dict[str, ExperimentState]
    """Defines the experiment's flow by specifying the sequence of experiment and data acquisition system states
    executed during runtime."""
    unity_scene_name: str
    """The name of the Virtual Reality task (Unity Scene) used during the experiment."""
