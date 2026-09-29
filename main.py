import argparse
from pathlib import Path

import pandas as pd

from src.backtest.backtester import Backtester
from src.betting.bankroll import kelly_stake
from src.betting.odds import american_to_implied, devig_two_way
from src.data.historical_loader import HistoricalLoader
from src.models.ensemble_model import MLBPredictionModel
from src.pipeline.mlb_data_pipeline import MLBDataPipeline
from src.utils.constants import DATA_DIR, MODELS_DIR, REPORTS_DIR, SETTINGS
from src.utils.logger import get_logger

logger = get_logger("main")


def cmd_predict(args):
    pipeline = MLBDataPipeline(date_str=args.date)
    df = pipeline.ejecutar()
    if df.empty:
        return
    model_path = MODELS_DIR / "ensemble_v2.pkl"
    if model_path.exists():
        df["prob_home"] = MLBPredictionModel.load().predict_proba(df)
    else:
        logger.warning("No hay modelo entrenado; entrena con: python main.py train --season 2024")
        df["prob_home"] = 0.5
    df["prob_away"] = 1 - df["prob_home"]

    bank = SETTINGS["bankroll"]
    odds_h = args.odds_home or SETTINGS["odds"]["default_odds_home"]
    odds_a = args.odds_away or SETTINGS["odds"]["default_odds_away"]
    m_h, m_a = devig_two_way(american_to_implied(odds_h), american_to_implied(odds_a))
    df["edge_home"] = (df["prob_home"] - m_h).round(4)
    df["edge_away"] = (df["prob_away"] - m_a).round(4)

    sides, stakes = [], []
    for row in df.itertuples():
        side, stake = "", 0.0
        if row.edge_home >= bank["min_edge"] and row.edge_home >= row.edge_away:
            stake = kelly_stake(row.prob_home, odds_h, bank["unidad_base"],
                                bank["kelly_fraction"], bank["max_stake_pct"])
            side = "HOME"
        elif row.edge_away >= bank["min_edge"]:
            stake = kelly_stake(row.prob_away, odds_a, bank["unidad_base"],
                                bank["kelly_fraction"], bank["max_stake_pct"])
            side = "AWAY"
        sides.append(side)
        stakes.append(stake)
    df["apostar"] = sides
    df["stake_unidades"] = stakes

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"predictions_{pipeline.date}.csv"
    df.to_csv(out, index=False)
    n_value = int((df["apostar"] != "").sum())
    logger.info("%d juegos | %d value bets | guardado: %s", len(df), n_value, out)
    print(df[["home_team", "away_team", "prob_home", "edge_home", "edge_away",
              "apostar", "stake_unidades"]].to_string(index=False))


def cmd_train(args):
    loader = HistoricalLoader()
    df = _load_or_build(loader, args.season)
    MLBPredictionModel().fit(df).save()
    out = DATA_DIR / f"train_{args.season}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    logger.info("Dataset guardado en %s", out)


def cmd_backtest(args):
    loader = HistoricalLoader()
    df = _load_or_build(loader, args.season)
    bt = Backtester()
    _, metrics = bt.run(df, n_splits=args.splits,
                        odds_home=args.odds_home, odds_away=args.odds_away)
    logger.info("===== RESULTADOS BACKTEST %s =====", args.season)
    for k, v in metrics.items():
        logger.info("  %s: %s", k, v)


def _load_or_build(loader: HistoricalLoader, season: int) -> pd.DataFrame:
    path = DATA_DIR / f"train_{season}.csv"
    if path.exists():
        logger.info("Cargando dataset existente: %s", path)
        return pd.read_csv(path)
    logger.info("Construyendo dataset %s (puede tardar: descarga stats as-of semanales)", season)
    games = loader.games(f"{season}-03-20", f"{season}-10-05")
    df = loader.build_dataset(games)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MLB Sabermetrics Pipeline v2")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("predict", help="Pipeline de hoy + predicciones + value bets")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (default: hoy)")
    p.add_argument("--odds-home", type=int, default=None, help="Cuota americana local")
    p.add_argument("--odds-away", type=int, default=None, help="Cuota americana visitante")
    p.set_defaults(fn=cmd_predict)

    t = sub.add_parser("train", help="Entrenar ensemble con una temporada")
    t.add_argument("--season", type=int, required=True)
    t.set_defaults(fn=cmd_train)

    b = sub.add_parser("backtest", help="Backtest walk-forward de una temporada")
    b.add_argument("--season", type=int, required=True)
    b.add_argument("--splits", type=int, default=None)
    b.add_argument("--odds-home", type=int, default=None)
    b.add_argument("--odds-away", type=int, default=None)
    b.set_defaults(fn=cmd_backtest)

    args = parser.parse_args()
    args.fn(args)
