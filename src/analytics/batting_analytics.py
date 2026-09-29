import re

import numpy as np
import pandas as pd

from src.data.pybaseball_wrapper import PybaseballWrapper
from src.utils.constants import TEAM_NAME_MAP
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _series(df: pd.DataFrame, col: str) -> pd.Series:
    """Busca una columna con tolerancia a variantes de nombre."""
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    low = {c.lower(): c for c in df.columns}
    for cand in (col.lower(), col.lower().replace("%", ""), col.lower().replace("_", "")):
        if cand in low:
            return pd.to_numeric(df[low[cand]], errors="coerce").fillna(0.0)
    return pd.Series(0.0, index=df.index)


class BattingAnalytics:
    """wRC+ / OPS / FB% a nivel equipo, ponderados por PA.

    Nota: pybaseball no expone splits vs RHP/LHP directamente; las metricas
    son totales de temporada. Los splits se pueden agregar scrapando FanGraphs
    (team batting vs handedness) en una v2.
    """

    NEUTRAL = {"wRC+": 100.0, "OPS": 0.720, "Fly_Ball_Pct": 0.350}

    def __init__(self, stats_provider=None):
        self.provider = stats_provider or PybaseballWrapper()

    def _batting_df(self, season: int, as_of: str | None) -> pd.DataFrame:
        if hasattr(self.provider, "batting_players"):
            return self.provider.batting_players(season, as_of)
        return self.provider.batting_stats(season)

    def team_metrics(self, team_abbr: str, season: int, as_of: str | None = None) -> dict:
        team_name = TEAM_NAME_MAP.get(team_abbr, team_abbr)
        df = self._batting_df(season, as_of)
        if df.empty or "Team" not in df.columns:
            return dict(self.NEUTRAL)

        teams = df["Team"].astype(str)
        sub = df[teams.str.strip().str.lower() == team_name.strip().lower()]
        if sub.empty:
            sub = df[teams.str.contains(re.escape(team_name), case=False, na=False)]
        pa = _series(sub, "PA")
        if sub.empty or pa.sum() < 100:
            logger.debug("Bateo insuficiente para %s", team_abbr)
            return dict(self.NEUTRAL)

        def wavg(col: str) -> float:
            vals = _series(sub, col)
            return float(np.average(vals, weights=pa)) if pa.sum() > 0 else 0.0

        fb = wavg("FB%")
        if fb > 1.0:  # escala 0-100 -> 0-1
            fb /= 100.0
        return {"wRC+": wavg("wRC+"), "OPS": wavg("OPS"), "Fly_Ball_Pct": fb}

    def matchup(self, home_abbr: str, away_abbr: str, season: int,
                as_of: str | None = None) -> dict:
        h = self.team_metrics(home_abbr, season, as_of)
        a = self.team_metrics(away_abbr, season, as_of)
        return {
            "wRC_plus_home": h["wRC+"], "OPS_home": h["OPS"], "Fly_Ball_Pct_home": h["Fly_Ball_Pct"],
            "wRC_plus_away": a["wRC+"], "OPS_away": a["OPS"], "Fly_Ball_Pct_away": a["Fly_Ball_Pct"],
        }
