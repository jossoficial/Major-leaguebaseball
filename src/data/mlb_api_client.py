import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.core.exceptions import ExternalServiceError
from src.utils.constants import MLB_BASE_URL, SETTINGS, USER_AGENT
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MLBAPIClient:
    """Cliente centralizado con timeout, retries, backoff y rate-limit."""

    def __init__(self):
        cfg = SETTINGS["api"]
        self.session = requests.Session()
        retry = Retry(
            total=0,  # El bucle explícito conserva el control del rate limit y los logs.
            connect=0,
            read=0,
            status=0,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.max_retries = max(1, int(cfg.get("max_retries", 3)))
        self.timeout = max(1, int(cfg.get("timeout", 15)))
        self.sleep = max(0.0, float(cfg.get("rate_limit_sleep", 0.35)))

    def get(self, path: str, **params):
        url = path if path.startswith("http") else f"{MLB_BASE_URL}{path}"
        last_error = None
        for attempt in range(self.max_retries):
            try:
                if self.sleep:
                    time.sleep(self.sleep)
                response = self.session.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                wait = min(30, 2 ** attempt)
                logger.warning("Intento %d/%d fallo: %s | esperando %ds", attempt + 1,
                               self.max_retries, exc, wait)
                if attempt < self.max_retries - 1:
                    time.sleep(wait)
        raise ExternalServiceError(
            f"No se pudo consultar {url} tras {self.max_retries} intentos"
        ) from last_error

    def schedule(self, start_date: str, end_date: str,
                 hydrate: str = "team,probablePitcher,linescore") -> dict:
        return self.get("/schedule", sportId=1, startDate=start_date,
                        endDate=end_date, hydrate=hydrate)

    def boxscore(self, game_pk: int) -> dict:
        return self.get(f"/game/{game_pk}/boxscore")

    def standings(self, season: int) -> dict:
        return self.get("/standings", leagueId="103,104", season=season)
