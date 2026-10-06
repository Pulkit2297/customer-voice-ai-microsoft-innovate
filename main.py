"""CustomerVoice AI - Main Application Entrypoint."""

import uvicorn
from fastapi import FastAPI
from api.health import router as health_router
from src.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Customer Voice Intelligence Platform",
    version="0.1.0",
)

# Register routers
app.include_router(health_router)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True if settings.APP_ENV == "development" else False,
    )
