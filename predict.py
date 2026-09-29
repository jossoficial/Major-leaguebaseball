import pandas as pd
import numpy as np
from datetime import datetime
from catboost import CatBoostClassifier
from tabulate import tabulate

FEATURES = ["diff_pct"]


def entrenar_modelo_express():
    """Entrena solo con datos históricos reales; nunca genera observaciones sintéticas."""
    raise RuntimeError(
        "No hay modelo histórico instalado. Ejecuta `python main.py train --season YYYY` "
        "con datos reales antes de predecir."
    )


def generar_predicciones():
    try:
        df_hoy = pd.read_csv("juegos_hoy.csv")
    except FileNotFoundError:
        print("No se encontró juegos_hoy.csv. Abortando sin datos ficticios.")
        return
    if df_hoy.empty:
        print("No hay partidos con métricas reales disponibles.")
        return
    if "diff_pct" not in df_hoy or df_hoy["diff_pct"].isna().any():
        print("Faltan métricas reales; no se generarán predicciones de relleno.")
        return
    print("Este script legacy requiere un modelo entrenado con datos reales. Usa `main.py predict`.")


if __name__ == "__main__":
    generar_predicciones()
