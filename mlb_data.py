import requests
import pandas as pd
from datetime import datetime
from pitcher_stats import extraer_metricas_lanzadores

def descargar_datos_mlb():
    """
    Descarga los juegos de hoy desde la API de MLB Stats
    y calcula la diferencia de porcentaje de victorias entre equipos,
    más las métricas avanzadas de lanzadores usando Sabermetría.
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
                'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9'
            ])
            df_vacio.to_csv('juegos_hoy.csv', index=False)
            return
        
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
                
                juegos_data.append({
                    'away_team': away_team,
                    'home_team': home_team,
                    'diff_pct': diff_pct,
                    'pitcher_away': metricas_lanzadores.get('pitcher_away', 'Desconocido'),
                    'pitcher_home': metricas_lanzadores.get('pitcher_home', 'Desconocido'),
                    'delta_FIP': metricas_lanzadores.get('delta_FIP', 0.0),
                    'delta_WAR': metricas_lanzadores.get('delta_WAR', 0.0),
                    'delta_K9': metricas_lanzadores.get('delta_K9', 0.0),
                    'delta_BB9': metricas_lanzadores.get('delta_BB9', 0.0),
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
        else:
            print("⚠️ No se pudieron procesar los juegos de hoy")
            df_vacio = pd.DataFrame(columns=[
                'away_team', 'home_team', 'diff_pct',
                'pitcher_away', 'pitcher_home',
                'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9'
            ])
            df_vacio.to_csv('juegos_hoy.csv', index=False)
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error al conectar con la API de MLB: {e}")
        # Crear archivo vacío para que el workflow continúe
        df_vacio = pd.DataFrame(columns=[
            'away_team', 'home_team', 'diff_pct',
            'pitcher_away', 'pitcher_home',
            'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9'
        ])
        df_vacio.to_csv('juegos_hoy.csv', index=False)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        df_vacio = pd.DataFrame(columns=[
            'away_team', 'home_team', 'diff_pct',
            'pitcher_away', 'pitcher_home',
            'delta_FIP', 'delta_WAR', 'delta_K9', 'delta_BB9'
        ])
        df_vacio.to_csv('juegos_hoy.csv', index=False)

if __name__ == "__main__":
    descargar_datos_mlb()
