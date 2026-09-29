import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import json

def mapeo_team_id_nombres() -> Dict[int, str]:
    """Retorna el mapeo de IDs de la MLB a nombres de equipos oficiales."""
    return {
        109: "Arizona Diamondbacks", 144: "Atlanta Braves", 110: "Baltimore Orioles",
        111: "Boston Red Sox", 112: "Chicago Cubs", 145: "Chicago White Sox",
        113: "Cincinnati Reds", 114: "Cleveland Guardians", 115: "Colorado Rockies",
        116: "Detroit Tigers", 117: "Houston Astros", 118: "Kansas City Royals",
        108: "Los Angeles Angels", 119: "Los Angeles Dodgers", 146: "Miami Marlins",
        158: "Milwaukee Brewers", 142: "Minnesota Twins", 121: "New York Mets",
        147: "New York Yankees", 133: "Oakland Athletics", 143: "Philadelphia Phillies",
        134: "Pittsburgh Pirates", 135: "San Diego Padres", 137: "San Francisco Giants",
        136: "Seattle Mariners", 138: "St. Louis Cardinals", 139: "Tampa Bay Rays",
        140: "Texas Rangers", 141: "Toronto Blue Jays", 120: "Washington Nationals"
    }

def extraer_fatiga_bullpen(team_id: int, nombre_equipo: str) -> Optional[Dict]:
    """Función de interfaz compatible con mlb_data.py"""
    gestor = GestorFatigaBullpen()
    return gestor.calcular_fatiga_bullpen(team_id, nombre_equipo)

