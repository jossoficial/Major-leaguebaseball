import pandas as pd
import numpy as np
from datetime import datetime
from catboost import CatBoostClassifier

def entrenar_modelo_express():
    """
    Simula el comportamiento histórico de la MLB (Data Sintética basada en histórico real)
    para entrenar a CatBoost en la nube antes de predecir.
    """
    np.random.seed(42)
    # Generamos 1000 partidos históricos de entrenamiento
    n_partidos = 1000
    
    # Variables: diferencia de porcentaje de victorias (Local - Visitante)
    diff_pct = np.random.uniform(-0.300, 0.300, n_partidos)
    
    # El resultado final (1 = gana local, 0 = gana visitante) 
    # Añadimos la ventaja histórica de localía (+4%) y algo de aleatoriedad
    prob_base = 1 / (1 + np.exp(-(diff_pct * 5 + 0.16))) 
    resultado = np.where(np.random.rand(n_partidos) < prob_base, 1, 0)
    
    df_train = pd.DataFrame({
        'diff_pct': diff_pct,
        'resultado': resultado
    })
    
    # Inicializar y entrenar CatBoost silenciosamente
    model = CatBoostClassifier(
        iterations=150,
        learning_rate=0.05,
        depth=4,
        verbose=0
    )
    model.fit(df_train[['diff_pct']], df_train['resultado'])
    return model

def generar_predicciones():
    try:
        df_hoy = pd.read_csv("juegos_hoy.csv")
    except FileNotFoundError:
        print("No se encontró el archivo juegos_hoy.csv. Abortando.")
        return

    if df_hoy.empty:
        print("No hay partidos programados en 'juegos_hoy.csv'.")
        return

    # 1. Entrenar el clasificador CatBoost en tiempo de ejecución
    modelo_catboost = entrenar_modelo_express()
    
    # 2. Predecir las probabilidades del set extraído de la API de la MLB
    # predict_proba devuelve [prob_perder, prob_ganar]
    X_hoy = df_hoy[['diff_pct']]
    probabilidades = modelo_catboost.predict_proba(X_hoy)[:, 1]
    
    predicciones = []
    for i, row in df_hoy.iterrows():
        prob_home = round(probabilidades[i] * 100, 1)
        
        predicciones.append({
            "Partido": f"{row['away_team']} @ {row['home_team']}",
            "Probabilidad Local (CatBoost %)": prob_home,
            "Predicción Ganador": row['home_team'] if prob_home > 50.0 else row['away_team']
        })
        
    df_res = pd.DataFrame(predicciones)
    hoy = datetime.today().strftime('%Y-%m-%d')
    
    # 3. Escribir el reporte en Markdown para visualizarlo en GitHub
    with open("PREDICCIONES.md", "w") as f:
        f.write(f"# Predicciones MLB con CatBoost - {hoy}\n\n")
        f.write("> **Nota del modelo:** Sistema de clasificación binaria entrenado dinámicamente mediante Gradient Boosting.\n\n")
        f.write(df_res.to_markdown(index=False))
    
    print("Predicciones con CatBoost generadas con éxito en PREDICCIONES.md")

if __name__ == "__main__":
    generar_predicciones()
