from typing import Dict
from datetime import datetime, timedelta
from src.data.mlb_api_client import MLBStatsAPIClient
from src.data.cache_manager import CacheManager

class BullpenAnalytics:
    """
    Análisis de fatiga del bullpen.
    Calcula métrica 0-100 basada en:
    - Volumen de lanzamientos en 3 días
    - Distribución entre relevistas
    - Días consecutivos del cerrador
    """
    
    def __init__(self):
        self.api = MLBStatsAPIClient()
        self.cache = CacheManager()
    
    def obtener_juegos_3dias(self, team_id: int) -> list:
        """
        Obtiene juegos del equipo en los últimos 3 días.
        
        Args:
            team_id: ID del equipo en MLB Stats API
            
        Returns:
            Lista de game_pk
        """
        try:
            hoy = datetime.today()
            hace_3_dias = (hoy - timedelta(days=3)).strftime('%Y-%m-%d')
            hoy_str = hoy.strftime('%Y-%m-%d')
            
            juegos = self.api.get_team_schedule(team_id, hace_3_dias, hoy_str)
            game_pks = [
                juego['gamePk'] for juego in juegos
                if juego.get('status', {}).get('abstractGameState') in ['Final', 'Completed']
            ]
            
            print(f"✅ Encontrados {len(game_pks)} juegos en 3 días")
            return game_pks
        except Exception as e:
            print(f"❌ Error obteniendo juegos: {e}")
            return []
    
    def extraer_relevistas(self, boxscore: Dict, team_id: int) -> Dict[str, int]:
        """
        Extrae relevistas y su cuenta de lanzamientos del boxscore.
        
        Args:
            boxscore: Diccionario del boxscore
            team_id: ID del equipo
            
        Returns:
            Dict {nombre_pitcher: pitch_count}
        """
        try:
            home_id = boxscore['teams']['home']['team']['id']
            team_key = 'home' if home_id == team_id else 'away'
            pitchers = boxscore['teams'][team_key]['pitchers']
            
            relevistas = {}
            for pitcher_id in pitchers:
                pitcher_data = boxscore['teams'][team_key]['players'][f'ID{pitcher_id}']
                pitch_count = pitcher_data.get('stats', {}).get('pitching', {}).get('numberOfPitches', 0)
                
                if pitch_count > 0:
                    nombre = pitcher_data['person']['fullName']
                    relevistas[nombre] = pitch_count
            
            return relevistas
        except Exception as e:
            print(f"⚠️ Error extrayendo relevistas: {e}")
            return {}
    
    def calcular_fatiga(self, team_id: int, nombre_equipo: str) -> Dict:
        """
        Calcula puntuación de fatiga del bullpen (0-100).
        
        Métrica de Fatiga:
        - 0-30: Descansado 🟢
        - 30-60: Normal 🟡
        - 60-80: Fatigado 🟠
        - 80-100: Muy fatigado 🔴
        
        Args:
            team_id: ID del equipo
            nombre_equipo: Nombre del equipo
            
        Returns:
            Dict con puntuación y métricas
        """
        try:
            print(f"🔍 Analizando fatiga del bullpen para {nombre_equipo}...")
            
            # Intentar caché primero
            datos_cache = self.cache.obtener('bullpen', nombre_equipo)
            if datos_cache:
                return datos_cache
            
            game_pks = self.obtener_juegos_3dias(team_id)
            if not game_pks:
                return self._resultado_default(nombre_equipo)
            
            lanzamientos_relevistas = {}
            dias_cerrador = {}
            
            for game_pk in game_pks:
                boxscore = self.api.get_boxscore(game_pk)
                if not boxscore:
                    continue
                
                relevistas = self.extraer_relevistas(boxscore, team_id)
                for pitcher, count in relevistas.items():
                    lanzamientos_relevistas[pitcher] = lanzamientos_relevistas.get(pitcher, 0) + count
            
            # Cálculos de fatiga
            total_lanzamientos = sum(lanzamientos_relevistas.values())
            num_relevistas = len(lanzamientos_relevistas)
            
            # Factor 1: Volumen (1200 es normal)
            fatiga_volumen = min(100, (total_lanzamientos / 1200) * 100)
            
            # Factor 2: Distribución (ideal: 8-12 relevistas)
            if num_relevistas < 5:
                fatiga_dist = 40
            elif num_relevistas < 8:
                fatiga_dist = 20
            elif num_relevistas <= 15:
                fatiga_dist = 0
            else:
                fatiga_dist = 15
            
            # Factor 3: Cerrador (>2 días consecutivos = fatiga)
            fatiga_cerrador = 0  # Simplificado en esta versión
            
            # Promedio ponderado
            puntuacion = (
                fatiga_volumen * 0.40 +
                fatiga_dist * 0.35 +
                fatiga_cerrador * 0.25
            )
            puntuacion = round(min(100, max(0, puntuacion)), 1)
            
            # Clasificación
            if puntuacion < 30:
                clasificacion = "Descansado 🟢"
            elif puntuacion < 60:
                clasificacion = "Normal 🟡"
            elif puntuacion < 80:
                clasificacion = "Fatigado 🟠"
            else:
                clasificacion = "Muy fatigado 🔴"
            
            resultado = {
                'equipo': nombre_equipo,
                'team_id': team_id,
                'puntuacion_fatiga': puntuacion,
                'clasificacion': clasificacion,
                'total_lanzamientos_3dias': total_lanzamientos,
                'num_relevistas_activos': num_relevistas,
                'timestamp': datetime.now().isoformat()
            }
            
            self.cache.guardar('bullpen', resultado, nombre_equipo)
            return resultado
        except Exception as e:
            print(f"❌ Error calculando fatiga: {e}")
            return self._resultado_default(nombre_equipo)
    
    def _resultado_default(self, nombre_equipo: str) -> Dict:
        """Retorna resultado por defecto en caso de error."""
        return {
            'equipo': nombre_equipo,
            'puntuacion_fatiga': 50.0,
            'clasificacion': 'Normal 🟡',
            'total_lanzamientos_3dias': 0,
            'num_relevistas_activos': 0,
            'error': 'No se pudo calcular',
            'timestamp': datetime.now().isoformat()
        }
