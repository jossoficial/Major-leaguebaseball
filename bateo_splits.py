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
        print(f"⚠️ El nombre del equipo '{team}' no está mapeado en TEAM_CODES.")
        return None
        
    year = datetime.now(timezone.utc).year
    
    # Obtener estadísticas desde pybaseball (Acceso directo a la API de FanGraphs)
    df = batting_stats(year, year, qual=0)
    
    if df is None or df.empty or "Team" not in df:
        return None
        
    # Filtrar por el código del equipo asignado
    df = df[df["Team"].astype(str).str.contains(code, na=False)]
    
    # Excluir lanzadores (Pitchers) si la columna de posición existe
    if "Pos" in df:
        df = df[~df["Pos"].astype(str).str.contains("P", na=False)]
        
    if df.empty:
        return None
        
    # Estandarizar mapeo de columnas en minúsculas para evitar variaciones de la API
    cols = {c.lower().strip(): c for c in df.columns}
    
    wrc_col = cols.get("wrc+") or cols.get("wrc+ ")
    ops_col = cols.get("ops")
    fb_col = cols.get("fb%")
    
    if not wrc_col or not ops_col or not fb_col:
        print(f"⚠️ Columnas requeridas no encontradas en el dataset de pybaseball.")
        return None
        
    # Calcular promedios reales omitiendo valores nulos
    values = df[[wrc_col, ops_col, fb_col]].apply(pd.to_numeric, errors="coerce").mean()
    
    if values.isna().any():
        return None
        
    return {
        "wRC_plus": float(values.iloc[0]), 
        "OPS": float(values.iloc[1]),
        "Fly_Ball_Pct": float(values.iloc[2]), 
        "fuente": "FanGraphs_via_pybaseball",
        "tipo_lanzador": hand
    }

def obtener_estadisticas_bateo_splits(equipo: str, tipo_lanzador: str) -> Optional[Dict]:
    """Retorna las estadísticas reales de bateo. Si falla la API o no hay registros, devuelve None."""
    if tipo_lanzador not in ("RHP", "LHP"):
        raise ValueError("tipo_lanzador debe ser RHP o LHP")
    try:
        return _stats(equipo, tipo_lanzador)
    except Exception as exc:
        print(f"❌ Error obteniendo datos reales de bateo para {equipo} mediante pybaseball: {exc}")
        return None

def integrar_metricas_bateo_splits(df: pd.DataFrame) -> pd.DataFrame:
    """Procesa el DataFrame saltando renglones si no se encuentran datos reales."""
    rows = []
    for _, row in df.iterrows():
        home = obtener_estadisticas_bateo_splits(row["home_team"], "RHP")
        away = obtener_estadisticas_bateo_splits(row["away_team"], "RHP")
        
        # Validación estricta: Si alguno es nulo, no incluimos la fila en el dataset final
        if not home or not away:
            continue
            
        rows.append({
            **row.to_dict(), 
            "wRC_plus_home": home["wRC_plus"],
            "OPS_home": home["OPS"], 
            "Fly_Ball_Pct_home": home["Fly_Ball_Pct"],
            "wRC_plus_away": away["wRC_plus"], 
            "OPS_away": away["OPS"],
            "Fly_Ball_Pct_away": away["Fly_Ball_Pct"]
        })
    return pd.DataFrame(rows)
