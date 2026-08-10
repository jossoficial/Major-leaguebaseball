import pandas as pd
from datetime import datetime
from typing import List, Dict
from src.data.mlb_api_client import MLBStatsAPIClient
from src.analytics.pitcher_analytics import PitcherAnalytics
from src.analytics.batting_analytics import BattingAnalytics
from src.analytics.bullpen_analytics import BullpenAnalytics

class MLBDataPipeline:
    """
    Pipeline principal que orquesta la extracción y procesamiento
    de datos MLB para machine learning.
    
    Flujo:
    1. Obtener juegos del día
    2. Extraer métricas de lanzadores (sabermetría)
    3. Extraer métricas de bateo (splits)
    4. Extraer fatiga del bullpen
    5. Generar CSV para ML
    """
    
    # Mapeo de equipos a IDs MLB Stats API
    TEAM_ID_MAP = {
        'Arizona Diamondbacks': 109,
        'Atlanta Braves': 144,
        'Baltimore Orioles': 110,
        'Boston Red Sox': 111,
        'Chicago Cubs': 112,
        'Chicago White Sox': 145,
        'Cincinnati Reds': 113,
        'Cleveland Guardians': 114,
        'Colorado Rockies': 115,
        'Detroit Tigers': 116,
        'Houston Astros': 117,
        'Kansas City Royals': 118,
        'Los Angeles Angels': 108,
        'Los Angeles Dodgers': 119,
        'Miami Marlins': 146,
        'Milwaukee Brewers': 158,
        'Minnesota Twins': 142,
        'New York Mets': 121,
        'New York Yankees': 147,
        'Oakland Athletics': 133,
        'Philadelphia Phillies': 143,
        'Pittsburgh Pirates': 23,
        'San Diego Padres': 25,
        'San Francisco Giants': 137,
        'Seattle Mariners': 136,
        'St. Louis Cardinals': 138,
        'Tampa Bay Rays': 139,
        'Texas Rangers': 140,
        'Toronto Blue Jays': 141,
        'Washington Nationals': 120,
    }
    
    def __init__(self):
        self.api = MLBStatsAPIClient()
        self.pitcher_analytics = PitcherAnalytics()
        self.batting_analytics = BattingAnalytics()
        self.bullpen_analytics = BullpenAnalytics()
    
    def obtener_tipo_lanzador(self, nombre: str) -> str:
        """
        Determina si un lanzador es derecho (RHP) o zurdo (LHP).
        Por defecto retorna RHP si no puede determinarse.
        
        Args:
            nombre: Nombre del lanzador
            
        Returns:
            'RHP' o 'LHP'
        """
        # Simplificado: siempre retorna RHP
        # En producción, consultar a pybaseball
        return 'RHP'
    
    def calcular_win_percentage(self, wins: int, losses: int) -> float:
        """
        Calcula porcentaje de victorias.
        
        Args:
            wins: Victorias
            losses: Derrotas
            
        Returns:
            Porcentaje de victorias (0-1)
        """
        total = wins + losses
        return wins / total if total > 0 else 0.5
    
    def procesar_juego(self, juego: Dict) -> Dict:
        """
        Procesa un juego individual y extrae todas las métricas.
        
        Args:
            juego: Diccionario con datos del juego
            
        Returns:
            Dict con todas las features para ML
        """
        try:
            # Datos básicos
            away_team = juego['teams']['away']['team']['name']
            home_team = juego['teams']['home']['team']['name']
            away_id = juego['teams']['away']['team']['id']
            home_id = juego['teams']['home']['team']['id']
            game_pk = juego.get('gamePk')
            
            print(f"\n🎯 Procesando: {away_team} @ {home_team}")
            
            # Calcular diferencia de porcentaje de victorias
            try:
                away_team_data = self.api.get_team(away_id)
                home_team_data = self.api.get_team(home_id)
                
                away_record = away_team_data.get('teams', [{}])[0].get('record', [{}])[0] if away_team_data else {}
                home_record = home_team_data.get('teams', [{}])[0].get('record', [{}])[0] if home_team_data else {}
                
                away_pct = self.calcular_win_percentage(
                    away_record.get('wins', 0),
                    away_record.get('losses', 0)
                )
                home_pct = self.calcular_win_percentage(
                    home_record.get('wins', 0),
                    home_record.get('losses', 0)
                )
                diff_pct = home_pct - away_pct
            except:
                diff_pct = 0.0
            
            # Métricas de lanzadores
            pitcher_metrics = self.pitcher_analytics.analizar_juego(game_pk)
            
            # Métricas de bateo
            tipo_pitcher_home = self.obtener_tipo_lanzador(pitcher_metrics.get('pitcher_home', ''))
            tipo_pitcher_away = self.obtener_tipo_lanzador(pitcher_metrics.get('pitcher_away', ''))
            
            stats_home = self.batting_analytics.obtener_estadisticas(home_team, tipo_pitcher_away) or {}
            stats_away = self.batting_analytics.obtener_estadisticas(away_team, tipo_pitcher_home) or {}
            
            # Métricas de bullpen
            fatiga_home = self.bullpen_analytics.calcular_fatiga(home_id, home_team)
            fatiga_away = self.bullpen_analytics.calcular_fatiga(away_id, away_team)
            
            # Armar registro
            return {
                'away_team': away_team,
                'home_team': home_team,
                'diff_pct': diff_pct,
                'pitcher_away': pitcher_metrics.get('pitcher_away', 'Unknown'),
                'pitcher_home': pitcher_metrics.get('pitcher_home', 'Unknown'),
                'delta_FIP': pitcher_metrics.get('delta_FIP', 0.0),
                'delta_WAR': pitcher_metrics.get('delta_WAR', 0.0),
                'delta_K9': pitcher_metrics.get('delta_K9', 0.0),
                'delta_BB9': pitcher_metrics.get('delta_BB9', 0.0),
                'wRC_plus_home': stats_home.get('wRC_plus', 100.0),
                'OPS_home': stats_home.get('OPS', 0.720),
                'Fly_Ball_Pct_home': stats_home.get('Fly_Ball_Pct', 32.5),
                'wRC_plus_away': stats_away.get('wRC_plus', 100.0),
                'OPS_away': stats_away.get('OPS', 0.720),
                'Fly_Ball_Pct_away': stats_away.get('Fly_Ball_Pct', 32.5),
                'fatiga_bullpen_home': fatiga_home.get('puntuacion_fatiga', 50.0),
                'fatiga_bullpen_away': fatiga_away.get('puntuacion_fatiga', 50.0),
            }
        except Exception as e:
            print(f"❌ Error procesando juego: {e}")
            return None
    
    def ejecutar(self, fecha: str = None) -> pd.DataFrame:
        """
        Ejecuta el pipeline completo para una fecha.
        
        Args:
            fecha: Fecha en formato YYYY-MM-DD (default: hoy)
            
        Returns:
            DataFrame con todos los juegos y features
        """
        if not fecha:
            fecha = datetime.today().strftime('%Y-%m-%d')
        
        print(f"\n📅 Ejecutando pipeline para {fecha}...")
        
        # Obtener juegos
        juegos = self.api.get_schedule(fecha)
        
        if not juegos:
            print(f"⚠️ No hay juegos para {fecha}")
            return pd.DataFrame()
        
        # Filtrar juegos programados/en progreso
        juegos_activos = [
            j for j in juegos
            if j.get('status', {}).get('abstractGameState') in ['Scheduled', 'Pre-Game', 'In Progress', 'Live']
        ]
        
        if not juegos_activos:
            print(f"⚠️ No hay juegos programados para {fecha}")
            return pd.DataFrame()
        
        # Procesar cada juego
        juegos_data = []
        for juego in juegos_activos:
            resultado = self.procesar_juego(juego)
            if resultado:
                juegos_data.append(resultado)
        
        if juegos_data:
            df = pd.DataFrame(juegos_data)
            print(f"\n✅ {len(juegos_data)} juegos procesados")
            print(f"📊 Features generadas: {df.columns.tolist()}")
            return df
        else:
            print("⚠️ No se pudieron procesar los juegos")
            return pd.DataFrame()
    
    def guardar_csv(self, df: pd.DataFrame, filename: str = 'juegos_hoy.csv') -> None:
        """
        Guarda el DataFrame en CSV.
        
        Args:
            df: DataFrame a guardar
            filename: Nombre del archivo
        """
        if df.empty:
            print("⚠️ DataFrame vacío. Creando CSV con columnas vacías.")
            columnas = [
                'away_team', 'home_team', 'diff_pct',
                'pitcher_away', 'pitcher_home',
                'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9',
                'wRC_plus_home', 'OPS_home', 'Fly_Ball_Pct_home',
                'wRC_plus_away', 'OPS_away', 'Fly_Ball_Pct_away',
                'fatiga_bullpen_home', 'fatiga_bullpen_away'
            ]
            df = pd.DataFrame(columns=columnas)
        
        df.to_csv(filename, index=False)
        print(f"💾 Datos guardados en {filename}")
