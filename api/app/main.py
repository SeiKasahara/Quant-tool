from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.api import signals, documents, tickers, health, backtest
from app.core.config import settings
from app.core.logging import setup_logging

setup_logging()
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up API server")
    yield
    logger.info("Shutting down API server")

app = FastAPI(
    title="Signal Detection API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://web:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(signals.router, prefix="/signals", tags=["signals"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(tickers.router, prefix="/tickers", tags=["tickers"])
app.include_router(backtest.router, prefix="/backtest", tags=["backtest"])

@app.get("/")
async def root():
    return {"message": "Signal Detection API", "status": "running"}