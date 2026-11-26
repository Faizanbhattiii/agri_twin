"""
Main FastAPI Application for AgriTwin Pakistan.
"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agritwin.api.telemetry import router as telemetry_router
from agritwin.api.scenarios import router as scenarios_router
from agritwin.api.dashboard import router as dashboard_router
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
    app.include_router(dashboard_router)

    @app.get("/health", tags=["System"])
    def health_check() -> dict:
        """Service health check endpoint."""
        return {
            "status": "ok",
            "service": "AgriTwin Pakistan",
            "environment": settings.environment,
            "timezone": settings.timezone,
        }

    # Mount compiled React frontend if built
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="frontend")

    return app


app = create_app()
