"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.routers.analysis import router as analysis_router
from api.routers.users import router as users_router
from users.scheduler import start_scheduler, stop_scheduler

from config import get_api_config

setup_logging = __import__('logging_config', fromlist=['setup_logging', 'get_logger']).setup_logging
get_logger = __import__('logging_config', fromlist=['setup_logging', 'get_logger']).get_logger

api_config = get_api_config()

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
    title=api_config.title,
    description=api_config.description,
    version=api_config.version,
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
        "name": api_config.title,
        "version": api_config.version,
        "description": api_config.description,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
