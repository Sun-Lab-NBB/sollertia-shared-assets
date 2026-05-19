"""Provides shared pytest fixtures for the sollertia-shared-assets test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import platformdirs

from sollertia_shared_assets.configuration import (
    ExperimentState,
    WaterRewardTrial,
    MesoscopeExperimentConfiguration,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def sample_experiment_config() -> MesoscopeExperimentConfiguration:
    """Provides a sample MesoscopeExperimentConfiguration for testing."""
    state = ExperimentState(
        experiment_state_code=1,
        system_state_code=0,
        state_duration_s=600.0,
        supports_trials=True,
        reinforcing_initial_guided_trials=10,
        reinforcing_recovery_failed_threshold=5,
        reinforcing_recovery_guided_trials=3,
    )

    trial = WaterRewardTrial(reward_size_ul=5.0, reward_tone_duration_ms=300)

    return MesoscopeExperimentConfiguration(
        trial_structures={"trial1": trial},
        experiment_states={"state1": state},
        unity_scene_name="TestScene",
    )


@pytest.fixture
def clean_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provides an isolated temporary working directory for testing."""
    # Isolates platformdirs from the host machine to avoid polluting real user state.
    app_dir = tmp_path / "app_data"
    app_dir.mkdir()
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda **_kwargs: str(app_dir))

    working_dir = tmp_path / "working_directory"
    working_dir.mkdir()

    return working_dir
