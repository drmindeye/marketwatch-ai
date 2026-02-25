import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.payments import router as payments_router
from api.trade import router as trade_router
from api.ai import router as ai_router
from api.whatsapp import router as whatsapp_router
from api.telegram import router as telegram_router
from api.alerts import router as alerts_router
from api.market import router as market_router
from api.referral import router as referral_router
from api.profile import router as profile_router
from api.admin import router as admin_router
from services.worker import run_worker
from services.reminder_worker import run_reminder_worker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task = asyncio.create_task(run_worker())
    reminder_task = asyncio.create_task(run_reminder_worker())
    logger.info("FMP + reminder workers started")
    yield
    for task in (worker_task, reminder_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("Background workers stopped")


app = FastAPI(title="MarketWatch AI API", version="1.0.0", lifespan=lifespan)

_frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")
_allowed_origins = list(set(filter(None, [
    "http://localhost:3000",
    "http://localhost:3001",
    _frontend_url,
])))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.railway\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments_router)
app.include_router(trade_router)
app.include_router(ai_router)
app.include_router(whatsapp_router)
app.include_router(telegram_router)
app.include_router(alerts_router)
app.include_router(market_router)
app.include_router(referral_router)
app.include_router(profile_router)
app.include_router(admin_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
