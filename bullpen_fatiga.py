import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import json
import os

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
        self.url_base_mlb = "https://statsapi.mlb.com/api/v1"
        
        # Crear directorio de caché si no existe
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
    
    def obtener_juegos_equipo_3dias(self, team_id: int) -> list:
        """
        Obtiene los juegos de un equipo en los últimos 3 días.
        
        Args:
            team_id: ID del equipo en MLB Stats API
            
        Returns:
            Lista de game_pk (IDs de juegos)
        """
        try:
            hoy = datetime.today()
            hace_3_dias = (hoy - timedelta(days=3)).strftime('%Y-%m-%d')
            hoy_str = hoy.strftime('%Y-%m-%d')
            
            url = f"{self.url_base_mlb}/schedule?sportId=1&teamId={team_id}&startDate={hace_3_dias}&endDate={hoy_str}"
            response = requests.get(url)
            response.raise_for_status()
            
            juegos = response.json()
            game_pks = [juego['gamePk'] for juego in juegos if juego.get('status', {}).get('abstractGameState') in ['Final', 'Completed']]
            
            print(f"✅ Encontrados {len(game_pks)} juegos en los últimos 3 días para team_id={team_id}")
            return game_pks
            
        except Exception as e:
            print(f"❌ Error obteniendo juegos del equipo: {e}")
            return []
    
    def obtener_boxscore_juego(self, game_pk: int) -> Optional[Dict]:
        """
        Obtiene el boxscore completo de un juego.
        
        Args:
            game_pk: ID del juego
            
        Returns:
            Diccionario con datos del boxscore
        """
        try:
            url = f"{self.url_base_mlb}/game/{game_pk}/boxscore"
            response = requests.get(url)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            print(f"⚠️ Error obteniendo boxscore para game_pk {game_pk}: {e}")
            return None
    
    def extraer_relevistas_juego(self, boxscore: Dict, team_id: int) -> Dict[str, int]:
        """
        Extrae los relevistas y su cuenta de lanzamientos de un juego.
        
        Args:
            boxscore: Diccionario del boxscore
            team_id: ID del equipo
            
        Returns:
            Diccionario con {nombre_pitcher: pitch_count}
        """
        relevistas = {}
        
        try:
            # Determinar si el equipo es home o away
            home_id = boxscore['teams']['home']['team']['id']
            away_id = boxscore['teams']['away']['team']['id']
            
            team_key = 'home' if home_id == team_id else 'away'
            pitchers = boxscore['teams'][team_key]['pitchers']
            
            # Obtener lista de lanzadores del equipo
            for pitcher_id in pitchers:
                pitcher_data = boxscore['teams'][team_key]['players'][f'ID{pitcher_id}']
                
                # Verificar si lanzó (stats.pitching.numberOfPitches > 0)
                if pitcher_data.get('stats', {}).get('pitching', {}).get('numberOfPitches', 0) > 0:
                    nombre = pitcher_data['person']['fullName']
                    pitch_count = pitcher_data['stats']['pitching']['numberOfPitches']
                    relevistas[nombre] = pitch_count
            
            return relevistas
            
        except Exception as e:
            print(f"⚠️ Error extrayendo relevistas del boxscore: {e}")
            return {}
    
    def identificar_cerrador(self, boxscore: Dict, team_id: int) -> Optional[str]:
        """
        Identifica al cerrador (último pitcher en lanzar) del equipo.
        
        Args:
            boxscore: Diccionario del boxscore
            team_id: ID del equipo
            
        Returns:
            Nombre del cerrador o None
        """
        try:
            home_id = boxscore['teams']['home']['team']['id']
            team_key = 'home' if home_id == team_id else 'away'
            
            pitchers = boxscore['teams'][team_key]['pitchers']
            
            if not pitchers:
                return None
            
            # El último pitcher en la lista es típicamente el cerrador o último relevista
            ultimo_pitcher_id = pitchers[-1]
            ultimo_pitcher = boxscore['teams'][team_key]['players'][f'ID{ultimo_pitcher_id}']
            
            # Verificar que realmente lanzó
            if ultimo_pitcher.get('stats', {}).get('pitching', {}).get('numberOfPitches', 0) > 0:
                return ultimo_pitcher['person']['fullName']
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error identificando cerrador: {e}")
            return None
    
    def calcular_fatiga_bullpen(self, team_id: int, nombre_equipo: str) -> Dict:
        """
        Calcula la métrica de fatiga del bullpen para un equipo.
        
        Métrica de Fatiga (0-100):
        - 0-30: Bullpen descansado y fresco
        - 30-60: Bullpen normal
        - 60-80: Bullpen fatigado
        - 80-100: Bullpen muy fatigado (alto riesgo)
        
        Args:
            team_id: ID del equipo
            nombre_equipo: Nombre del equipo
            
        Returns:
            Diccionario con métricas de fatiga
        """
        
        try:
            print(f"\n🔍 Analizando fatiga del bullpen para {nombre_equipo}...")
            
            # Obtener juegos de los últimos 3 días
            game_pks = self.obtener_juegos_equipo_3dias(team_id)
            
            if not game_pks:
                print(f"⚠️ No hay juegos recientes para {nombre_equipo}")
                return self._resultado_defecto(nombre_equipo)
            
            # Acumular lanzamientos por relevista
            lanzamientos_relevistas = {}
            dias_consecutivos_cerrador = {}
            
            for game_pk in game_pks:
                boxscore = self.obtener_boxscore_juego(game_pk)
                if not boxscore:
                    continue
                
                # Extraer relevistas
                relevistas = self.extraer_relevistas_juego(boxscore, team_id)
                for pitcher, pitch_count in relevistas.items():
                    if pitcher not in lanzamientos_relevistas:
                        lanzamientos_relevistas[pitcher] = 0
                    lanzamientos_relevistas[pitcher] += pitch_count
                
                # Identificar cerrador
                cerrador = self.identificar_cerrador(boxscore, team_id)
                if cerrador:
                    if cerrador not in dias_consecutivos_cerrador:
                        dias_consecutivos_cerrador[cerrador] = 0
                    dias_consecutivos_cerrador[cerrador] += 1
            
            # Calcular métricas
            total_lanzamientos = sum(lanzamientos_relevistas.values())
            num_relevistas_activos = len(lanzamientos_relevistas)
            
            # Cerrador más usado
            cerrador_principal = max(dias_consecutivos_cerrador.items(), key=lambda x: x[1])[0] if dias_consecutivos_cerrador else "Desconocido"
            dias_cerrador_consecutivos = max(dias_consecutivos_cerrador.values()) if dias_consecutivos_cerrador else 0
            
            # CÁLCULO DE FATIGA (0-100)
            # Factores:
            # 1. Lanzamientos totales en 3 días (target: 1000-1200 es normal)
            # 2. Distribución entre relevistas (muchos relevistas = menos fatiga)
            # 3. Días consecutivos del cerrador (>2 días = fatiga)
            
            # Factor 1: Lanzamientos totales
            fatiga_lanzamientos = min(100, (total_lanzamientos / 1200) * 100)
            
            # Factor 2: Distribución (si hay pocos relevistas = más fatiga)
            # Ideal: 8-12 relevistas. Menos de 5 o más de 15 = problema
            if num_relevistas_activos < 5:
                fatiga_distribucion = 40
            elif num_relevistas_activos < 8:
                fatiga_distribucion = 20
            elif num_relevistas_activos <= 15:
                fatiga_distribucion = 0
            else:
                fatiga_distribucion = 15
            
            # Factor 3: Días consecutivos del cerrador
            # 0 días: 0 fatiga
            # 1 día: 10 fatiga
            # 2 días: 25 fatiga
            # 3 días: 50 fatiga
            fatiga_cerrador = [0, 10, 25, 50][min(dias_cerrador_consecutivos, 3)]
            
            # Promedio ponderado
            puntuacion_fatiga = (
                fatiga_lanzamientos * 0.40 +  # 40% por volumen total
                fatiga_distribucion * 0.35 +   # 35% por distribución
                fatiga_cerrador * 0.25          # 25% por intensidad del closer
            )
            
            puntuacion_fatiga = round(min(100, max(0, puntuacion_fatiga)), 1)
            
            # Clasificación
            if puntuacion_fatiga < 30:
                clasificacion = "Descansado 🟢"
            elif puntuacion_fatiga < 60:
                clasificacion = "Normal 🟡"
            elif puntuacion_fatiga < 80:
                clasificacion = "Fatigado 🟠"
            else:
                clasificacion = "Muy fatigado 🔴"
            
            resultado = {
                'equipo': nombre_equipo,
                'team_id': team_id,
                'puntuacion_fatiga': puntuacion_fatiga,
                'clasificacion': clasificacion,
                'total_lanzamientos_3dias': total_lanzamientos,
                'num_relevistas_activos': num_relevistas_activos,
                'cerrador_principal': cerrador_principal,
                'dias_consecutivos_cerrador': dias_cerrador_consecutivos,
                'lanzamientos_por_relevista': dict(sorted(lanzamientos_relevistas.items(), key=lambda x: x[1], reverse=True)),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n📊 Resultados para {nombre_equipo}:")
            print(f"   Puntuación de Fatiga: {puntuacion_fatiga}/100 ({clasificacion})")
            print(f"   Total de lanzamientos (3 días): {total_lanzamientos}")
            print(f"   Relevistas activos: {num_relevistas_activos}")
            print(f"   Cerrador: {cerrador_principal} ({dias_cerrador_consecutivos} días consecutivos)")
            
            return resultado
            
        except Exception as e:
            print(f"❌ Error calculando fatiga del bullpen: {e}")
            return self._resultado_defecto(nombre_equipo)
    
    def _resultado_defecto(self, nombre_equipo: str) -> Dict:
        """Retorna un resultado por defecto cuando hay error."""
        return {
            'equipo': nombre_equipo,
            'puntuacion_fatiga': 50.0,  # Neutral
            'clasificacion': 'Normal 🟡',
            'total_lanzamientos_3dias': 0,
            'num_relevistas_activos': 0,
            'cerrador_principal': 'Desconocido',
            'dias_consecutivos_cerrador': 0,
            'lanzamientos_por_relevista': {},
            'error': 'No se pudo calcular',
            'timestamp': datetime.now().isoformat()
        }

def extraer_fatiga_bullpen(team_id: int, nombre_equipo: str) -> Dict:
    """
    Función principal para extraer métrica de fatiga del bullpen.
    
    Args:
        team_id: ID del equipo en MLB Stats API
        nombre_equipo: Nombre del equipo
        
    Returns:
        Diccionario con puntuación de fatiga (0-100) lista para XGBoost
    """
    gestor = GestorFatigaBullpen()
    return gestor.calcular_fatiga_bullpen(team_id, nombre_equipo)

def mapeo_team_id_nombres() -> Dict[str, int]:
    """
    Mapeo de nombres de equipos a IDs de MLB Stats API.
    """
    return {
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

if __name__ == "__main__":
    # Ejemplo de uso
    print("=== Análisis de Fatiga del Bullpen ===\n")
    
    # Equipos de prueba
    equipos_prueba = [
        ('New York Yankees', 147),
        ('Los Angeles Dodgers', 119),
        ('Houston Astros', 117),
    ]
    
    for nombre_equipo, team_id in equipos_prueba:
        resultado = extraer_fatiga_bullpen(team_id, nombre_equipo)
        print(f"\n{'='*50}")
        print(f"Equipo: {resultado['equipo']}")
        print(f"Fatiga: {resultado['puntuacion_fatiga']}/100 - {resultado['clasificacion']}")
        print(f"Top relevistas: {list(resultado['lanzamientos_por_relevista'].keys())[:3]}")
