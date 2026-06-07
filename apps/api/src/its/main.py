from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="ITS Platform API", version="0.1.0")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Routers are mounted in later work packages (E9 / API-1, API-2):
    # from its.api.student import router as student_router
    # from its.api.teacher import router as teacher_router
    # app.include_router(student_router)
    # app.include_router(teacher_router)
    return app


app = create_app()
