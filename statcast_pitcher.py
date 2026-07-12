import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
import warnings

warnings.filterwarnings('ignore')

class ExtraerStadisticasStatcast:
    """
    Extrae estadísticas avanzadas de física del picheo usando statcast de pybaseball.
    Procesa datos del último mes por tipo de picheo.
    Output: Una fila de DataFrame lista para ML.
    """
    
    def __init__(self, pitcher_id: int, dias_atras: int = 30):
        """
        Inicializa el extractor de estadísticas statcast.
        
        Args:
            pitcher_id: ID del pitcher en MLB Stats API
            dias_atras: Número de días hacia atrás para analizar (default: 30)
        """
        self.pitcher_id = pitcher_id
        self.dias_atras = dias_atras
        
        # Calcular rango de fechas
        hoy = datetime.today()
        hace_n_dias = (hoy - timedelta(days=dias_atras))
        
        self.fecha_inicio = hace_n_dias.strftime('%Y-%m-%d')
        self.fecha_fin = hoy.strftime('%Y-%m-%d')
        
        print(f"📊 Extrayendo datos statcast para pitcher_id={pitcher_id}")
        print(f"   Rango: {self.fecha_inicio} a {self.fecha_fin}")
    
    def obtener_datos_statcast(self) -> Optional[pd.DataFrame]:
        """
        Obtiene datos statcast para el pitcher en el rango de fechas.
        
        Returns:
            DataFrame con datos statcast o None si hay error
        """
        try:
            from pybaseball import statcast_pitcher
            
            print(f"🔍 Consultando statcast_pitcher...")
            
            # Obtener datos de statcast
            df_statcast = statcast_pitcher(self.fecha_inicio, self.fecha_fin, self.pitcher_id)
            
            if df_statcast is None or df_statcast.empty:
                print(f"⚠️ No hay datos statcast para pitcher_id={self.pitcher_id} en el rango especificado")
                return None
            
            print(f"✅ Obtenidos {len(df_statcast)} registros de statcast")
            return df_statcast
            
        except ImportError:
            print(f"❌ Error: pybaseball no está instalado")
            print(f"   Ejecuta: pip install pybaseball")
            return None
        except Exception as e:
            print(f"❌ Error obteniendo datos statcast: {e}")
            return None
    
    def agrupar_por_tipo_picheo(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Agrupa los datos por tipo de picheo.
        
        Args:
            df: DataFrame con datos statcast
            
        Returns:
            Diccionario con {tipo_picheo: DataFrame_filtrado}
        """
        try:
            # Mapeo de tipos de picheo comunes
            tipos_picheo = {
                'Fastball': ['FF', 'FA', 'FT', 'FC'],  # Four-seam, Two-seam
                'Curveball': ['CU', 'CV'],
                'Slider': ['SL', 'SV'],
                'Changeup': ['CH', 'FS'],
                'Splitter': ['SP', 'SF'],
            }
            
            grupos = {}
            
            for nombre, codigos in tipos_picheo.items():
                # Buscar columna de tipo de picheo (puede ser 'pitch_type' o 'pitch_name')
                if 'pitch_type' in df.columns:
                    df_filtered = df[df['pitch_type'].isin(codigos)]
                elif 'pitch_name' in df.columns:
                    df_filtered = df[df['pitch_name'].str.contains(nombre, case=False, na=False)]
                else:
                    continue
                
                if not df_filtered.empty:
                    grupos[nombre] = df_filtered
            
            print(f"✅ Agrupados por tipo de picheo: {list(grupos.keys())}")
            return grupos
            
        except Exception as e:
            print(f"❌ Error agrupando por tipo de picheo: {e}")
            return {}
    
    def calcular_metricas_por_tipo(self, df_grupo: pd.DataFrame, tipo_picheo: str) -> Dict[str, float]:
        """
        Calcula métricas para un tipo de picheo específico.
        
        Args:
            df_grupo: DataFrame filtrado para un tipo de picheo
            tipo_picheo: Nombre del tipo de picheo
            
        Returns:
            Diccionario con métricas (velocidad, rotación, whiff%)
        """
        try:
            metricas = {}
            
            # Velocidad promedio de salida (release_speed)
            if 'release_speed' in df_grupo.columns:
                velocidades = pd.to_numeric(df_grupo['release_speed'], errors='coerce')
                velocidades = velocidades.dropna()
                
                if not velocidades.empty:
                    metricas['release_speed'] = round(velocidades.mean(), 2)
                else:
                    metricas['release_speed'] = 0.0
            else:
                metricas['release_speed'] = 0.0
            
            # Rotación promedio (release_spin_rate)
            if 'release_spin_rate' in df_grupo.columns:
                rotaciones = pd.to_numeric(df_grupo['release_spin_rate'], errors='coerce')
                rotaciones = rotaciones.dropna()
                
                if not rotaciones.empty:
                    metricas['release_spin_rate'] = round(rotaciones.mean(), 0)
                else:
                    metricas['release_spin_rate'] = 0.0
            else:
                metricas['release_spin_rate'] = 0.0
            
            # Porcentaje de strikes abanicados (Whiff %)
            # Whiff = strike sin contacto (swinging_strike)
            if 'description' in df_grupo.columns:
                total_pitches = len(df_grupo)
                whiffs = (df_grupo['description'].str.lower().str.contains('swinging_strike', na=False)).sum()
                
                if total_pitches > 0:
                    metricas['whiff_pct'] = round((whiffs / total_pitches) * 100, 2)
                else:
                    metricas['whiff_pct'] = 0.0
            else:
                metricas['whiff_pct'] = 0.0
            
            # Información adicional
            metricas['num_pitches'] = len(df_grupo)
            
            return metricas
            
        except Exception as e:
            print(f"❌ Error calculando métricas para {tipo_picheo}: {e}")
            return {
                'release_speed': 0.0,
                'release_spin_rate': 0.0,
                'whiff_pct': 0.0,
                'num_pitches': 0
            }
    
    def generar_fila_dataframe(self, todos_grupos: Dict[str, Dict]) -> pd.DataFrame:
        """
        Genera una fila de DataFrame con todas las métricas para todos los tipos de picheo.
        
        Args:
            todos_grupos: Diccionario con métricas de todos los tipos
            
        Returns:
            DataFrame de una sola fila listo para concatenar
        """
        try:
            datos_fila = {
                'pitcher_id': self.pitcher_id,
                'fecha_analisis': datetime.today().strftime('%Y-%m-%d'),
                'periodo_dias': self.dias_atras,
            }
            
            # Agregar métricas por tipo de picheo
            for tipo_picheo, metricas in todos_grupos.items():
                # Normalizar nombre del tipo (para usar como prefijo de columna)
                tipo_normalizado = tipo_picheo.lower().replace(' ', '_')
                
                datos_fila[f'{tipo_normalizado}_speed'] = metricas.get('release_speed', 0.0)
                datos_fila[f'{tipo_normalizado}_spin'] = metricas.get('release_spin_rate', 0.0)
                datos_fila[f'{tipo_normalizado}_whiff_pct'] = metricas.get('whiff_pct', 0.0)
                datos_fila[f'{tipo_normalizado}_num_pitches'] = metricas.get('num_pitches', 0)
            
            # Crear DataFrame de una fila
            df_resultado = pd.DataFrame([datos_fila])
            
            return df_resultado
            
        except Exception as e:
            print(f"❌ Error generando fila de DataFrame: {e}")
            return pd.DataFrame()
    
    def extraer_metricas_completas(self) -> Optional[pd.DataFrame]:
        """
        Función principal orquestadora: obtiene y procesa todos los datos statcast.
        
        Returns:
            DataFrame de una fila con todas las métricas listo para ML
        """
        try:
            # Obtener datos statcast
            df_statcast = self.obtener_datos_statcast()
            if df_statcast is None or df_statcast.empty:
                print(f"⚠️ No se pudieron obtener datos. Retornando DataFrame vacío.")
                return pd.DataFrame()
            
            # Agrupar por tipo de picheo
            grupos = self.agrupar_por_tipo_picheo(df_statcast)
            if not grupos:
                print(f"⚠️ No se encontraron grupos de picheos.")
                return pd.DataFrame()
            
            # Calcular métricas por tipo
            todos_grupos = {}
            for tipo_picheo, df_grupo in grupos.items():
                metricas = self.calcular_metricas_por_tipo(df_grupo, tipo_picheo)
                todos_grupos[tipo_picheo] = metricas
                
                print(f"   {tipo_picheo}: {metricas}")
            
            # Generar fila de DataFrame
            df_resultado = self.generar_fila_dataframe(todos_grupos)
            
            if not df_resultado.empty:
                print(f"\n✅ Estadísticas generadas exitosamente")
                print(f"   Columnas: {df_resultado.columns.tolist()}")
                return df_resultado
            else:
                return pd.DataFrame()
            
        except Exception as e:
            print(f"❌ Error en extracción completa: {e}")
            return pd.DataFrame()

def extraer_estadisticas_pitcher_statcast(pitcher_id: int, dias_atras: int = 30) -> Optional[pd.DataFrame]:
    """
    Función principal para extraer estadísticas de física del picheo.
    
    Args:
        pitcher_id: ID del pitcher en MLB Stats API
        dias_atras: Número de días hacia atrás (default: 30)
        
    Returns:
        DataFrame de una fila con métricas statcast listo para ML
    """
    extractor = ExtraerStadisticasStatcast(pitcher_id, dias_atras)
    return extractor.extraer_metricas_completas()

if __name__ == "__main__":
    # Ejemplo de uso
    print("=== Extracción de Estadísticas Statcast de Pitcher ===\n")
    
    # Ejemplo: Gerrit Cole (ID: 543037)
    pitcher_id = 543037
    
    df_resultado = extraer_estadisticas_pitcher_statcast(pitcher_id, dias_atras=30)
    
    if not df_resultado.empty:
        print("\n📊 Resultado final (1 fila):")
        print(df_resultado)
        print(f"\nForma: {df_resultado.shape}")
        print(f"Tipos de datos:\n{df_resultado.dtypes}")
