"""
FatturaMVP - Main Application Entry Point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from sqlmodel import SQLModel
from app.models import *  # noqa: F401,F403
from app.api.v1.router import api_router

import logging
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup
    logger.info("FatturaMVP starting", version=settings.APP_VERSION)

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Seed default admin user if not exists
    await _seed_admin_user()

    logger.info("FatturaMVP ready")

    yield

    # Shutdown
    logger.info("FatturaMVP shutting down")
    await engine.dispose()


async def _seed_admin_user():
    """Create default admin user if none exists."""
    from app.db.session import async_session_maker
    from app.models.user import User
    from app.core.security import get_password_hash
    from sqlalchemy import select

    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.role == "admin").limit(1))
        if not result.scalar_one_or_none():
            admin = User(
                email="admin@fatturamvp.local",
                username="admin",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True,
                is_superuser=True,
            )
            db.add(admin)
            await db.commit()
            logger.info("Created default admin user: admin@fatturamvp.local / admin123")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Professional FatturaPA Invoice Management System with AI-powered extraction",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {e}"

    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "database": db_status,
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api": settings.API_V1_PREFIX,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
