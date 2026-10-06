"""Health check API endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel
from src.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Schema for health-check response."""

    status: str
    service: str


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Return service health status."""
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
    )
