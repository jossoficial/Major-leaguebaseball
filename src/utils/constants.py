"""Constantes centralizadas de la aplicación."""

# Mapeo de equipos
TEAM_ID_MAP = {
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

# Directorio de caché
CACHE_DIR = '.cache'

# MLB Stats API
MLB_API_BASE_URL = 'https://statsapi.mlb.com/api/v1'

# Valores por defecto para sabermetría
DEFAULT_PITCHER_STATS = {
    'FIP': 4.0,
    'WAR': 0.0,
    'K/9': 8.0,
    'BB/9': 3.0
}

# Valores por defecto para bateo
DEFAULT_BATTING_STATS = {
    'wRC_plus': 100.0,
    'OPS': 0.720,
    'Fly_Ball_Pct': 32.5
}

# Thresholds de fatiga bullpen
BULLPEN_FATIGUE_THRESHOLDS = {
    'fresh': (0, 30),      # Verde
    'normal': (30, 60),    # Amarillo
    'fatigued': (60, 80),  # Naranja
    'exhausted': (80, 100) # Rojo
}
