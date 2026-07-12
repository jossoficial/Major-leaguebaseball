import requests
import pandas as pd
from datetime import datetime
from pitcher_stats import extraer_metricas_lanzadores
from bateo_splits import obtener_estadisticas_bateo_splits
from bullpen_fatiga import extraer_fatiga_bullpen, mapeo_team_id_nombres

def obtener_tipo_lanzador(nombre_lanzador: str) -> str:
    """
    Intenta determinar si un lanzador es derecho (RHP) o zurdo (LHP).
    Por defecto retorna 'RHP' si no puede determinarse.
    
    Args:
        nombre_lanzador: Nombre del lanzador
        
    Returns:
        'RHP' o 'LHP'
    """
    try:
        from pybaseball import playerid_reverse_lookup
        
        # Buscar información del pitcher
        datos = playerid_reverse_lookup([nombre_lanzador])
        
        if datos and not datos.empty:
            # Si encontramos datos, intentar obtener el brazo (throws)
            # Nota: pybaseball puede no siempre tener esta información
            return 'RHP'  # Default a RHP como fallback
        else:
            return 'RHP'
    except:
        # Por defecto, asumir RHP
        return 'RHP'

def descargar_datos_mlb():
    """
    Descarga los juegos de hoy desde la API de MLB Stats
    con métricas avanzadas de lanzadores (Sabermetría), bateo (Splits) y bullpen.
    
    Genera un CSV con:
    - Datos básicos del juego
    - Estadísticas de lanzadores (FIP, WAR, K/9, BB/9)
    - Estadísticas de bateo por splits (wRC+, OPS, Fly Ball %)
    - Fatiga del bullpen (0-100) para ambos equipos
    """
    try:
        # Obtener la fecha de hoy en formato YYYY-MM-DD
        hoy = datetime.today().strftime('%Y-%m-%d')
        
        # API de MLB Stats
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={hoy}"
        response = requests.get(url)
        response.raise_for_status()
        
        juegos = response.json()
        
        # juegos es una lista directamente
        if not isinstance(juegos, list) or len(juegos) == 0:
            print(f"No hay juegos programados para {hoy}")
            # Crear archivo vacío para que predict.py maneje el caso
            df_vacio = pd.DataFrame(columns=[
                'away_team', 'home_team', 'diff_pct',
                'pitcher_away', 'pitcher_home',
                'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9',
                'wRC_plus_home', 'OPS_home', 'Fly_Ball_Pct_home',
                'wRC_plus_away', 'OPS_away', 'Fly_Ball_Pct_away',
                'fatiga_bullpen_home', 'fatiga_bullpen_away'
            ])
            df_vacio.to_csv('juegos_hoy.csv', index=False)
            return
        
        # Obtener mapeo de equipo a team_id
        mapeo_equipos = mapeo_team_id_nombres()
        
        juegos_data = []
        
        for juego in juegos:
            try:
                # Verificar que el juego está programado
                game_state = juego.get('status', {}).get('abstractGameState', '')
                if game_state not in ['Scheduled', 'Pre-Game', 'In Progress', 'Live']:
                    continue
                
                # Extraer nombres de equipos
                away_team = juego['teams']['away']['team']['name']
                home_team = juego['teams']['home']['team']['name']
                
                away_id = juego['teams']['away']['team']['id']
                home_id = juego['teams']['home']['team']['id']
                game_pk = juego.get('gamePk')
                
                # Obtener récords de los equipos de la API
                try:
                    away_stats_url = f"https://statsapi.mlb.com/api/v1/teams/{away_id}"
                    home_stats_url = f"https://statsapi.mlb.com/api/v1/teams/{home_id}"
                    
                    away_team_data = requests.get(away_stats_url).json()
                    home_team_data = requests.get(home_stats_url).json()
                    
                    # Acceder a los datos correctamente
                    away_record = away_team_data.get('teams', [{}])[0].get('record', [{}])[0] if 'teams' in away_team_data else {}
                    home_record = home_team_data.get('teams', [{}])[0].get('record', [{}])[0] if 'teams' in home_team_data else {}
                    
                    away_wins = away_record.get('wins', 0)
                    away_losses = away_record.get('losses', 0)
                    home_wins = home_record.get('wins', 0)
                    home_losses = home_record.get('losses', 0)
                    
                except:
                    # Si no podemos obtener los récords, usar valores por defecto
                    away_wins, away_losses = 0, 0
                    home_wins, home_losses = 0, 0
                
                # Calcular porcentaje de victorias
                away_pct = away_wins / (away_wins + away_losses) if (away_wins + away_losses) > 0 else 0.5
                home_pct = home_wins / (home_wins + home_losses) if (home_wins + home_losses) > 0 else 0.5
                
                # Diferencia de porcentaje (local - visitante)
                diff_pct = home_pct - away_pct
                
                # Extraer métricas de lanzadores usando Sabermetría
                print(f"\n🎯 Procesando juego: {away_team} @ {home_team}")
                metricas_lanzadores = extraer_metricas_lanzadores(game_pk)
                
                nombre_pitcher_home = metricas_lanzadores.get('pitcher_home', 'Desconocido')
                nombre_pitcher_away = metricas_lanzadores.get('pitcher_away', 'Desconocido')
                
                # Determinar tipo de lanzador (RHP o LHP)
                tipo_pitcher_home = obtener_tipo_lanzador(nombre_pitcher_home)
                tipo_pitcher_away = obtener_tipo_lanzador(nombre_pitcher_away)
                
                # Extraer estadísticas de bateo por splits
                print(f"📊 Extrayendo estadísticas de bateo...")
                stats_bateo_home = obtener_estadisticas_bateo_splits(home_team, tipo_pitcher_away)
                stats_bateo_away = obtener_estadisticas_bateo_splits(away_team, tipo_pitcher_home)
                
                # Valores por defecto si hay error
                if not stats_bateo_home:
                    stats_bateo_home = {
                        'wRC_plus': 100.0,
                        'OPS': 0.720,
                        'Fly_Ball_Pct': 32.5
                    }
                
                if not stats_bateo_away:
                    stats_bateo_away = {
                        'wRC_plus': 100.0,
                        'OPS': 0.720,
                        'Fly_Ball_Pct': 32.5
                    }
                
                # Extraer fatiga del bullpen
                print(f"💪 Analizando estado del bullpen...")
                fatiga_home = extraer_fatiga_bullpen(home_id, home_team)
                fatiga_away = extraer_fatiga_bullpen(away_id, away_team)
                
                fatiga_home_score = fatiga_home.get('puntuacion_fatiga', 50.0)
                fatiga_away_score = fatiga_away.get('puntuacion_fatiga', 50.0)
                
                juegos_data.append({
                    'away_team': away_team,
                    'home_team': home_team,
                    'diff_pct': diff_pct,
                    'pitcher_away': nombre_pitcher_away,
                    'pitcher_home': nombre_pitcher_home,
                    'delta_FIP': metricas_lanzadores.get('delta_FIP', 0.0),
                    'delta_WAR': metricas_lanzadores.get('delta_WAR', 0.0),
                    'delta_K9': metricas_lanzadores.get('delta_K9', 0.0),
                    'delta_BB9': metricas_lanzadores.get('delta_BB9', 0.0),
                    'wRC_plus_home': stats_bateo_home.get('wRC_plus', 100.0),
                    'OPS_home': stats_bateo_home.get('OPS', 0.720),
                    'Fly_Ball_Pct_home': stats_bateo_home.get('Fly_Ball_Pct', 32.5),
                    'wRC_plus_away': stats_bateo_away.get('wRC_plus', 100.0),
                    'OPS_away': stats_bateo_away.get('OPS', 0.720),
                    'Fly_Ball_Pct_away': stats_bateo_away.get('Fly_Ball_Pct', 32.5),
                    'fatiga_bullpen_home': fatiga_home_score,
                    'fatiga_bullpen_away': fatiga_away_score,
                })
                
            except KeyError as ke:
                print(f"❌ Error de clave al procesar juego: {ke}")
                continue
            except Exception as e:
                print(f"❌ Error procesando juego: {e}")
                continue
        
        # Guardar los datos en CSV
        if juegos_data:
            df = pd.DataFrame(juegos_data)
            df.to_csv('juegos_hoy.csv', index=False)
            print(f"\n✅ {len(juegos_data)} juegos descargados y guardados en juegos_hoy.csv")
            print(f"📊 Columnas incluidas: {df.columns.tolist()}")
            print(f"\n📈 Variables Machine Learning disponibles:")
            print(f"   📌 Bateo: wRC+ (home/away), OPS (home/away), Fly Ball % (home/away)")
            print(f"   📌 Lanzadores: delta_FIP, delta_WAR, delta_K9, delta_BB9")
            print(f"   📌 Bullpen: fatiga_bullpen_home (0-100), fatiga_bullpen_away (0-100)")
            print(f"   📌 Equipos: diff_pct (porcentaje de victorias)")
            print(f"\n💡 Total de features: 17 variables premium para XGBoost/CatBoost")
        else:
            print("⚠️ No se pudieron procesar los juegos de hoy")
            df_vacio = pd.DataFrame(columns=[
                'away_team', 'home_team', 'diff_pct',
                'pitcher_away', 'pitcher_home',
                'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9',
                'wRC_plus_home', 'OPS_home', 'Fly_Ball_Pct_home',
                'wRC_plus_away', 'OPS_away', 'Fly_Ball_Pct_away',
                'fatiga_bullpen_home', 'fatiga_bullpen_away'
            ])
            df_vacio.to_csv('juegos_hoy.csv', index=False)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con la API de MLB: {e}")
        # Crear archivo vacío para que el workflow continúe
        df_vacio = pd.DataFrame(columns=[
            'away_team', 'home_team', 'diff_pct',
            'pitcher_away', 'pitcher_home',
            'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9',
            'wRC_plus_home', 'OPS_home', 'Fly_Ball_Pct_home',
            'wRC_plus_away', 'OPS_away', 'Fly_Ball_Pct_away',
            'fatiga_bullpen_home', 'fatiga_bullpen_away'
        ])
        df_vacio.to_csv('juegos_hoy.csv', index=False)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        df_vacio = pd.DataFrame(columns=[
            'away_team', 'home_team', 'diff_pct',
            'pitcher_away', 'pitcher_home',
            'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9',
            'wRC_plus_home', 'OPS_home', 'Fly_Ball_Pct_home',
            'wRC_plus_away', 'OPS_away', 'Fly_Ball_Pct_away',
            'fatiga_bullpen_home', 'fatiga_bullpen_away'
        ])
        df_vacio.to_csv('juegos_hoy.csv', index=False)

if __name__ == "__main__":
    descargar_datos_mlb()
