import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError  # noqa: F401  (kept default handling)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api import auth
from app.api.candidate_intelligence import (
    router as candidate_intelligence_router,
)
from app.api.career_profile import (
    router as career_profile_router,
)
from app.api.projects import (
    router as projects_router,
)
from app.api.resume_intelligence import (
    router as resume_intelligence_router,
)
from app.api.jobs import router as jobs_router
from app.api.rag import router as rag_router
from app.api.applications import router as applications_router
from app.api.follow_ups import router as follow_ups_router
from app.api.analytics import router as analytics_router
from app.api.interviews import router as interviews_router
from app.api.resumes import (
    router as resumes_router,
)
from app.core import database
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import limiter


log = logging.getLogger("app.request")

# Probes and API docs must never be throttled or a busy API could fail its own health check.
_UNLIMITED_PREFIXES = ("/health", "/version", "/docs", "/openapi.json")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


def create_app() -> FastAPI:
    settings = get_settings()
    settings.validate_for_runtime()

    configure_logging(
        getattr(logging, settings.log_level.upper(), None)
        if settings.log_level
        else (logging.DEBUG if settings.debug else logging.INFO)
    )

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    if settings.allowed_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
        ],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID", "Retry-After"],
    )

    @app.middleware("http")
    async def request_pipeline(request: Request, call_next):
        """Request id, global rate limit, security headers and structured access log."""
        request_id = request.headers.get("X-Request-ID", "")[:64] or uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.perf_counter()
        client = request.client.host if request.client else "unknown"

        limit = get_settings().api_rate_limit_per_minute
        if (
            limit > 0
            and request.method != "OPTIONS"
            and not request.url.path.startswith(_UNLIMITED_PREFIXES)
        ):
            retry_after = limiter.check(f"global:{client}", limit, 60)
            if retry_after is not None:
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Try again shortly."},
                    headers={"Retry-After": str(retry_after)},
                )
            else:
                response = await _call(call_next, request, request_id)
        else:
            response = await _call(call_next, request, request_id)

        response.headers["X-Request-ID"] = request_id
        for name, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)

        log.info(
            "request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": round(
                    (time.perf_counter() - start) * 1000,
                    1,
                ),
                "client": client,
            },
        )

        return response

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness: the process is up. Does not touch the database."""
        return {"status": "ok"}

    @app.get("/health/ready", tags=["meta"])
    def ready() -> JSONResponse:
        """Readiness: the database answers. Use this for load balancer / orchestrator probes."""
        try:
            with database.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:  # noqa: BLE001
            log.error("readiness check failed", exc_info=True)
            return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
        return JSONResponse(content={"status": "ready", "database": "ok"})

    @app.get("/version", tags=["meta"])
    def version() -> dict[str, str]:
        s = get_settings()
        return {"name": s.app_name, "version": s.app_version, "environment": s.environment}

    # API routers
    app.include_router(auth.router)
    app.include_router(career_profile_router)
    app.include_router(projects_router)
    app.include_router(resumes_router)
    app.include_router(resume_intelligence_router)
    app.include_router(candidate_intelligence_router)
    app.include_router(jobs_router)
    app.include_router(rag_router)
    app.include_router(applications_router)
    app.include_router(follow_ups_router)
    app.include_router(analytics_router)
    app.include_router(interviews_router)

    return app


async def _call(call_next, request: Request, request_id: str):
    """Run the app; turn unhandled errors into a JSON 500 that carries the request id."""
    try:
        return await call_next(request)
    except Exception:  # noqa: BLE001
        log.error("unhandled error", extra={"request_id": request_id, "path": request.url.path}, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )


app = create_app()
