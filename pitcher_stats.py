import requests
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, Tuple

def obtener_lanzadores_abridores(game_pk: int) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Consulta la MLB Stats API para obtener los lanzadores abridores de un juego.
    
    Args:
        game_pk: ID único del juego en la MLB Stats API
        
    Returns:
        Tupla con diccionarios de lanzador local y visitante (None si no hay datos)
    """
    try:
        url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}"
        response = requests.get(url)
        response.raise_for_status()
        juego_data = response.json()
        
        # Extraer lanzadores probables
        home_pitcher = juego_data.get('gameData', {}).get('probablePitchers', {}).get('home')
        away_pitcher = juego_data.get('gameData', {}).get('probablePitchers', {}).get('away')
        
        return away_pitcher, home_pitcher
    except Exception as e:
        print(f"Error obteniendo lanzadores abridores para game_pk {game_pk}: {e}")
        return None, None

def obtener_estadisticas_lanzador_pybaseball(nombre_lanzador: str) -> Optional[Dict]:
    """
    Busca las estadísticas del lanzador en pybaseball para la temporada actual.
    Maneja excepciones si el pitcher es novato o no tiene datos disponibles.
    
    Args:
        nombre_lanzador: Nombre completo del lanzador
        
    Returns:
        Diccionario con estadísticas o None si no se encuentran
    """
    try:
        # Importar pybaseball
        from pybaseball import playerid_lookup, pitching_stats
        
        # Buscar el ID del lanzador
        año_actual = datetime.now().year
        
        # Intentar buscar en la base de datos de pybaseball
        # Para esto usamos pitcher_stats que obtiene datos de FanGraphs
        pitcher_data = pitching_stats(año_actual, año_actual)
        
        # Filtrar por nombre (búsqueda flexible para manejar variaciones de nombres)
        nombre_limpio = nombre_lanzador.lower().strip()
        coincidencias = pitcher_data[
            pitcher_data['Name'].str.lower().str.contains(nombre_limpio.split()[-1], na=False)
        ]
        
        if coincidencias.empty:
            print(f"No se encontraron datos para {nombre_lanzador}")
            return None
        
        # Tomar el primer resultado (mejor coincidencia)
        stats = coincidencias.iloc[0]
        
        return {
            'nombre': stats.get('Name', nombre_lanzador),
            'FIP': stats.get('FIP', None),
            'WAR': stats.get('WAR', None),
            'K/9': stats.get('K/9', None),
            'BB/9': stats.get('BB/9', None),
        }
    except Exception as e:
        print(f"Error obteniendo estadísticas de pybaseball para {nombre_lanzador}: {e}")
        return None

def calcular_diferencia_lanzadores(stats_visitante: Optional[Dict], 
                                   stats_local: Optional[Dict]) -> Dict:
    """
    Calcula las diferencias (Δ) de métricas avanzadas entre lanzadores.
    Diferencia = Local menos Visitante
    
    Args:
        stats_visitante: Diccionario con estadísticas del lanzador visitante
        stats_local: Diccionario con estadísticas del lanzador local
        
    Returns:
        Diccionario con diferencias de métricas
    """
    # Definir valores por defecto para novatos/sin datos
    valores_default = {
        'FIP': 4.0,
        'WAR': 0.0,
        'K/9': 8.0,
        'BB/9': 3.0
    }
    
    # Extraer valores, usando defaults si no existen
    stats_v = {
        'FIP': stats_visitante.get('FIP', valores_default['FIP']) if stats_visitante else valores_default['FIP'],
        'WAR': stats_visitante.get('WAR', valores_default['WAR']) if stats_visitante else valores_default['WAR'],
        'K/9': stats_visitante.get('K/9', valores_default['K/9']) if stats_visitante else valores_default['K/9'],
        'BB/9': stats_visitante.get('BB/9', valores_default['BB/9']) if stats_visitante else valores_default['BB/9'],
    }
    
    stats_l = {
        'FIP': stats_local.get('FIP', valores_default['FIP']) if stats_local else valores_default['FIP'],
        'WAR': stats_local.get('WAR', valores_default['WAR']) if stats_local else valores_default['WAR'],
        'K/9': stats_local.get('K/9', valores_default['K/9']) if stats_local else valores_default['K/9'],
        'BB/9': stats_local.get('BB/9', valores_default['BB/9']) if stats_local else valores_default['BB/9'],
    }
    
    # Calcular diferencias (Local - Visitante)
    # FIP menor es mejor para el lanzador
    # WAR mayor es mejor
    # K/9 mayor es mejor (más ponches)
    # BB/9 menor es mejor (menos bases por bola)
    
    diferencias = {
        'delta_FIP': stats_v['FIP'] - stats_l['FIP'],  # Positivo = ventaja local (local tiene menor FIP)
        'delta_WAR': stats_l['WAR'] - stats_v['WAR'],  # Positivo = ventaja local
        'delta_K9': stats_l['K/9'] - stats_v['K/9'],  # Positivo = ventaja local
        'delta_BB9': stats_v['BB/9'] - stats_l['BB/9'],  # Positivo = ventaja local
    }
    
    return diferencias

def extraer_metricas_lanzadores(game_pk: int) -> Dict:
    """
    Función principal que orquesta todo el proceso de extracción de métricas
    de lanzadores abridores y calcula sus diferencias.
    
    Args:
        game_pk: ID único del juego en la MLB Stats API
        
    Returns:
        Diccionario completo con estadísticas y diferencias
    """
    try:
        print(f"Procesando juego {game_pk}...")
        
        # Obtener lanzadores
        away_pitcher, home_pitcher = obtener_lanzadores_abridores(game_pk)
        
        if not away_pitcher or not home_pitcher:
            print(f"No se pudieron obtener los lanzadores para el juego {game_pk}")
            return {
                'game_pk': game_pk,
                'error': 'Lanzadores no disponibles',
                'delta_FIP': 0.0,
                'delta_WAR': 0.0,
                'delta_K9': 0.0,
                'delta_BB9': 0.0,
            }
        
        nombre_away = away_pitcher.get('person', {}).get('fullName', 'Desconocido')
        nombre_home = home_pitcher.get('person', {}).get('fullName', 'Desconocido')
        
        print(f"  Visitante: {nombre_away}")
        print(f"  Local: {nombre_home}")
        
        # Obtener estadísticas
        stats_away = obtener_estadisticas_lanzador_pybaseball(nombre_away)
        stats_home = obtener_estadisticas_lanzador_pybaseball(nombre_home)
        
        # Calcular diferencias
        diferencias = calcular_diferencia_lanzadores(stats_away, stats_home)
        
        resultado = {
            'game_pk': game_pk,
            'pitcher_away': nombre_away,
            'pitcher_home': nombre_home,
            'stats_away': stats_away,
            'stats_home': stats_home,
            'delta_FIP': diferencias['delta_FIP'],
            'delta_WAR': diferencias['delta_WAR'],
            'delta_K9': diferencias['delta_K9'],
            'delta_BB9': diferencias['delta_BB9'],
        }
        
        return resultado
        
    except Exception as e:
        print(f"Error procesando juego {game_pk}: {e}")
        return {
            'game_pk': game_pk,
            'error': str(e),
            'delta_FIP': 0.0,
            'delta_WAR': 0.0,
            'delta_K9': 0.0,
            'delta_BB9': 0.0,
        }

if __name__ == "__main__":
    # Ejemplo de uso: procesar un juego reciente
    # Nota: Reemplaza este ID con un game_pk real
    test_game_pk = 746345  # Ejemplo
    
    resultado = extraer_metricas_lanzadores(test_game_pk)
    print("\n=== Resultado ===")
    for key, value in resultado.items():
        print(f"{key}: {value}")
