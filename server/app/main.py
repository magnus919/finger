"""Finger server — FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .endpoints import read as read_ep, write as write_ep, auth as auth_ep
from . import storage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("finger")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: sweep expired plans, then bind."""
    swept = storage.sweep_expired()
    if swept:
        logger.info("Swept %d expired plans on startup", swept)
    yield


app = FastAPI(
    title="Finger Protocol Server",
    description="Modern finger protocol over HTTPS (RFC 1288 revival)",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(read_ep.router)
app.include_router(write_ep.router)
app.include_router(auth_ep.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
