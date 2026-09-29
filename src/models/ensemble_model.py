import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from src.pipeline.feature_builder import FEATURES, TARGET
from src.utils.constants import MODELS_DIR, SETTINGS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MLBPredictionModel:
    """Ensemble ponderado (CatBoost + XGBoost + LogReg) + calibracion isotonica.

    - Split TEMPORAL (nunca aleatorio): ultimo 20% de fechas = validacion.
    - Pesos inversamente proporcionales al log-loss de validacion.
    - Calibracion isotonica sobre probabilidades combinadas -> probabilidades
      usables directamente contra cuotas (clave para value betting).
    """

    def __init__(self):
        cfg = SETTINGS["model"]
        self.test_size = cfg["test_size"]
        self.rs = cfg["random_state"]
        self.cb_params = cfg["catboost"]
        self.xg_params = cfg["xgboost"]
        self.feature_names = list(FEATURES)
        self.models: dict = {}
        self.weights: dict = {}
        self.calibrator: IsotonicRegression | None = None

    # ---------------- entrenamiento ----------------
    def _split_temporal(self, df: pd.DataFrame):
        df = df.sort_values("date").reset_index(drop=True)
        cut = int(len(df) * (1 - self.test_size))
        return df.iloc[:cut], df.iloc[cut:]

    def _build_models(self) -> dict:
        return {
            "catboost": CatBoostClassifier(random_seed=self.rs, verbose=0, **self.cb_params),
            "xgboost": XGBClassifier(random_state=self.rs, eval_metric="logloss",
                                     verbosity=0, **self.xg_params),
            "logreg": Pipeline([
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000)),
            ]),
        }

    def fit(self, df: pd.DataFrame, target: str = TARGET) -> "MLBPredictionModel":
        train, val = self._split_temporal(df)
        X_tr, y_tr = train[self.feature_names].fillna(0), train[target]
        X_va, y_va = val[self.feature_names].fillna(0), val[target]
        logger.info("Train: %d | Val: %d (split temporal)", len(train), len(val))

        losses = {}
        for name, mdl in self._build_models().items():
            mdl.fit(X_tr, y_tr)
            p = np.clip(mdl.predict_proba(X_va)[:, 1], 1e-6, 1 - 1e-6)
            losses[name] = log_loss(y_va, p)
            self.models[name] = mdl
            logger.info("  %s log-loss val: %.4f", name, losses[name])

        inv = {k: 1.0 / max(v, 1e-9) for k, v in losses.items()}
        total = sum(inv.values())
        self.weights = {k: v / total for k, v in inv.items()}

        blend = self._blend(X_va)
        self.calibrator = IsotonicRegression(out_of_bounds="clip")
        self.calibrator.fit(blend, y_va)
        cal = np.clip(self.calibrator.predict(blend), 1e-6, 1 - 1e-6)
        logger.info("Pesos: %s", {k: round(v, 3) for k, v in self.weights.items()})
        logger.info("Blend log-loss: %.4f | Calibrado: %.4f",
                    log_loss(y_va, np.clip(blend, 1e-6, 1 - 1e-6)), log_loss(y_va, cal))
        return self

    # ---------------- inferencia ----------------
    def _blend(self, X: pd.DataFrame) -> np.ndarray:
        return sum(self.weights[n] * self.models[n].predict_proba(X)[:, 1]
                   for n in self.models)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feature_names].fillna(0)
        p = self._blend(X)
        if self.calibrator is not None:
            p = self.calibrator.predict(p)
        return np.clip(p, 0.01, 0.99)

    # ---------------- persistencia ----------------
    def save(self, path: Path | None = None) -> str:
        path = path or Path(MODELS_DIR) / "ensemble_v2.pkl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info("Modelo guardado en %s", path)
        return str(path)

    @classmethod
    def load(cls, path: Path | None = None) -> "MLBPredictionModel":
        path = path or Path(MODELS_DIR) / "ensemble_v2.pkl"
        with open(path, "rb") as f:
            return pickle.load(f)
