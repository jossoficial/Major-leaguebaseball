import time

import requests

from src.utils.constants import MLB_BASE_URL, SETTINGS, USER_AGENT
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MLBAPIClient:
    """Cliente centralizado con retries, backoff y rate-limit para la MLB Stats API."""

    def __init__(self):
        cfg = SETTINGS["api"]
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.max_retries = cfg["max_retries"]
        self.timeout = cfg["timeout"]
        self.sleep = cfg["rate_limit_sleep"]

    def get(self, path: str, **params):
        url = path if path.startswith("http") else f"{MLB_BASE_URL}{path}"
        for attempt in range(self.max_retries):
            try:
                time.sleep(self.sleep)
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                wait = 2 ** attempt
                logger.warning("Intento %d/%d fallo: %s | esperando %ds",
                               attempt + 1, self.max_retries, exc, wait)
                time.sleep(wait)
        raise RuntimeError(f"No se pudo consultar {url} tras {self.max_retries} intentos")

    def schedule(self, start_date: str, end_date: str,
                 hydrate: str = "team,probablePitcher,linescore") -> dict:
        return self.get("/schedule", sportId=1, startDate=start_date,
                        endDate=end_date, hydrate=hydrate)

    def boxscore(self, game_pk: int) -> dict:
        return self.get(f"/game/{game_pk}/boxscore")

    def standings(self, season: int) -> dict:
        return self.get("/standings", leagueId="103,104", season=season)
