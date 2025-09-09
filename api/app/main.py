from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.api import signals, documents, tickers, health, backtest, metrics as metrics_api, sources as sources_api, event_patterns, auth, settings as settings_api
from app.services import ingest_events
from fastapi import Request
from fastapi.responses import StreamingResponse
import asyncio
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
app.include_router(metrics_api.router, prefix="", tags=["metrics"])
app.include_router(sources_api.router, prefix="", tags=["sources"])
app.include_router(event_patterns.router, prefix="", tags=["event_patterns"])
app.include_router(auth.router, prefix="", tags=["auth"])
app.include_router(settings_api.router, prefix="", tags=["settings"])


@app.get('/ingest/stream')
async def ingest_stream(request: Request):
    # SSE endpoint forwarding in-memory ingest events
    async def event_generator():
        try:
            async for ev in ingest_events.subscribe():
                import json
                yield f'data: {json.dumps(ev)}\n\n'
                if await request.is_disconnected():
                    break
        finally:
            return

    headers = {
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no'
    }
    return StreamingResponse(event_generator(), media_type='text/event-stream', headers=headers)

@app.get("/")
async def root():
    return {"message": "Signal Detection API", "status": "running"}