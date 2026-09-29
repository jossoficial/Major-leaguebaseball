import numpy as np
import pandas as pd

from src.data.cache_manager import CacheManager
from src.data.mlb_api_client import MLBAPIClient
from src.pipeline.feature_builder import build_frame
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AsOfStatsProvider:
    """Stats 'as of' una fecha dada -> evita data leakage en backtests.

    Usa pybaseball *_stats_range acumulando desde el 1 de marzo,
    con cache semanal para no saturar FanGraphs.
    """

    def __init__(self):
        self.cache = CacheManager("asof_stats")

    def _bucket(self, as_of: str) -> str:
        ts = pd.Timestamp(as_of)
        return (ts - pd.Timedelta(days=int(ts.weekday()))).strftime("%Y-%m-%d")

    def pitching(self, season: int, as_of: str | None = None) -> pd.DataFrame:
        from pybaseball import pitching_stats, pitching_stats_range
        if as_of is None:
            return pitching_stats(season)
        key = f"pit_{season}_{self._bucket(as_of)}"
        df = self.cache.get(key)
        if df is None:
            logger.info("Descargando pitching stats acumuladas hasta %s", as_of)
            df = pitching_stats_range(f"{season}-03-01", as_of)
            self.cache.set(key, df)
        return df

    def batting_players(self, season: int, as_of: str | None = None) -> pd.DataFrame:
        from pybaseball import batting_stats, batting_stats_range
        if as_of is None:
            return batting_stats(season)
        key = f"bat_{season}_{self._bucket(as_of)}"
        df = self.cache.get(key)
        if df is None:
            logger.info("Descargando batting stats acumuladas hasta %s", as_of)
            df = batting_stats_range(f"{season}-03-01", as_of)
            self.cache.set(key, df)
        return df


class HistoricalLoader:
    """Descarga partidos FINALIZADOS con resultados y arma el dataset de entrenamiento."""

    def __init__(self):
        self.api = MLBAPIClient()
        self.cache = CacheManager("historical")

    # ---------------- resultados ----------------
    def games(self, start: str, end: str) -> pd.DataFrame:
        key = f"games_{start}_{end}"
        df = self.cache.get(key)
        if df is not None:
            return df

        data = self.api.schedule(start, end)
        rows = []
        for d in data.get("dates", []):
            for g in d.get("games", []):
                if g.get("status", {}).get("abstractGameState") != "Final":
                    continue
                home, away = g["teams"]["home"], g["teams"]["away"]
                ls = g.get("linescore", {}).get("teams", {})
                h_runs = ls.get("home", {}).get("runs")
                a_runs = ls.get("away", {}).get("runs")
                if h_runs is None or a_runs is None:
                    continue
                rows.append({
                    "date": d.get("date") or g.get("gameDate", "")[:10],
                    "game_pk": g["gamePk"],
                    "home_team": home["team"]["name"],
                    "away_team": away["team"]["name"],
                    "home_abbr": home["team"].get("abbreviation"),
                    "away_abbr": away["team"].get("abbreviation"),
                    "home_score": h_runs, "away_score": a_runs,
                    "home_win": int(h_runs > a_runs),
                    "home_pitcher": (home.get("probablePitcher") or {}).get("fullName"),
                    "away_pitcher": (away.get("probablePitcher") or {}).get("fullName"),
                })
        df = pd.DataFrame(rows)
        self.cache.set(key, df)
        logger.info("%d partidos finalizados entre %s y %s", len(df), start, end)
        return df

    # ---------------- dataset con features ----------------
    def build_dataset(self, games: pd.DataFrame) -> pd.DataFrame:
        from src.analytics.batting_analytics import BattingAnalytics
        from src.analytics.bullpen_analytics import BullpenAnalytics
        from src.analytics.context_analytics import ContextAnalytics
        from src.analytics.pitcher_analytics import PitcherAnalytics

        provider = AsOfStatsProvider()
        pitchers = PitcherAnalytics(provider)
        batting = BattingAnalytics(provider)
        bullpen = BullpenAnalytics()
        context = ContextAnalytics()

        valid = games.dropna(subset=["home_pitcher", "away_pitcher", "home_abbr", "away_abbr"])
        records = []
        for row in valid.itertuples():
            season = int(str(row.date)[:4])
            as_of = (pd.Timestamp(row.date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            rec = {
                "date": row.date, "game_pk": row.game_pk,
                "home_team": row.home_team, "away_team": row.away_team,
                "home_abbr": row.home_abbr, "away_abbr": row.away_abbr,
                "home_pitcher": row.home_pitcher, "away_pitcher": row.away_pitcher,
                "diff_pct": 0.0,  # pendiente: standings as-of (ver README)
            }
            rec.update(pitchers.deltas(row.home_pitcher, row.away_pitcher, season, as_of))
            rec.update(batting.matchup(row.home_abbr, row.away_abbr, season, as_of))
            rec["fatiga_bullpen_home"] = bullpen.fatigue(row.home_abbr, row.date)
            rec["fatiga_bullpen_away"] = bullpen.fatigue(row.away_abbr, row.date)
            rec.update(context.context_features(row.home_abbr, row.away_abbr, row.date))
            records.append(rec)

        df = build_frame(records)
        df = df.merge(games[["game_pk", "home_win", "home_score", "away_score"]],
                      on="game_pk", how="left")
        return df
