import pandas as pd
import numpy as np
from catboost import CatBoostClassifier

class MLBPredictionModel:
    """
    Modelo de clasificación binaria para predicción de ganador local.
    Usa CatBoost con datos históricos sintéticos basados en MLB.
    """
    
    def __init__(self):
        self.model = None
    
    def entrenar(self) -> CatBoostClassifier:
        """
        Entrena el modelo con datos históricos sintéticos.
        
        Simula 1000 partidos históricos con ventaja de localía (+4%).
        
        Returns:
            Modelo entrenado
        """
        np.random.seed(42)
        n_partidos = 1000
        
        # Diferencia de porcentaje de victorias (Local - Visitante)
        diff_pct = np.random.uniform(-0.300, 0.300, n_partidos)
        
        # Resultado: 1 = gana local, 0 = gana visitante
        # Ventaja histórica de localía: +4% (0.04 en logit)
        prob_base = 1 / (1 + np.exp(-(diff_pct * 5 + 0.16)))
        resultado = np.where(np.random.rand(n_partidos) < prob_base, 1, 0)
        
        df_train = pd.DataFrame({
            'diff_pct': diff_pct,
            'resultado': resultado
        })
        
        # Entrenar silenciosamente
        self.model = CatBoostClassifier(
            iterations=150,
            learning_rate=0.05,
            depth=4,
            verbose=0
        )
        self.model.fit(df_train[['diff_pct']], df_train['resultado'])
        return self.model
    
    def predecir(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Realiza predicciones sobre juegos.
        
        Args:
            df: DataFrame con columna 'diff_pct'
            
        Returns:
            DataFrame con predicciones
        """
        if self.model is None:
            self.entrenar()
        
        # Predecir probabilidades
        X = df[['diff_pct']]
        probabilidades = self.model.predict_proba(X)[:, 1]
        
        predicciones = []
        for i, row in df.iterrows():
            prob_home = round(probabilidades[i] * 100, 1)
            
            predicciones.append({
                'Partido': f"{row['away_team']} @ {row['home_team']}",
                'Probabilidad_Local_%': prob_home,
                'Prediccion_Ganador': row['home_team'] if prob_home > 50.0 else row['away_team']
            })
        
        return pd.DataFrame(predicciones)
