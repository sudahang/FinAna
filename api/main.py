"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routers.analysis import router as analysis_router
from api.routers.users import router as users_router
from users.scheduler import start_scheduler, stop_scheduler

# Setup logging
from logging_config import setup_logging, get_logger

setup_logging(level=logging.INFO)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FinAna API starting...")
    start_scheduler()
    yield
    logger.info("FinAna API shutting down...")
    stop_scheduler()


app = FastAPI(
    title="FinAna API",
    description="Investment Research Assistant API",
    version="0.1.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(analysis_router)
app.include_router(users_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "FinAna API",
        "version": "0.1.0",
        "description": "Investment Research Assistant",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
