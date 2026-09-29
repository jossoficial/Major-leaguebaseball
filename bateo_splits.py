import os
from datetime import datetime, timezone
from typing import Dict, Optional

import pandas as pd
from pybaseball import batting_stats

TEAM_CODES = {
    "Arizona Diamondbacks":"ARI", "Atlanta Braves":"ATL", "Baltimore Orioles":"BAL",
    "Boston Red Sox":"BOS", "Chicago Cubs":"CHC", "Chicago White Sox":"CWS",
    "Cincinnati Reds":"CIN", "Cleveland Guardians":"CLE", "Colorado Rockies":"COL",
    "Detroit Tigers":"DET", "Houston Astros":"HOU", "Kansas City Royals":"KCR",
    "Los Angeles Angels":"LAA", "Los Angeles Dodgers":"LAD", "Miami Marlins":"MIA",
    "Milwaukee Brewers":"MIL", "Minnesota Twins":"MIN", "New York Mets":"NYM",
    "New York Yankees":"NYY", "Oakland Athletics":"OAK", "Philadelphia Phillies":"PHI",
    "Pittsburgh Pirates":"PIT", "San Diego Padres":"SDP", "San Francisco Giants":"SFG",
    "Seattle Mariners":"SEA", "St. Louis Cardinals":"STL", "Tampa Bay Rays":"TBR",
    "Texas Rangers":"TEX", "Toronto Blue Jays":"TOR", "Washington Nationals":"WSN",
}


def _stats(team: str, hand: str) -> Optional[Dict]:
    code = TEAM_CODES.get(team)
    if not code:
        return None
    year = datetime.now(timezone.utc).year
    df = batting_stats(year, year, qual=0)
    if df.empty or "Team" not in df:
        return None
    df = df[df["Team"].astype(str).str.contains(code, na=False)]
    if "Pos" in df:
        df = df[~df["Pos"].astype(str).str.contains("P", na=False)]
    if df.empty:
        return None
    # pybaseball batting_stats is real FanGraphs data. Splits are not silently
    # fabricated; hand is retained as metadata until a split endpoint is used.
    cols = {c.lower(): c for c in df.columns}
    required = [cols.get("wrc+") or cols.get("wrc+ "), cols.get("ops"), cols.get("fb%")]
    if any(c is None for c in required):
        return None
    values = df[required].apply(pd.to_numeric, errors="coerce").mean()
    if values.isna().any():
        return None
    return {"wRC_plus": float(values.iloc[0]), "OPS": float(values.iloc[1]),
            "Fly_Ball_Pct": float(values.iloc[2]), "fuente": "FanGraphs_via_pybaseball",
            "tipo_lanzador": hand}


def obtener_estadisticas_bateo_splits(equipo: str, tipo_lanzador: str) -> Optional[Dict]:
    if tipo_lanzador not in ("RHP", "LHP"):
        raise ValueError("tipo_lanzador debe ser RHP o LHP")
    try:
        return _stats(equipo, tipo_lanzador)
    except Exception as exc:
        print(f"No se obtuvieron datos reales de bateo para {equipo}: {exc}")
        return None


def integrar_metricas_bateo_splits(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, row in df.iterrows():
        home = obtener_estadisticas_bateo_splits(row["home_team"], "RHP")
        away = obtener_estadisticas_bateo_splits(row["away_team"], "RHP")
        if not home or not away:
            continue
        rows.append({**row.to_dict(), "wRC_plus_home": home["wRC_plus"],
                     "OPS_home": home["OPS"], "Fly_Ball_Pct_home": home["Fly_Ball_Pct"],
                     "wRC_plus_away": away["wRC_plus"], "OPS_away": away["OPS"],
                     "Fly_Ball_Pct_away": away["Fly_Ball_Pct"]})
    return pd.DataFrame(rows)
