"""FastAPI application for SCF Brain — Control ↔ Technology Evidence Engine.

Serves the bidirectional compliance pipeline as a web API with CORS support
and SSE streaming for real-time agent activity updates.

Usage:
    PYTHONPATH=projects uv run uvicorn scf_brain.api.app:app --reload --port 8006
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scf_brain.api.routers.scf_brain import router as scf_brain_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load env vars on startup.

    Args:
        app: The FastAPI application instance.
    """
    load_dotenv()
    logger.info("SCF Brain API starting up — Control ↔ Technology Evidence Engine")
    yield
    logger.info("SCF Brain API shutting down")


app = FastAPI(
    title="SCF Brain API — ControlBridge AI",
    description="Bidirectional compliance engine: SCF controls ↔ Palo Alto firewall evidence",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5178", "http://127.0.0.1:5178"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scf_brain_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        dict: Status indicator.
    """
    return {"status": "ok", "service": "scf-brain"}
