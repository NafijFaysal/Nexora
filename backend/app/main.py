"""Application entry point.

Run locally, bound to this machine only (see PROJECT_GUIDE.md, security rule 13):

    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings, load_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="What If? Decision Intelligence Platform", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def limit_request_size(request: Request, call_next):
        # Checks the declared size only. Field limits in the schemas bound the payload
        # for requests that do not declare one.
        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > settings.max_request_bytes:
            return JSONResponse(status_code=413, content={"detail": "Request body is too large."})
        return await call_next(request)

    app.include_router(router)
    return app


app = create_app()
