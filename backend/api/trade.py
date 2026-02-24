from fastapi import APIRouter

from models.trade import (
    PipRequest,
    PipResponse,
    PositionSizeRequest,
    PositionSizeResponse,
    RiskRewardRequest,
    RiskRewardResponse,
)

router = APIRouter(prefix="/api/trade", tags=["trade"])

JPY_PAIRS = ("JPY",)
CRYPTO_LARGE = ("BTC", "ETH", "XAU", "GOLD")


def _pip_size(symbol: str) -> float:
    s = symbol.upper()
    if any(p in s for p in JPY_PAIRS):
        return 0.01
    if any(p in s for p in CRYPTO_LARGE):
        return 0.01
    return 0.0001


@router.post("/risk-reward", response_model=RiskRewardResponse)
def calculate_risk_reward(req: RiskRewardRequest) -> RiskRewardResponse:
    risk = abs(req.entry - req.stop_loss)
    reward = abs(req.take_profit - req.entry)
    ratio = round(reward / risk, 2) if risk > 0 else 0.0

    return RiskRewardResponse(
        risk_pips=round(risk / 0.0001, 1),
        reward_pips=round(reward / 0.0001, 1),
        ratio=ratio,
        ratio_label=f"1:{ratio}",
    )


@router.post("/position-size", response_model=PositionSizeResponse)
def calculate_position_size(req: PositionSizeRequest) -> PositionSizeResponse:
    risk_amount = round(req.account_balance * (req.risk_percent / 100), 2)
    # lots = risk_amount / (stop_loss_pips * pip_value_per_lot)
    lots = round(risk_amount / (req.stop_loss_pips * req.pip_value), 4)
    units = int(lots * 100_000)

    return PositionSizeResponse(
        risk_amount=risk_amount,
        lots=lots,
        units=units,
    )


@router.post("/pips", response_model=PipResponse)
def calculate_pips(req: PipRequest) -> PipResponse:
    pip = _pip_size(req.symbol)
    diff = req.price_to - req.price_from
    pips = round(diff / pip, 1)

    return PipResponse(
        pips=abs(pips),
        direction="up" if pips > 0 else "down",
    )
