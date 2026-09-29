def american_to_implied(odds: float) -> float:
    """Cuota americana -> probabilidad implicita (con margen / vig)."""
    odds = float(odds)
    return 100.0 / (odds + 100.0) if odds > 0 else -odds / (-odds + 100.0)


def implied_to_american(p: float) -> float:
    p = min(max(float(p), 1e-6), 1 - 1e-6)
    return round(100 * p / (1 - p) - 100 if p >= 0.5 else -100 * (1 - p) / p)


def american_to_decimal(odds: float) -> float:
    odds = float(odds)
    return round(1 + (odds / 100.0 if odds > 0 else 100.0 / -odds), 4)


def devig_two_way(p_home: float, p_away: float) -> tuple[float, float]:
    """Elimina el vig: normaliza probabilidades implicitas a 1."""
    total = p_home + p_away
    return p_home / total, p_away / total


def edge(prob_modelo: float, prob_mercado: float) -> float:
    """Ventaja estimada del modelo sobre el mercado (sin vig)."""
    return prob_modelo - prob_mercado


def is_value_bet(prob_modelo: float, prob_mercado: float, min_edge: float = 0.03) -> bool:
    return edge(prob_modelo, prob_mercado) >= min_edge
