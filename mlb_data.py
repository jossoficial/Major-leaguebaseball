import requests
import pandas as pd
from datetime import datetime

def descargar_datos_mlb():
    """
    Descarga los juegos de hoy desde la API de MLB Stats
    y calcula la diferencia de porcentaje de victorias entre equipos.
    """
    try:
        # Obtener la fecha de hoy en formato YYYY-MM-DD
        hoy = datetime.today().strftime('%Y-%m-%d')
        
        # API de MLB Stats
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={hoy}"
        response = requests.get(url)
        response.raise_for_status()
        
        juegos = response.json()
        
        if not juegos:
            print(f"No hay juegos programados para {hoy}")
            # Crear archivo vacío para que predict.py maneje el caso
            df_vacio = pd.DataFrame(columns=['away_team', 'home_team', 'diff_pct'])
            df_vacio.to_csv('juegos_hoy.csv', index=False)
            return
        
        juegos_data = []
        
        for juego in juegos:
            if juego['status']['abstractGameState'] == 'Scheduled' or juego['status']['abstractGameState'] == 'Pre-Game':
                try:
                    away_team = juego['teams']['away']['team']['name']
                    home_team = juego['teams']['home']['team']['name']
                    
                    away_id = juego['teams']['away']['team']['id']
                    home_id = juego['teams']['home']['team']['id']
                    
                    # Obtener estadísticas de los equipos
                    away_stats_url = f"https://statsapi.mlb.com/api/v1/teams/{away_id}"
                    home_stats_url = f"https://statsapi.mlb.com/api/v1/teams/{home_id}"
                    
                    away_response = requests.get(away_stats_url).json()
                    home_response = requests.get(home_stats_url).json()
                    
                    # Obtener el récord actual (si está disponible en la temporada)
                    away_wins = away_response.get('record', {}).get('wins', 0) if 'record' in away_response else 0
                    away_losses = away_response.get('record', {}).get('losses', 0) if 'record' in away_response else 0
                    home_wins = home_response.get('record', {}).get('wins', 0) if 'record' in home_response else 0
                    home_losses = home_response.get('record', {}).get('losses', 0) if 'record' in home_response else 0
                    
                    # Calcular porcentaje de victorias
                    away_pct = away_wins / (away_wins + away_losses) if (away_wins + away_losses) > 0 else 0.5
                    home_pct = home_wins / (home_wins + home_losses) if (home_wins + home_losses) > 0 else 0.5
                    
                    # Diferencia de porcentaje (local - visitante)
                    diff_pct = home_pct - away_pct
                    
                    juegos_data.append({
                        'away_team': away_team,
                        'home_team': home_team,
                        'diff_pct': diff_pct
                    })
                    
                except Exception as e:
                    print(f"Error procesando juego: {e}")
                    continue
        
        # Guardar los datos en CSV
        if juegos_data:
            df = pd.DataFrame(juegos_data)
            df.to_csv('juegos_hoy.csv', index=False)
            print(f"✓ {len(juegos_data)} juegos descargados y guardados en juegos_hoy.csv")
        else:
            print("No se pudieron procesar los juegos de hoy")
            df_vacio = pd.DataFrame(columns=['away_team', 'home_team', 'diff_pct'])
            df_vacio.to_csv('juegos_hoy.csv', index=False)
            
    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con la API de MLB: {e}")
        # Crear archivo vacío para que el workflow continúe
        df_vacio = pd.DataFrame(columns=['away_team', 'home_team', 'diff_pct'])
        df_vacio.to_csv('juegos_hoy.csv', index=False)
    except Exception as e:
        print(f"Error inesperado: {e}")
        df_vacio = pd.DataFrame(columns=['away_team', 'home_team', 'diff_pct'])
        df_vacio.to_csv('juegos_hoy.csv', index=False)

if __name__ == "__main__":
    descargar_datos_mlb()
