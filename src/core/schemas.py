"""Small, stable schemas for boundaries between pipeline components."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class GameInput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    game_pk: int = Field(gt=0)
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)


class PredictionOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    game_pk: int = Field(gt=0)
    prob_home: float = Field(ge=0, le=1)
    prob_away: float = Field(ge=0, le=1)
    apostar: str = ""
    stake_unidades: float = Field(ge=0)
