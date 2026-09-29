import pandas as pd

from src.data.cache_manager import CacheManager
from src.data.mlb_api_client import MLBAPIClient
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BullpenAnalytics:
    """Fatiga del bullpen (0-100) calculada con boxscores reales de la MLB API.

    Componentes (ultimos 3 dias):
      45% pitcheos de relevistas         (150 pitches = agotado)
      25% pitcheos del dia anterior      (60 pitches = agotado)
      20% apariciones de relevistas      (10 = agotado)
      10% apariciones en juegos cerrados (margen <= 2, 4 = agotado)
      +15 si no hubo juego el dia anterior (bullpen frio sin uso reciente)
    """

    def __init__(self, api: MLBAPIClient | None = None):
        self.api = api or MLBAPIClient()
        self.cache = CacheManager("bullpen")

    def _recent_games(self, abbr: str, date: str) -> pd.DataFrame:
        start = (pd.Timestamp(date) - pd.Timedelta(days=4)).strftime("%Y-%m-%d")
        prev = (pd.Timestamp(date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        key = f"recent_{abbr}_{start}_{prev}"
        df = self.cache.get(key)
        if df is not None:
            return df

        data = self.api.schedule(start, prev, hydrate="team,probablePitcher,linescore")
        rows = []
        for d in data.get("dates", []):
            for g in d.get("games", []):
                if g.get("status", {}).get("abstractGameState") != "Final":
                    continue
                home, away = g["teams"]["home"], g["teams"]["away"]
                sides = {home["team"].get("abbreviation"): ("home", home),
                         away["team"].get("abbreviation"): ("away", away)}
                if abbr not in sides:
                    continue
                side, mine = sides[abbr]
                ls = g.get("linescore", {}).get("teams", {})
                h_r = ls.get("home", {}).get("runs", 0) or 0
                a_r = ls.get("away", {}).get("runs", 0) or 0
                rows.append({
                    "date": d.get("date"),
                    "game_pk": g["gamePk"], "side": side,
                    "starter_id": (mine.get("probablePitcher") or {}).get("id"),
                    "margin": abs(h_r - a_r),
                })
        df = pd.DataFrame(rows)
        self.cache.set(key, df)
        return df

    def _boxscore(self, game_pk: int) -> dict:
        key = f"bs_{game_pk}"
        bs = self.cache.get_json(key)
        if bs is None:
            bs = self.api.boxscore(game_pk)
            self.cache.set_json(key, bs)
        return bs

    def fatigue(self, abbr: str, date: str) -> float:
        games = self._recent_games(abbr, date)
        prev_day = (pd.Timestamp(date) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        p3 = p1 = app3 = lev3 = 0
        played_yesterday = False
        for g in games.itertuples() if not games.empty else []:
            team = self._boxscore(g.game_pk).get("teams", {}).get(g.side, {})
            players = team.get("players", {})
            for pid in team.get("pitchers", []):
                p = players.get(f"ID{pid}") or {}
                st = (p.get("stats") or {}).get("pitching") or {}
                pitches = st.get("pitchesThrown", st.get("pitches", 0)) or 0
                if pitches <= 0 or pid == g.starter_id:
                    continue  # solo relevistas con trabajo real
                p3 += pitches
                app3 += 1
                if g.margin <= 2:
                    lev3 += 1
                if g.date == prev_day:
                    p1 += pitches
                    played_yesterday = True

        raw = 100.0 * (
            0.45 * min(p3 / 150.0, 1.0)
            + 0.25 * min(p1 / 60.0, 1.0)
            + 0.20 * min(app3 / 10.0, 1.0)
            + 0.10 * min(lev3 / 4.0, 1.0)
        )
        if not played_yesterday:
            raw = min(raw + 15.0, 100.0)
        return round(float(raw), 2)
