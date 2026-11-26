"""
Main FastAPI Application for AgriTwin Pakistan.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agritwin.api.telemetry import router as telemetry_router
from agritwin.api.scenarios import router as scenarios_router
from agritwin.core.config import settings
from agritwin.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup."""
    init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="AgriTwin Pakistan API",
        description="Hybrid Digital Twin of Pakistani Farmland for Wheat Monitoring & Yield Forecasting",
        version="0.6.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(telemetry_router)
    app.include_router(scenarios_router)

    @app.get("/health", tags=["System"])
    def health_check() -> dict:
        """Service health check endpoint."""
        return {
            "status": "ok",
            "service": "AgriTwin Pakistan",
            "environment": settings.environment,
            "timezone": settings.timezone,
        }

    return app


app = create_app()
