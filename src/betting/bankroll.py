from src.betting.odds import american_to_decimal


def kelly_fraction(prob: float, odds_american: float) -> float:
    """Fraccion de Kelly completa: f* = (b*p - q) / b."""
    b = american_to_decimal(odds_american) - 1
    q = 1 - prob
    return max(0.0, (b * prob - q) / b)


def kelly_stake(prob: float, odds_american: float, bankroll: float,
                fraction: float = 0.25, max_pct: float = 0.02) -> float:
    """Stake en unidades: Kelly fraccionado, limitado a max_pct del bankroll."""
    stake = bankroll * kelly_fraction(prob, odds_american) * fraction
    return round(min(stake, bankroll * max_pct), 2)
