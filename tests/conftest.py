"""Provides shared pytest fixtures for the sollertia-shared-assets test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import platformdirs

from sollertia_shared_assets.configuration import (
    Cue,
    Segment,
    VREnvironment,
    ExperimentState,
    WaterRewardTrial,
    MesoscopeExperimentConfiguration,
)

if TYPE_CHECKING:
    from pathlib import Path


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

    # Defines cues that sum to 175 cm for Segment_abc (50 + 75 + 50).
    cues = [
        Cue(name="A", code=1, length_cm=50.0, texture="Cue 016 - 4x1.png"),
        Cue(name="B", code=2, length_cm=75.0, texture="Cue 001 - 4x1.png"),
        Cue(name="C", code=3, length_cm=50.0, texture="Cue 008 - 2x1 repeat.png"),
    ]

    segments = [
        Segment(name="Segment_abc", cue_sequence=["A", "B", "C"], transition_probabilities=None),
    ]

    # References the segment; cue_sequence and trial_length_cm are derived fields.
    trial = WaterRewardTrial(
        segment_name="Segment_abc",
        stimulus_trigger_zone_start_cm=150.0,
        stimulus_trigger_zone_end_cm=175.0,
        stimulus_location_cm=160.0,
        show_stimulus_collision_boundary=False,
    )

    return MesoscopeExperimentConfiguration(
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


@pytest.fixture
def clean_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Sets up a clean temporary working directory for testing."""
    # Redirects platformdirs to an isolated temporary application-data directory.
    app_dir = tmp_path / "app_data"
    app_dir.mkdir()
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    working_dir = tmp_path / "working_directory"
    working_dir.mkdir()

    return working_dir
