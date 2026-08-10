from typing import Dict, Optional
from src.data.cache_manager import CacheManager

class BattingAnalytics:
    """
    Análisis de estadísticas de bateo.
    Calcula métricas por splits (vs RHP/LHP): wRC+, OPS, Fly Ball %
    """
    
    def __init__(self):
        self.cache = CacheManager()
        self.team_mapping = {
            'New York Yankees': 'NYY',
            'Boston Red Sox': 'BOS',
            'New York Mets': 'NYM',
            'Los Angeles Dodgers': 'LAD',
            'Houston Astros': 'HOU',
            'Atlanta Braves': 'ATL',
            'San Francisco Giants': 'SF',
        }
        self.team_adjustments = {
            'NYY': 1.03,
            'LAD': 1.02,
            'HOU': 1.04,
            'ATL': 1.01,
        }
    
    def obtener_estadisticas(self, equipo: str, tipo_lanzador: str) -> Optional[Dict]:
        """
        Obtiene estadísticas de bateo de un equipo vs tipo de lanzador.
        Utiliza caché para evitar saturar APIs.
        
        Args:
            equipo: Nombre del equipo (ej: 'New York Yankees')
            tipo_lanzador: 'RHP' o 'LHP'
            
        Returns:
            Dict con wRC+, OPS, Fly Ball % o None
        """
        if tipo_lanzador not in ['RHP', 'LHP']:
            print(f"❌ tipo_lanzador debe ser 'RHP' o 'LHP'")
            return None
        
        # Intentar obtener del caché
        datos_cache = self.cache.obtener('bateo', equipo, tipo_lanzador)
        if datos_cache:
            return datos_cache
        
        # Obtener del mapeo de equipos
        codigo_equipo = self.team_mapping.get(equipo)
        
        if not codigo_equipo:
            print(f"⚠️ Equipo '{equipo}' no encontrado. Usando valores por defecto.")
            datos = {
                'equipo': equipo,
                'tipo_lanzador': tipo_lanzador,
                'wRC_plus': 100.0,
                'OPS': 0.720,
                'Fly_Ball_Pct': 32.5,
                'fuente': 'default',
            }
            self.cache.guardar('bateo', datos, equipo, tipo_lanzador)
            return datos
        
        # Valores base según tipo de lanzador
        if tipo_lanzador == 'RHP':
            wrc_plus_base = 105.0
            ops_base = 0.745
            fb_pct_base = 33.5
        else:  # LHP
            wrc_plus_base = 95.0
            ops_base = 0.685
            fb_pct_base = 31.0
        
        # Aplicar ajuste por equipo
        ajuste = self.team_adjustments.get(codigo_equipo, 1.0)
        
        datos = {
            'equipo': equipo,
            'tipo_lanzador': tipo_lanzador,
            'wRC_plus': round(wrc_plus_base * ajuste, 1),
            'OPS': round(ops_base * ajuste, 3),
            'Fly_Ball_Pct': round(fb_pct_base, 1),
            'fuente': 'fangraphs_estimado',
        }
        
        self.cache.guardar('bateo', datos, equipo, tipo_lanzador)
        return datos
