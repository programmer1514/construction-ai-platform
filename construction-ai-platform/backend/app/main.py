"""ConstructAI - Multimodal Construction Intelligence Platform (FastAPI backend)."""
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .errors import AppError, error_body
from .routers import cracks, knowledge, planning, safety, site, valuation, weather

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("constructai")

app = FastAPI(
    title="ConstructAI - Multimodal Construction Intelligence Platform",
    version="1.0.0",
    description="Safety monitoring, crack analysis, planning, valuation, site assistant, weather advisory and knowledge assistant.",
)

app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status, content=error_body(exc.code, exc.message))


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    problems = []
    for e in exc.errors():
        field = ".".join(str(p) for p in e.get("loc", []) if p not in ("body", "query"))
        problems.append(f"{field or 'input'}: {e.get('msg', 'invalid value')}")
    return JSONResponse(status_code=422, content=error_body("validation_error", "Some inputs are invalid: " + "; ".join(problems[:5]), problems))


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content=error_body("internal_error", "Something went wrong on the server. Please try again."))


@app.get("/api/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "mode": "live" if settings.live else "demo",
        "model": settings.model if settings.live else None,
        "modules": ["safety", "cracks", "planning", "valuation", "site", "weather", "knowledge"],
    }


for r in (safety, cracks, planning, valuation, site, weather, knowledge):
    app.include_router(r.router)

# Serve the built frontend (frontend/dist) from the same server when it exists - handy for single-container deploys.
# Done via the 404 handler (not a "/" mount) so API routes keep correct 404 / 405 behaviour and JSON error bodies.
_dist = (Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()
_index = _dist / "index.html"

_MESSAGES = {404: ("not_found", "The requested resource was not found."), 405: ("method_not_allowed", "This HTTP method is not allowed for this endpoint.")}


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404 and request.method == "GET" and not request.url.path.startswith("/api") and _index.is_file():
        candidate = (_dist / request.url.path.lstrip("/")).resolve()
        if candidate.is_file() and _dist in candidate.parents:  # static asset (path-traversal safe)
            return FileResponse(candidate)
        return FileResponse(_index)  # single-page-app fallback
    code, message = _MESSAGES.get(exc.status_code, ("http_error", str(exc.detail)))
    return JSONResponse(status_code=exc.status_code, content=error_body(code, message))
