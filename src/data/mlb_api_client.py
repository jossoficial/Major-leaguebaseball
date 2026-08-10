import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List

class MLBStatsAPIClient:
    """
    Cliente para la MLB Stats API.
    Gestiona todas las llamadas HTTP a https://statsapi.mlb.com/api/v1
    """
    
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1"
        self.session = requests.Session()
    
    def get_schedule(self, date: str, sport_id: int = 1) -> List[Dict]:
        """
        Obtiene los juegos programados para una fecha.
        
        Args:
            date: Fecha en formato YYYY-MM-DD
            sport_id: ID del deporte (1 = MLB)
            
        Returns:
            Lista de diccionarios con información de juegos
        """
        try:
            url = f"{self.base_url}/schedule?sportId={sport_id}&date={date}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error obteniendo schedule: {e}")
            return []
    
    def get_game(self, game_pk: int) -> Optional[Dict]:
        """
        Obtiene datos detallados de un juego.
        
        Args:
            game_pk: ID del juego
            
        Returns:
            Diccionario con datos del juego
        """
        try:
            url = f"{self.base_url}/game/{game_pk}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error obteniendo game {game_pk}: {e}")
            return None
    
    def get_boxscore(self, game_pk: int) -> Optional[Dict]:
        """
        Obtiene el boxscore de un juego.
        
        Args:
            game_pk: ID del juego
            
        Returns:
            Diccionario con boxscore
        """
        try:
            url = f"{self.base_url}/game/{game_pk}/boxscore"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error obteniendo boxscore {game_pk}: {e}")
            return None
    
    def get_team_schedule(self, team_id: int, start_date: str, end_date: str) -> List[Dict]:
        """
        Obtiene el schedule de un equipo en un rango de fechas.
        
        Args:
            team_id: ID del equipo
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            
        Returns:
            Lista de juegos
        """
        try:
            url = f"{self.base_url}/schedule?sportId=1&teamId={team_id}&startDate={start_date}&endDate={end_date}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error obteniendo team schedule: {e}")
            return []
    
    def get_team(self, team_id: int) -> Optional[Dict]:
        """
        Obtiene información del equipo.
        
        Args:
            team_id: ID del equipo
            
        Returns:
            Diccionario con datos del equipo
        """
        try:
            url = f"{self.base_url}/teams/{team_id}"
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"❌ Error obteniendo team {team_id}: {e}")
            return None
