import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from src.betting.bankroll import american_to_decimal, kelly_stake
from src.betting.odds import american_to_implied, devig_two_way
from src.models.ensemble_model import MLBPredictionModel
from src.pipeline.feature_builder import TARGET
from src.utils.constants import REPORTS_DIR, SETTINGS
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Backtester:
    """Walk-forward backtesting con simulacion de apuestas.

    En cada fold se reentrena el modelo solo con datos anteriores al fold
    (sin leakage) y se simulan value bets con Kelly fraccionado.
    """

    def __init__(self):
        self.cfg = SETTINGS

    def run(self, df: pd.DataFrame, n_splits: int | None = None,
            odds_home: int | None = None, odds_away: int | None = None):
        df = df.sort_values("date").reset_index(drop=True)
        n = n_splits or self.cfg["backtest"]["n_splits"]
        odds_home = odds_home or self.cfg["odds"]["default_odds_home"]
        odds_away = odds_away or self.cfg["odds"]["default_odds_away"]
        cuts = np.linspace(0, len(df), n + 1).astype(int)

        preds = []
        for i in range(1, n):  # el fold 0 no tiene suficiente historia
            train, test = df.iloc[:cuts[i]], df.iloc[cuts[i]:cuts[i + 1]]
            if len(train) < 200 or test.empty:
                continue
            logger.info("Fold %d/%d: train=%d test=%d", i, n - 1, len(train), len(test))
            model = MLBPredictionModel().fit(train)
            p = model.predict_proba(test)
            tmp = test[["date", "game_pk", "home_team", "away_team", TARGET]].copy()
            tmp["prob_home"] = p
            preds.append(tmp)

        res = pd.concat(preds, ignore_index=True)
        res["prob_away"] = 1 - res["prob_home"]
        sim = self._simulate(res, odds_home, odds_away)
        metrics = self._metrics(res, sim)

        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        res.to_csv(REPORTS_DIR / "backtest_predictions.csv", index=False)
        sim.to_csv(REPORTS_DIR / "equity_curve.csv", index=False)
        return res, metrics

    # ---------------- simulacion ----------------
    def _simulate(self, res: pd.DataFrame, odds_home: int, odds_away: int) -> pd.DataFrame:
        bank = self.cfg["bankroll"]
        m_home, m_away = devig_two_way(american_to_implied(odds_home),
                                       american_to_implied(odds_away))
        bankroll = float(bank["unidad_base"])
        rows = []
        for row in res.itertuples():
            side, stake, profit = "", 0.0, 0.0
            edge_h = row.prob_home - m_home
            edge_a = row.prob_away - m_away
            if max(edge_h, edge_a) >= bank["min_edge"]:
                side = "H" if edge_h >= edge_a else "A"
                prob = row.prob_home if side == "H" else row.prob_away
                odds = odds_home if side == "H" else odds_away
                stake = kelly_stake(prob, odds, bankroll,
                                    bank["kelly_fraction"], bank["max_stake_pct"])
                won = bool(row.home_win) if side == "H" else not bool(row.home_win)
                profit = stake * (american_to_decimal(odds) - 1) if won else -stake
                bankroll += profit
            rows.append({"date": row.date, "game_pk": row.game_pk, "side": side,
                         "stake": round(stake, 2), "profit": round(profit, 2),
                         "bankroll": round(bankroll, 2)})
        return pd.DataFrame(rows)

    # ---------------- metricas ----------------
    @staticmethod
    def _max_drawdown(bankroll: pd.Series) -> float:
        return round(float((bankroll - bankroll.cummax()).min()), 2)

    def _metrics(self, res: pd.DataFrame, sim: pd.DataFrame) -> dict:
        y, p = res[TARGET], res["prob_home"]
        bets = sim[sim["stake"] > 0]
        total_staked = bets["stake"].sum()
        return {
            "juegos": len(res),
            "apuestas": len(bets),
            "log_loss": round(log_loss(y, p), 4),
            "brier": round(brier_score_loss(y, p), 4),
            "accuracy": round(accuracy_score(y, (p > 0.5).astype(int)), 4),
            "staked_unidades": round(total_staked, 2),
            "profit_unidades": round(sim["profit"].sum(), 2),
            "roi_pct": round(100 * sim["profit"].sum() / total_staked, 2) if total_staked else 0.0,
            "win_rate_apuestas": round((bets["profit"] > 0).mean(), 4) if len(bets) else 0.0,
            "bankroll_final": round(sim["bankroll"].iloc[-1], 2) if len(sim) else 0.0,
            "max_drawdown_unidades": self._max_drawdown(sim["bankroll"]) if len(sim) else 0.0,
        }
