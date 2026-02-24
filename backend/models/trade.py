from pydantic import BaseModel, Field


class RiskRewardRequest(BaseModel):
    entry: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: float = Field(..., gt=0)


class RiskRewardResponse(BaseModel):
    risk_pips: float
    reward_pips: float
    ratio: float
    ratio_label: str


class PositionSizeRequest(BaseModel):
    account_balance: float = Field(..., gt=0)
    risk_percent: float = Field(..., gt=0, le=100)
    stop_loss_pips: float = Field(..., gt=0)
    pip_value: float = Field(default=10.0, gt=0, description="Pip value in account currency per standard lot")


class PositionSizeResponse(BaseModel):
    risk_amount: float
    lots: float
    units: int


class PipRequest(BaseModel):
    symbol: str
    price_from: float = Field(..., gt=0)
    price_to: float = Field(..., gt=0)


class PipResponse(BaseModel):
    pips: float
    direction: str
