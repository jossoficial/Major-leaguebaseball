from datetime import datetime

import pandas as pd

from src.analytics.batting_analytics import BattingAnalytics
from src.analytics.bullpen_analytics import BullpenAnalytics
from src.analytics.context_analytics import ContextAnalytics
from src.analytics.pitcher_analytics import PitcherAnalytics
from src.data.cache_manager import CacheManager
from src.data.mlb_api_client import MLBAPIClient
from src.pipeline.feature_builder import build_frame
from src.utils.constants import REPORTS_DIR
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MLBDataPipeline:
    """Pipeline principal: juegos de hoy -> DataFrame de features listo para el modelo."""

    def __init__(self, date_str: str | None = None):
        self.date = date_str or datetime.now().strftime("%Y-%m-%d")
        self.season = int(self.date[:4])
        self.api = MLBAPIClient()
        self.pitchers = PitcherAnalytics()
        self.batting = BattingAnalytics()
        self.bullpen = BullpenAnalytics(self.api)
        self.context = ContextAnalytics(self.api)
        self.cache = CacheManager("schedule")

    def juegos_hoy(self) -> pd.DataFrame:
        data = self.api.schedule(self.date, self.date, hydrate="team,probablePitcher")
        rows = []
        for d in data.get("dates", []):
            for g in d.get("games", []):
                home, away = g["teams"]["home"], g["teams"]["away"]
                rows.append({
                    "date": self.date, "game_pk": g["gamePk"],
                    "home_team": home["team"]["name"], "away_team": away["team"]["name"],
                    "home_abbr": home["team"].get("abbreviation"),
                    "away_abbr": away["team"].get("abbreviation"),
                    "home_pitcher": (home.get("probablePitcher") or {}).get("fullName", "TBD"),
                    "away_pitcher": (away.get("probablePitcher") or {}).get("fullName", "TBD"),
                })
        return pd.DataFrame(rows)

    def _standings_pct(self) -> dict:
        cached = self.cache.get_json(f"pct_{self.season}")
        if cached is not None:
            return cached
        data = self.api.standings(self.season)
        pct = {}
        for record in data.get("records", []):
            for t in record.get("teamRecords", []):
                name = t["team"]["name"]
                if "winningPercentage" in t:
                    pct[name] = float(t["winningPercentage"])
                else:
                    w, l = t.get("gamesWon", 0), t.get("gamesLost", 0)
                    pct[name] = w / (w + l) if (w + l) else 0.5
        self.cache.set_json(f"pct_{self.season}", pct)
        return pct

    def ejecutar(self) -> pd.DataFrame:
        games = self.juegos_hoy()
        if games.empty:
            logger.warning("No hay juegos programados para %s", self.date)
            return games

        pct = self._standings_pct()
        records = []
        for g in games.itertuples():
            rec = g._asdict()
            rec["diff_pct"] = round(pct.get(g.home_team, 0.5) - pct.get(g.away_team, 0.5), 4)
            rec.update(self.pitchers.deltas(g.home_pitcher, g.away_pitcher, self.season))
            rec.update(self.batting.matchup(g.home_abbr, g.away_abbr, self.season))
            rec["fatiga_bullpen_home"] = self.bullpen.fatigue(g.home_abbr, self.date)
            rec["fatiga_bullpen_away"] = self.bullpen.fatigue(g.away_abbr, self.date)
            rec.update(self.context.context_features(g.home_abbr, g.away_abbr, self.date))
            records.append(rec)
            logger.info("Procesado: %s @ %s", g.away_abbr, g.home_abbr)

        return build_frame(records)

    def guardar_csv(self, df: pd.DataFrame) -> str:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORTS_DIR / f"juegos_{self.date}.csv"
        df.to_csv(path, index=False)
        logger.info("Guardado: %s", path)
        return str(path)
