#!/usr/bin/env python
"""
Punto de entrada principal del pipeline MLB.

Ejemplo de uso:
    python main.py

Gera archivo 'juegos_hoy.csv' con features para ML.
"""

from src.pipeline.mlb_data_pipeline import MLBDataPipeline
from src.pipeline.models import MLBPredictionModel
from datetime import datetime

def main():
    print("\n" + "="*60)
    print("🏟️  MLB SABERMETRICS PIPELINE v1.0")
    print("="*60)
    
    # Ejecutar pipeline
    pipeline = MLBDataPipeline()
    df_juegos = pipeline.ejecutar()
    
    if df_juegos.empty:
        print("\n⚠️  No hay juegos para procesar.")
        return
    
    # Guardar datos
    pipeline.guardar_csv(df_juegos)
    
    # Realizar predicciones
    print("\n🤖 Entrenando modelo CatBoost...")
    modelo = MLBPredictionModel()
    modelo.entrenar()
    
    print("\n📊 Realizando predicciones...")
    predicciones = modelo.predecir(df_juegos)
    
    # Guardar predicciones
    hoy = datetime.today().strftime('%Y-%m-%d')
    with open('PREDICCIONES.md', 'w') as f:
        f.write(f"# Predicciones MLB - {hoy}\n\n")
        f.write("> **Sistema**: Modelo CatBoost basado en sabermetría avanzada\n\n")
        f.write(predicciones.to_markdown(index=False))
    
    print("\n✅ Predicciones guardadas en PREDICCIONES.md")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()
