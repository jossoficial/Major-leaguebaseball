import pandas as pd

from src.data.cache_manager import CacheManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class PybaseballWrapper:
    """Wrapper con cache para pybaseball (FanGraphs / Baseball Reference).

    Provee stats de temporada COMPLETA. Para backtests sin data leakage
    usar AsOfStatsProvider (historical_loader).
    """

    def __init__(self):
        self.cache = CacheManager("sabermetrics")
        try:
            import pybaseball  # noqa: F401
        except ImportError:
            raise ImportError("Instala pybaseball: pip install pybaseball")

    def pitching_stats(self, season: int) -> pd.DataFrame:
        from pybaseball import pitching_stats
        return self.cache.get_or_fetch(f"pitching_{season}",
                                       lambda: pitching_stats(season))

    def batting_stats(self, season: int) -> pd.DataFrame:
        from pybaseball import batting_stats
        return self.cache.get_or_fetch(f"batting_{season}",
                                       lambda: batting_stats(season))

    def standings(self, season: int) -> pd.DataFrame:
        from pybaseball import standings
        return self.cache.get_or_fetch(f"standings_{season}",
                                       lambda: pd.concat(standings(season),
                                                         ignore_index=True))

    def schedule_and_record(self, season: int, team: str) -> pd.DataFrame:
        from pybaseball import schedule_and_record
        return self.cache.get_or_fetch(
            f"record_{season}_{team}",
            lambda: schedule_and_record(season, team))
