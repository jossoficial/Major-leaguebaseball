from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def load_settings(path: Path | None = None) -> dict:
    path = path or ROOT / "config" / "settings.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


SETTINGS = load_settings()

CACHE_DIR = ROOT / SETTINGS["paths"]["cache_dir"]
DATA_DIR = ROOT / SETTINGS["paths"]["data_dir"]
REPORTS_DIR = ROOT / SETTINGS["paths"]["reports_dir"]
MODELS_DIR = ROOT / SETTINGS["paths"]["models_dir"]

MLB_BASE_URL = "https://statsapi.mlb.com/api/v1"
USER_AGENT = "mlb-sabermetrics-pipeline/2.0"

# Abreviatura -> nombre completo (segun MLB Stats API)
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
