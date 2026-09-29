"""Shared test fixtures and configuration."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd


@pytest.fixture(scope="session")
def temp_data_dir():
    """Temporary directory for test data artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_games_dataframe():
    """Sample games dataframe for testing."""
    return pd.DataFrame({
        "date": ["2026-09-29", "2026-09-30"],
        "game_pk": [1, 2],
        "home_team": ["Boston Red Sox", "New York Yankees"],
        "away_team": ["New York Yankees", "Boston Red Sox"],
        "home_abbr": ["BOS", "NYY"],
        "away_abbr": ["NYY", "BOS"],
        "home_score": [5, 3],
        "away_score": [2, 4],
        "home_win": [1, 0],
    })


@pytest.fixture
def sample_features_dataframe():
    """Sample features dataframe for model input."""
    return pd.DataFrame({
        "date": ["2026-09-29", "2026-09-30"],
        "game_pk": [1, 2],
        "home_team": ["Boston Red Sox", "New York Yankees"],
        "away_team": ["New York Yankees", "Boston Red Sox"],
        "home_abbr": ["BOS", "NYY"],
        "away_abbr": ["NYY", "BOS"],
        "diff_pct": [0.05, -0.03],
        "delta_FIP": [0.5, -0.2],
        "delta_WAR": [1.5, 0.8],
        "delta_K9": [0.3, 0.1],
        "delta_BB9": [-0.2, 0.0],
        "wRC_plus_home": [105, 98],
        "OPS_home": [0.75, 0.72],
        "Fly_Ball_Pct_home": [0.35, 0.40],
        "wRC_plus_away": [102, 108],
        "OPS_away": [0.73, 0.78],
        "Fly_Ball_Pct_away": [0.38, 0.36],
        "fatiga_bullpen_home": [45, 52],
        "fatiga_bullpen_away": [38, 60],
        "home_win": [1, 0],
    })


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    return {
        "MLB_ENV": "test",
        "MLB_LOG_LEVEL": "DEBUG",
        "MLB_LOG_JSON": "false",
        "MLB_API_TIMEOUT": "15",
        "MLB_API_MAX_RETRIES": "3",
        "MLB_API_RATE_LIMIT_SLEEP": "0.35",
    }
