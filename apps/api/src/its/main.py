from fastapi import FastAPI

from its.api.content import router as content_router
from its.api.errors import register_exception_handlers
from its.api.student import router as student_router
from its.api.teacher import router as teacher_router
from its.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="ITS Platform API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    register_exception_handlers(app)
    app.include_router(student_router)
    app.include_router(teacher_router)
    app.include_router(content_router)
    if settings.auth_dev_mode:  # DEV ONLY
        from its.api.dev import router as dev_router

        app.include_router(dev_router)
    return app


app = create_app()
