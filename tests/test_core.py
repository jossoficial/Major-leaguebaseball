"""Unit tests for core modules and configurations."""

import pytest
from pathlib import Path
from unittest.mock import patch

from src.core.config import env_bool, env_int, env_float
from src.core.exceptions import ExternalServiceError, ConfigurationError
from src.core.schemas import GameInput, PredictionOutput
from pydantic import ValidationError
from datetime import date


class TestConfig:
    """Test environment variable parsing."""

    def test_env_bool_true_variants(self):
        with patch.dict('os.environ', {'TEST_VAR': '1'}):
            assert env_bool('TEST_VAR') is True
        with patch.dict('os.environ', {'TEST_VAR': 'true'}):
            assert env_bool('TEST_VAR') is True
        with patch.dict('os.environ', {'TEST_VAR': 'yes'}):
            assert env_bool('TEST_VAR') is True
        with patch.dict('os.environ', {'TEST_VAR': 'on'}):
            assert env_bool('TEST_VAR') is True

    def test_env_bool_false_variants(self):
        with patch.dict('os.environ', {'TEST_VAR': '0'}):
            assert env_bool('TEST_VAR') is False
        with patch.dict('os.environ', {'TEST_VAR': 'false'}):
            assert env_bool('TEST_VAR') is False
        with patch.dict('os.environ', {'TEST_VAR': ''}, clear=False):
            assert env_bool('TEST_VAR', default=False) is False

    def test_env_int(self):
        with patch.dict('os.environ', {'TEST_INT': '42'}):
            assert env_int('TEST_INT', 0) == 42
        with patch.dict('os.environ', {'TEST_INT': 'invalid'}):
            assert env_int('TEST_INT', 99) == 99

    def test_env_float(self):
        with patch.dict('os.environ', {'TEST_FLOAT': '3.14'}):
            assert env_float('TEST_FLOAT', 0.0) == 3.14
        with patch.dict('os.environ', {'TEST_FLOAT': 'invalid'}):
            assert env_float('TEST_FLOAT', 2.71) == 2.71


class TestSchemas:
    """Test Pydantic data validation."""

    def test_game_input_valid(self):
        game = GameInput(
            date=date(2026, 9, 29),
            game_pk=12345,
            home_team="Boston Red Sox",
            away_team="New York Yankees",
        )
        assert game.game_pk == 12345
        assert game.home_team == "Boston Red Sox"

    def test_game_input_invalid_game_pk(self):
        with pytest.raises(ValidationError):
            GameInput(
                date=date(2026, 9, 29),
                game_pk=0,
                home_team="Boston Red Sox",
                away_team="New York Yankees",
            )

    def test_game_input_invalid_date(self):
        with pytest.raises(ValidationError):
            GameInput(
                date="2026-09-29",  # Debe ser date, no string
                game_pk=12345,
                home_team="Boston Red Sox",
                away_team="New York Yankees",
            )

    def test_prediction_output_valid(self):
        pred = PredictionOutput(
            game_pk=12345,
            prob_home=0.55,
            prob_away=0.45,
            apostar="HOME",
            stake_unidades=25.0,
        )
        assert pred.prob_home == 0.55
        assert pred.stake_unidades == 25.0

    def test_prediction_output_invalid_probability(self):
        with pytest.raises(ValidationError):
            PredictionOutput(
                game_pk=12345,
                prob_home=1.5,  # Fuera de rango [0, 1]
                prob_away=0.5,
                apostar="",
                stake_unidades=0,
            )


class TestExceptions:
    """Test custom exception classes."""

    def test_external_service_error(self):
        with pytest.raises(ExternalServiceError):
            raise ExternalServiceError("API not available")

    def test_configuration_error(self):
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Missing config key")
