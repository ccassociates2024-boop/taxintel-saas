from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.service_name,
        version=settings.service_version,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.include_router(router, prefix="/api/v1")
    return app


app = create_app()