class GestorFatigaBullpen:
    """
    Gestor avanzado para evaluar el estado del bullpen de un equipo.
    Analiza los últimos 3 días de boxscores para calcular:
    - Lanzamientos acumulados por relevista
    - Días consecutivos del cerrador
    - Métrica de fatiga del bullpen (0-100)
    """
    
    def __init__(self, cache_dir: str = '.cache_bullpen'):
        self.cache_dir = cache_dir
        self.fecha_hoy = datetime.today().strftime('%Y-%m-%d')
        self.url_base_mlb = "https://mlb.com"
        
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def obtener_juegos_equipo_3dias(self, team_id: int) -> list:
        """Obtiene los IDs de juegos reales de un equipo en los últimos 3 días."""
        try:
            hoy = datetime.today()
            hace_3_dias = (hoy - timedelta(days=3)).strftime('%Y-%m-%d')
            hoy_str = hoy.strftime('%Y-%m-%d')
            
            url = f"{self.url_base_mlb}/schedule?sportId=1&teamId={team_id}&startDate={hace_3_dias}&endDate={hoy_str}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            datos_schedule = response.json()
            game_pks = []
            
            # Navegación corregida y segura por la estructura real de la API
            for fecha_obj in datos_schedule.get("dates", []):
                for juego in fecha_obj.get("games", []):
                    estado_juego = juego.get('status', {}).get('abstractGameState', '')
                    if estado_juego in ['Final', 'Completed']:
                        game_pk = juego.get('gamePk')
                        if game_pk:
                            game_pks.append(game_pk)
            
            print(f"✅ Encontrados {len(game_pks)} juegos reales en los últimos 3 días para team_id={team_id}")
            return game_pks
            
        except Exception as e:
            print(f"❌ Error obteniendo juegos del equipo: {e}")
            return []
    
    def obtener_boxscore_juego(self, game_pk: int) -> Optional[Dict]:
        """Obtiene el boxscore completo de un juego."""
        try:
            url = f"{self.url_base_mlb}/game/{game_pk}/boxscore"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"⚠️ Error obteniendo boxscore para game_pk {game_pk}: {e}")
            return None
    
    def extraer_relevistas_juego(self, boxscore: Dict, team_id: int) -> Dict[str, int]:
        """Extrae los relevistas y su cuenta de lanzamientos de un juego."""
        relevistas = {}
        try:
            home_id = boxscore['teams']['home']['team']['id']
            team_key = 'home' if home_id == team_id else 'away'
            pitchers = boxscore['teams'][team_key]['pitchers']
            
            for pitcher_id in pitchers:
                pitcher_data = boxscore['teams'][team_key]['players'][f'ID{pitcher_id}']
                if pitcher_data.get('stats', {}).get('pitching', {}).get('numberOfPitches', 0) > 0:
                    nombre = pitcher_data['person']['fullName']
                    pitch_count = pitcher_data['stats']['pitching']['numberOfPitches']
                    relevistas[nombre] = pitch_count
            return relevistas
        except Exception as e:
            print(f"⚠️ Error extrayendo relevistas del boxscore: {e}")
            return {}
    
    def identificar_cerrador(self, boxscore: Dict, team_id: int) -> Optional[str]:
        """Identifica al cerrador (último pitcher en lanzar) del equipo."""
        try:
            home_id = boxscore['teams']['home']['team']['id']
            team_key = 'home' if home_id == team_id else 'away'
            pitchers = boxscore['teams'][team_key]['pitchers']
            
            if not pitchers:
                return None
            
            ultimo_pitcher_id = pitchers[-1]
            ultimo_pitcher = boxscore['teams'][team_key]['players'][f'ID{ultimo_pitcher_id}']
            
            if ultimo_pitcher.get('stats', {}).get('pitching', {}).get('numberOfPitches', 0) > 0:
                return ultimo_pitcher['person']['fullName']
            return None
        except Exception as e:
            print(f"⚠️ Error identificando cerrador: {e}")
            return None
    
    def calcular_fatiga_bullpen(self, team_id: int, nombre_equipo: str) -> Optional[Dict]:
        """Calcula la métrica de fatiga real del bullpen para un equipo (0-100)."""
        try:
            print(f"\n🔍 Analizando fatiga del bullpen para {nombre_equipo}...")
            game_pks = self.obtener_juegos_equipo_3dias(team_id)
            
            if not game_pks:
                print(f"⚠️ No hay juegos recientes para {nombre_equipo}. Retornando None por falta de datos reales.")
                return None
            
            lanzamientos_relevistas = {}
            dias_consecutivos_cerrador = {}
            
            for game_pk in game_pks:
                boxscore = self.obtener_boxscore_juego(game_pk)
                if not boxscore:
                    continue
                
                relevistas = self.extraer_relevistas_juego(boxscore, team_id)
                for pitcher, pitch_count in relevistas.items():
                    if pitcher not in lanzamientos_relevistas:
                        lanzamientos_relevistas[pitcher] = 0
                    lanzamientos_relevistas[pitcher] += pitch_count
                
                cerrador = self.identificar_cerrador(boxscore, team_id)
                if cerrador:
                    if cerrador not in dias_consecutivos_cerrador:
                        dias_consecutivos_cerrador[cerrador] = 0
                    dias_consecutivos_cerrador[cerrador] += 1
            
            if not lanzamientos_relevistas:
                return None
                
            total_lanzamientos = sum(lanzamientos_relevistas.values())
            num_relevistas_activos = len(lanzamientos_relevistas)
            dias_cerrador_consecutivos = max(dias_consecutivos_cerrador.values()) if dias_consecutivos_cerrador else 0
            
            # Algoritmo matemático real de fatiga (0 a 100)
            factor_lanzamientos = min(total_lanzamientos / 300.0, 1.0) * 50
            factor_relevistas = max(0, (5 - num_relevistas_activos) * 10) if num_relevistas_activos < 5 else 0
            factor_cerrador = min(dias_cerrador_consecutivos * 20, 30)
            
            puntuacion_fatiga = float(min(factor_lanzamientos + factor_relevistas + factor_cerrador, 100.0))
            
            return {
                "team_id": team_id,
                "nombre_equipo": nombre_equipo,
                "puntuacion_fatiga": puntuacion_fatiga,
                "total_pitches_3d": total_lanzamientos,
                "relevistas_usados": num_relevistas_activos,
                "dias_consecutivos_cerrador": dias_cerrador_consecutivos
            }
        except Exception as e:
            print(f"❌ Error calculando fatiga del bullpen para {nombre_equipo}: {e}")
            return None
