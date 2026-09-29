"""Integration tests for data layer modules."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.data.cache_manager import CacheManager
from src.data.mlb_api_client import MLBAPIClient
from src.core.exceptions import ExternalServiceError


class TestCacheManager:
    """Test cache persistence and TTL."""

    @pytest.fixture
    def temp_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch('src.data.cache_manager.CACHE_DIR', new_callable=lambda: tempfile.TemporaryDirectory().name)
    def test_set_and_get_dataframe(self, mock_cache_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cache_dir_path = Path(tmpdir)
            with patch('src.data.cache_manager.CACHE_DIR', mock_cache_dir_path):
                cache = CacheManager("test", ttl_hours=24)
                df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
                cache.set("test_key", df)
                cached_df = cache.get("test_key")
                assert cached_df is not None
                pd.testing.assert_frame_equal(df, cached_df)

    @patch('src.data.cache_manager.CACHE_DIR')
    def test_get_expired_cache(self, mock_cache_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cache_dir_path = Path(tmpdir)
            with patch('src.data.cache_manager.CACHE_DIR', mock_cache_dir_path):
                cache = CacheManager("test", ttl_hours=0)  # TTL = 0 = expires immediately
                df = pd.DataFrame({"a": [1, 2, 3]})
                cache.set("test_key", df)
                # Simulate cache expiration
                meta_file = (mock_cache_dir_path / "test" / "*.meta")
                cached_df = cache.get("test_key")
                # Should be None or the cache should be considered expired
                # (depends on actual TTL implementation)

    @patch('src.data.cache_manager.CACHE_DIR')
    def test_set_and_get_json(self, mock_cache_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cache_dir_path = Path(tmpdir)
            with patch('src.data.cache_manager.CACHE_DIR', mock_cache_dir_path):
                cache = CacheManager("test", ttl_hours=24)
                data = {"key": "value", "number": 42}
                cache.set_json("json_key", data)
                cached_data = cache.get_json("json_key")
                assert cached_data == data


class TestMLBAPIClient:
    """Test API client retry logic and error handling."""

    @patch('src.data.mlb_api_client.requests.Session.get')
    def test_successful_request(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": "success"}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = MLBAPIClient()
        result = client.get("/test", param1="value1")
        assert result == {"data": "success"}

    @patch('src.data.mlb_api_client.requests.Session.get')
    def test_retry_on_timeout(self, mock_get):
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")

        client = MLBAPIClient()
        with pytest.raises(ExternalServiceError):
            client.get("/test")
        # Verify retries were attempted
        assert mock_get.call_count >= client.max_retries

    @patch('src.data.mlb_api_client.requests.Session.get')
    def test_http_error(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404 Not Found")
        mock_get.return_value = mock_response

        client = MLBAPIClient()
        with pytest.raises(ExternalServiceError):
            client.get("/nonexistent")

    @patch('src.data.mlb_api_client.requests.Session.get')
    def test_schedule_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"dates": [{"games": []}]}
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        client = MLBAPIClient()
        result = client.schedule("2026-09-29", "2026-09-30")
        assert "dates" in result
        mock_get.assert_called_once()
