from typing import Dict, Optional
from src.data.mlb_api_client import MLBStatsAPIClient
from src.data.pybaseball_wrapper import PyBaseballWrapper

class PitcherAnalytics:
    """
    Análisis de estadísticas de lanzadores.
    Calcula métricas avanzadas: FIP, WAR, K/9, BB/9
    """
    
    def __init__(self):
        self.api = MLBStatsAPIClient()
        self.defaults = {
            'FIP': 4.0,
            'WAR': 0.0,
            'K/9': 8.0,
            'BB/9': 3.0
        }
    
    def obtener_lanzadores_juego(self, game_pk: int) -> tuple:
        """
        Obtiene los lanzadores abridores de un juego.
        
        Args:
            game_pk: ID del juego
            
        Returns:
            Tupla (lanzador_visitante, lanzador_local)
        """
        try:
            juego = self.api.get_game(game_pk)
            if not juego:
                return None, None
            
            away_pitcher = juego.get('gameData', {}).get('probablePitchers', {}).get('away')
            home_pitcher = juego.get('gameData', {}).get('probablePitchers', {}).get('home')
            
            return away_pitcher, home_pitcher
        except Exception as e:
            print(f"❌ Error obteniendo lanzadores: {e}")
            return None, None
    
    def obtener_estadisticas(self, nombre_lanzador: str) -> Optional[Dict]:
        """
        Obtiene estadísticas de un lanzador vía pybaseball.
        
        Args:
            nombre_lanzador: Nombre completo
            
        Returns:
            Dict con FIP, WAR, K/9, BB/9
        """
        return PyBaseballWrapper.obtener_estadisticas_lanzador(nombre_lanzador)
    
    def calcular_delta(self, stats_visitante: Optional[Dict], stats_local: Optional[Dict]) -> Dict:
        """
        Calcula las diferencias (Δ) de métricas entre lanzadores.
        Diferencia = Local menos Visitante (positivo = ventaja local).
        
        Args:
            stats_visitante: Estadísticas del lanzador visitante
            stats_local: Estadísticas del lanzador local
            
        Returns:
            Dict con delta_FIP, delta_WAR, delta_K9, delta_BB9
        """
        # Extraer valores con defaults
        stats_v = {
            'FIP': stats_visitante.get('FIP', self.defaults['FIP']) if stats_visitante else self.defaults['FIP'],
            'WAR': stats_visitante.get('WAR', self.defaults['WAR']) if stats_visitante else self.defaults['WAR'],
            'K/9': stats_visitante.get('K/9', self.defaults['K/9']) if stats_visitante else self.defaults['K/9'],
            'BB/9': stats_visitante.get('BB/9', self.defaults['BB/9']) if stats_visitante else self.defaults['BB/9'],
        }
        
        stats_l = {
            'FIP': stats_local.get('FIP', self.defaults['FIP']) if stats_local else self.defaults['FIP'],
            'WAR': stats_local.get('WAR', self.defaults['WAR']) if stats_local else self.defaults['WAR'],
            'K/9': stats_local.get('K/9', self.defaults['K/9']) if stats_local else self.defaults['K/9'],
            'BB/9': stats_local.get('BB/9', self.defaults['BB/9']) if stats_local else self.defaults['BB/9'],
        }
        
        # Cálculos: positivo = ventaja local
        return {
            'delta_FIP': stats_v['FIP'] - stats_l['FIP'],  # Menor FIP es mejor
            'delta_WAR': stats_l['WAR'] - stats_v['WAR'],  # Mayor WAR es mejor
            'delta_K9': stats_l['K/9'] - stats_v['K/9'],   # Mayor K/9 es mejor
            'delta_BB9': stats_v['BB/9'] - stats_l['BB/9'], # Menor BB/9 es mejor
        }
    
    def analizar_juego(self, game_pk: int) -> Dict:
        """
        Análisis completo de lanzadores para un juego.
        
        Args:
            game_pk: ID del juego
            
        Returns:
            Dict con todos los deltas y nombres
        """
        try:
            away_pitcher, home_pitcher = self.obtener_lanzadores_juego(game_pk)
            
            if not away_pitcher or not home_pitcher:
                return {
                    'game_pk': game_pk,
                    'error': 'Lanzadores no disponibles',
                    'delta_FIP': 0.0,
                    'delta_WAR': 0.0,
                    'delta_K9': 0.0,
                    'delta_BB9': 0.0,
                }
            
            nombre_away = away_pitcher.get('person', {}).get('fullName', 'Unknown')
            nombre_home = home_pitcher.get('person', {}).get('fullName', 'Unknown')
            
            stats_away = self.obtener_estadisticas(nombre_away)
            stats_home = self.obtener_estadisticas(nombre_home)
            
            deltas = self.calcular_delta(stats_away, stats_home)
            
            return {
                'game_pk': game_pk,
                'pitcher_away': nombre_away,
                'pitcher_home': nombre_home,
                'stats_away': stats_away,
                'stats_home': stats_home,
                **deltas
            }
        except Exception as e:
            print(f"❌ Error analizando juego: {e}")
            return {
                'game_pk': game_pk,
                'error': str(e),
                'delta_FIP': 0.0,
                'delta_WAR': 0.0,
                'delta_K9': 0.0,
                'delta_BB9': 0.0,
            }
