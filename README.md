# MLB Sabermetrics Pipeline 🏟️

Pipeline modular para análisis y predicción de juegos de Major League Baseball usando sabermetría avanzada.

## 📊 ¿Qué hace?

Extrae métricas de la MLB Stats API y realiza predicciones de ganador local combinando:

- **Análisis de Lanzadores**: FIP, WAR, K/9, BB/9 (diferencias entre abridores)
- **Análisis de Bateo**: wRC+, OPS, Fly Ball % (estadísticas por splits RHP/LHP)
- **Análisis de Bullpen**: Métrica de fatiga 0-100 (volumen, distribución, consistencia)
- **Modelo Predictivo**: CatBoost para clasificación binaria (probabilidad de victoria local)

## 🏗️ Arquitectura Modular

```
src/
  data/                    # Capa de acceso a datos
    mlb_api_client.py      # Cliente centralizado MLB Stats API
    cache_manager.py       # Gestor de caché unificado por categoría
    pybaseball_wrapper.py  # Wrapper para pybaseball (sabermetría)
  
  analytics/               # Capa de análisis y cálculos
    pitcher_analytics.py   # Métricas de lanzadores (delta FIP, WAR, K/9, BB/9)
    batting_analytics.py   # Métricas de bateo (wRC+, OPS, Fly Ball %)
    bullpen_analytics.py   # Fatiga del bullpen (0-100)
  
  pipeline/                # Orquestación e integración
    mlb_data_pipeline.py   # Pipeline principal (coordinador)
    models.py              # Modelo CatBoost para predicciones
  
  utils/
    constants.py           # Configuración centralizada

main.py                    # Punto de entrada
requirements.txt           # Dependencias
```

## 🚀 Cómo usar

### Instalación

```bash
git clone https://github.com/jossoficial/Major-leaguebaseball.git
cd Major-leaguebaseball
pip install -r requirements.txt
```

### Ejecutar Pipeline Completo

```bash
python main.py
```

Esto genera `juegos_hoy.csv` con todas las features para ML.

### Usar en Python

```python
from src.pipeline.mlb_data_pipeline import MLBDataPipeline
from src.pipeline.models import MLBPredictionModel

# Ejecutar pipeline
pipeline = MLBDataPipeline()
df_juegos = pipeline.ejecutar()  # Procesa juegos de hoy

# Guardar datos
pipeline.guardar_csv(df_juegos)

# Realizar predicciones
modelo = MLBPredictionModel()
modelo.entrenar()
predicciones = modelo.predecir(df_juegos)
print(predicciones)
```

## 📈 Features Generadas

### Equipo
- `away_team` - Equipo visitante
- `home_team` - Equipo local
- `diff_pct` - Diferencia de porcentaje de victorias (local - visitante)

### Lanzadores (Sabermetría)
- `delta_FIP` - Diferencia FIP (lower is better for pitcher)
- `delta_WAR` - Diferencia WAR (ventaja acumulada)
- `delta_K9` - Diferencia K/9 (strikeouts por 9 innings)
- `delta_BB9` - Diferencia BB/9 (base on balls por 9 innings)

### Bateo (Splits)
- `wRC_plus_home` - wRC+ equipo local vs lanzador visitante
- `OPS_home` - On-base Plus Slugging (equipo local)
- `Fly_Ball_Pct_home` - % de fly balls (equipo local)
- `wRC_plus_away` - wRC+ equipo visitante
- `OPS_away` - OPS (equipo visitante)
- `Fly_Ball_Pct_away` - % de fly balls (equipo visitante)

### Bullpen
- `fatiga_bullpen_home` - Métrica de fatiga 0-100 (equipo local)
- `fatiga_bullpen_away` - Métrica de fatiga 0-100 (equipo visitante)

## 🔄 Caché

Todos los módulos utilizan caché automático para evitar saturar APIs externas:

```
.cache/
  bateo/          # Estadísticas de bateo (por equipo/tipo lanzador)
  bullpen/        # Fatiga del bullpen (por equipo)
  pitcher/        # Estadísticas de lanzadores (por nombre)
```

El caché se invalida automáticamente cada día.

## 📚 Stack Técnico

- **Lenguaje**: Python 3.8+
- **APIs**: MLB Stats API, pybaseball (FanGraphs)
- **Librerías principales**:
  - `requests` - HTTP client
  - `pandas` - Data manipulation
  - `catboost` - ML classification
  - `pybaseball` - Baseball statistics
  - `numpy` - Numerical computing

## 🎯 Próximas mejoras

- [ ] Integración con más features (home field advantage, travel distance)
- [ ] Modelo ensemble (XGBoost + CatBoost)
- [ ] API REST para predicciones en tiempo real
- [ ] Dashboard de visualización
- [ ] Backtesting contra datos históricos
- [ ] Metricas avanzadas de statcast (exit velo, barrel rate)

## 📝 Licencia

MIT
