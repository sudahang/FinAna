"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers.analysis import router as analysis_router

# Setup logging
from logging_config import setup_logging, get_logger

setup_logging(level=logging.INFO)
logger = get_logger(__name__)
logger.info("FinAna API starting...")

app = FastAPI(
    title="FinAna API",
    description="Investment Research Assistant API",
    version="0.1.0"
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
