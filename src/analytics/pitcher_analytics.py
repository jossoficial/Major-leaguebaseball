import numpy as np
import pandas as pd

from src.data.pybaseball_wrapper import PybaseballWrapper
from src.utils.logger import get_logger

logger = get_logger(__name__)

SABER_COLS = ("FIP", "WAR", "K/9", "BB/9")


def _pick(row: pd.Series, *names, default=np.nan):
    for n in names:
        if n in row.index and pd.notna(row[n]):
            return row[n]
    return default


class PitcherAnalytics:
    """Metricas de abridores: deltas local - visitante (positivo = ventaja local).

    Convencion de signos:
      delta_FIP  = FIP_away  - FIP_home   (FIP menor es mejor)
      delta_WAR  = WAR_home  - WAR_away
      delta_K9   = K9_home   - K9_away
      delta_BB9  = BB9_away  - BB9_home   (BB9 menor es mejor)
    """

    def __init__(self, stats_provider=None):
        self.provider = stats_provider or PybaseballWrapper()

    def pitcher_line(self, name: str, season: int, as_of: str | None = None) -> dict | None:
        df = self.provider.pitching(season, as_of) if hasattr(self.provider, "pitching") \
            else self.provider.pitching_stats(season)
        if "Name" not in df.columns:
            return None
        target = name.strip().lower()
        exact = df[df["Name"].astype(str).str.strip().str.lower() == target]
        row = exact.iloc[0] if len(exact) else None
        if row is None:  # fallback: apellido
            last = target.split()[-1]
            fuzzy = df[df["Name"].astype(str).str.contains(last, case=False, na=False)]
            row = fuzzy.iloc[0] if len(fuzzy) else None
        if row is None:
            logger.debug("Lanzador no encontrado: %s", name)
            return None
        return {k: float(_pick(row, k, default=0.0)) for k in SABER_COLS}

    def deltas(self, home_pitcher: str, away_pitcher: str, season: int,
               as_of: str | None = None) -> dict:
        h = self.pitcher_line(home_pitcher, season, as_of) or dict.fromkeys(SABER_COLS, 0.0)
        a = self.pitcher_line(away_pitcher, season, as_of) or dict.fromkeys(SABER_COLS, 0.0)
        return {
            "delta_FIP": a["FIP"] - h["FIP"],
            "delta_WAR": h["WAR"] - a["WAR"],
            "delta_K9": h["K/9"] - a["K/9"],
            "delta_BB9": a["BB/9"] - h["BB/9"],
        }
