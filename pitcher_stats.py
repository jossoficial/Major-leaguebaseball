import requests
from typing import Dict


def extraer_metricas_lanzadores(game_pk: int) -> Dict:
    """Obtiene los abridores del feed live oficial de MLB.

    No inventa métricas: si MLB no las publica, devuelve None y el pipeline
    debe excluir ese partido o esperar a que haya datos.
    """
    url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()
    teams = data.get("gameData", {}).get("teams", {})
    live = data.get("liveData", {}).get("boxscore", {}).get("teams", {})

    result = {
        "pitcher_home": None, "pitcher_away": None,
        "delta_FIP": None, "delta_WAR": None,
        "delta_K9": None, "delta_BB9": None,
    }
    for side in ("home", "away"):
        probable = teams.get(side, {}).get("probablePitcher")
        if probable:
            result[f"pitcher_{side}"] = probable.get("fullName")
        # En juegos iniciados, el boxscore es la fuente autoritativa.
        if not result[f"pitcher_{side}"]:
            players = live.get(side, {}).get("players", {})
            starters = [p for p in players.values() if p.get("gameStatus", {}).get("isCurrent")]
            if starters:
                result[f"pitcher_{side}"] = starters[0].get("person", {}).get("fullName")
    return result
