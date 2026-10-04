from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from veridex.api import serializers
from veridex.api.routes import router
from veridex.config import get_settings
from veridex.db.session import make_engine
from veridex.domain.errors import DomainError
from veridex.domain.taxonomy import default_taxonomy
from veridex.logging import configure_logging
from veridex.storage.local import LocalFilesystemStorage


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(title="Veridex", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.taxonomy = default_taxonomy()
    app.state.storage = LocalFilesystemStorage(settings.storage_root)
    app.state.serializers = serializers
    engine = make_engine(settings)
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    @app.middleware("http")
    async def db_session(request: Request, call_next):
        session = app.state.session_factory()
        request.state.session = session
        try:
            response = await call_next(request)
            return response
        finally:
            session.close()

    @app.exception_handler(DomainError)
    async def domain_error(_request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": {"code": "invalid_request", "message": str(exc.errors())}})

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
