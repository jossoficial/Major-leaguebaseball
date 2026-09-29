from math import asin, cos, radians, sin, sqrt

import pandas as pd

from src.data.cache_manager import CacheManager
from src.data.mlb_api_client import MLBAPIClient

# Coordenadas aproximadas de los estadios (lat, lon)
STADIUM_COORDS = {
    "ARI": (33.445, -112.066), "ATH": (38.582, -121.503), "OAK": (37.746, -122.202),
    "ATL": (33.890, -84.468), "BAL": (39.284, -76.620), "BOS": (42.346, -71.098),
    "CHC": (41.948, -87.656), "CWS": (41.830, -87.634), "CIN": (39.097, -84.508),
    "CLE": (41.496, -81.685), "COL": (39.756, -104.994), "DET": (42.339, -83.049),
    "HOU": (29.757, -95.356), "KC": (39.051, -94.481), "LAA": (33.800, -117.883),
    "LAD": (34.073, -118.240), "MIA": (25.778, -80.220), "MIL": (43.028, -87.971),
    "MIN": (44.982, -93.278), "NYM": (40.757, -73.846), "NYY": (40.830, -73.926),
    "PHI": (39.906, -75.166), "PIT": (40.447, -80.007), "SD": (32.707, -117.157),
    "SF": (37.778, -122.389), "SEA": (47.591, -122.333), "STL": (38.623, -90.193),
    "TB": (27.768, -82.653), "TEX": (32.747, -97.084), "TOR": (43.641, -79.389),
    "WSH": (38.873, -77.007),
}


def haversine_km(a: tuple, b: tuple) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * asin(sqrt(h))


class ContextAnalytics:
    """Features de contexto: dias de descanso y distancia de viaje (haversine).

    Aproximacion: la sede de un juego se identifica con el estadio del equipo
    local de ese juego (ignora series neutrales, despreciable en MLB regular).
    """

    def __init__(self, api: MLBAPIClient | None = None):
        self.api = api or MLBAPIClient()
        self.cache = CacheManager("context")

    def _prev_game(self, abbr: str, date: str):
        start = (pd.Timestamp(date) - pd.Timedelta(days=8)).strftime("%Y-%m-%d")
        prev = (pd.Timestamp(date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        key = f"prev_{abbr}_{date}"
        cached = self.cache.get_json(key)
        if cached is not None:
            return cached.get("prev_date"), cached.get("prev_venue")

        data = self.api.schedule(start, prev, hydrate="team")
        best = None
        for d in data.get("dates", []):
            for g in d.get("games", []):
                if g.get("status", {}).get("abstractGameState") != "Final":
                    continue
                home = g["teams"]["home"]["team"]
                away = g["teams"]["away"]["team"]
                if home.get("abbreviation") == abbr:
                    cand = (d.get("date"), away.get("abbreviation"))
                elif away.get("abbreviation") == abbr:
                    cand = (d.get("date"), home.get("abbreviation"))
                else:
                    continue
                if best is None or cand[0] > best[0]:
                    best = cand
        result = {"prev_date": best[0] if best else None,
                  "prev_venue": best[1] if best else None}
        self.cache.set_json(key, result)
        return result["prev_date"], result["prev_venue"]

    def context_features(self, home: str, away: str, date: str) -> dict:
        out = {"month": int(date[5:7])}
        for side, abbr in (("home", home), ("away", away)):
            prev_date, prev_venue = self._prev_game(abbr, date)
            if prev_date is None:
                out[f"rest_days_{side}"] = 3
                out[f"travel_km_{side}"] = 0.0
                continue
            out[f"rest_days_{side}"] = (pd.Timestamp(date) - pd.Timestamp(prev_date)).days - 1
            c_from, c_to = STADIUM_COORDS.get(prev_venue), STADIUM_COORDS.get(home)
            out[f"travel_km_{side}"] = haversine_km(c_from, c_to) if c_from and c_to else 0.0
        out["diff_rest"] = out["rest_days_home"] - out["rest_days_away"]
        out["diff_travel_km"] = round(out["travel_km_home"] - out["travel_km_away"], 1)
        return out
