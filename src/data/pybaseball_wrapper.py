from typing import Optional, Dict
from datetime import datetime

class PyBaseballWrapper:
    """
    Wrapper centralizado para llamadas a pybaseball.
    Simplifica manejo de errores y fallbacks.
    """
    
    @staticmethod
    def obtener_estadisticas_lanzador(nombre_lanzador: str) -> Optional[Dict]:
        """
        Obtiene estadísticas de un lanzador.
        
        Args:
            nombre_lanzador: Nombre del lanzador
            
        Returns:
            Dict con FIP, WAR, K/9, BB/9 o None
        """
        try:
            from pybaseball import pitching_stats
            
            año_actual = datetime.now().year
            pitcher_data = pitching_stats(año_actual, año_actual)
            
            # Búsqueda flexible por apellido
            nombre_limpio = nombre_lanzador.lower().strip()
            coincidencias = pitcher_data[
                pitcher_data['Name'].str.lower().str.contains(nombre_limpio.split()[-1], na=False)
            ]
            
            if coincidencias.empty:
                print(f"⚠️ No encontrado: {nombre_lanzador}")
                return None
            
            stats = coincidencias.iloc[0]
            return {
                'nombre': stats.get('Name', nombre_lanzador),
                'FIP': stats.get('FIP', None),
                'WAR': stats.get('WAR', None),
                'K/9': stats.get('K/9', None),
                'BB/9': stats.get('BB/9', None),
            }
        except Exception as e:
            print(f"❌ Error obteniendo estadísticas: {e}")
            return None
    
    @staticmethod
    def obtener_datos_statcast(fecha_inicio: str, fecha_fin: str, pitcher_id: int):
        """
        Obtiene datos statcast para un lanzador.
        
        Args:
            fecha_inicio: Fecha inicio (YYYY-MM-DD)
            fecha_fin: Fecha fin (YYYY-MM-DD)
            pitcher_id: ID del lanzador
            
        Returns:
            DataFrame con datos statcast
        """
        try:
            from pybaseball import statcast_pitcher
            
            df = statcast_pitcher(fecha_inicio, fecha_fin, pitcher_id)
            if df is None or df.empty:
                print(f"⚠️ Sin datos statcast para pitcher_id={pitcher_id}")
                return None
            
            return df
        except Exception as e:
            print(f"❌ Error obteniendo statcast: {e}")
            return None
