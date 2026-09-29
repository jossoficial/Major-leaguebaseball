import os
from pathlib import Path

import yaml

from src.core.config import ROOT, env_float, env_int


def load_settings(path: Path | None = None) -> dict:
    path = path or ROOT / "config" / "settings.yaml"
    with open(path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}
    settings.setdefault("api", {})
    settings["api"]["timeout"] = env_int("MLB_API_TIMEOUT", settings["api"].get("timeout", 15))
    settings["api"]["max_retries"] = env_int("MLB_API_MAX_RETRIES", settings["api"].get("max_retries", 3))
    settings["api"]["rate_limit_sleep"] = env_float(
        "MLB_API_RATE_LIMIT_SLEEP", settings["api"].get("rate_limit_sleep", 0.35)
    )
    return settings


SETTINGS = load_settings()


def _path_setting(name: str) -> Path:
    configured = os.getenv(f"MLB_{name.upper()}", SETTINGS["paths"][name])
    return Path(configured) if Path(configured).is_absolute() else ROOT / configured


CACHE_DIR = _path_setting("cache_dir")
DATA_DIR = _path_setting("data_dir")
REPORTS_DIR = _path_setting("reports_dir")
MODELS_DIR = _path_setting("models_dir")

MLB_BASE_URL = os.getenv("MLB_BASE_URL", "https://statsapi.mlb.com/api/v1")
USER_AGENT = os.getenv("MLB_USER_AGENT", "mlb-sabermetrics-pipeline/2.1")

TEAM_NAME_MAP = {
    "ARI": "Arizona Diamondbacks", "ATH": "Athletics", "OAK": "Athletics",
    "ATL": "Atlanta Braves", "BAL": "Baltimore Orioles", "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs", "CWS": "Chicago White Sox", "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians", "COL": "Colorado Rockies", "DET": "Detroit Tigers",
    "HOU": "Houston Astros", "KC": "Kansas City Royals", "LAA": "Los Angeles Angels",
    "LAD": "Los Angeles Dodgers", "MIA": "Miami Marlins", "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins", "NYM": "New York Mets", "NYY": "New York Yankees",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates", "SD": "San Diego Padres",
    "SF": "San Francisco Giants", "SEA": "Seattle Mariners", "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays", "TEX": "Texas Rangers", "TOR": "Toronto Blue Jays",
    "WSH": "Washington Nationals",
}
