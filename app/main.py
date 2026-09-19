"""FastAPI entry point for PausePal."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.analyzer import (
    DEFAULT_MODEL,
    PROVIDER_NAME,
    AnalysisUnavailable,
    analyze_message,
    load_config,
)
from app.schemas import AnalysisResponse, AnalyzeRequest


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = (PROJECT_DIR / "static").resolve()
INDEX_FILE = (STATIC_DIR / "index.html").resolve()

app = FastAPI(title="PausePal API")
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR), check_dir=False),
    name="static",
)


_TEMPORARY_HOME = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>PausePal</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; line-height: 1.5;">
<h1>PausePal backend is running</h1>
<p>The message analysis page has not been added to this build yet.</p>
<p>API: <code>POST /api/analyze</code> with JSON <code>{"text": "..."}</code>.
Health: <a href="/health">/health</a>.</p>
</body>
</html>
"""


@app.exception_handler(RequestValidationError)
async def readable_validation_error(_request: Any, exc: RequestValidationError) -> JSONResponse:
    """Keep API validation failures short, English, and free of message content."""
    error = exc.errors()[0] if exc.errors() else {}
    location = error.get("loc", ())
    message = str(error.get("msg", ""))
    if message.startswith("Value error, "):
        message = message[len("Value error, "):]

    if "text" in location:
        if message in ("field required", "Field required"):
            detail = "Please include a text field in the request body."
        elif message.startswith("Text "):
            detail = message
        else:
            detail = "Text must be a string."
    elif error.get("type") in ("json_invalid", "value_error.jsondecode"):
        detail = "Please send a valid JSON request body."
    else:
        detail = "Please send a JSON object containing a text field."

    return JSONResponse(status_code=422, content={"detail": detail})


@app.exception_handler(AnalysisUnavailable)
async def analysis_unavailable(_request: Any, exc: AnalysisUnavailable) -> JSONResponse:
    """Model failures are reported as 503, never disguised as results."""
    return JSONResponse(status_code=503, content={"detail": exc.detail, "reason": exc.reason})


@app.get("/health")
async def health() -> dict[str, Any]:
    config = load_config()
    return {
        "status": "ok",
        "analysis_mode": "live",
        "analysis_available": config is not None,
        "provider": PROVIDER_NAME,
        "model": config.model if config else DEFAULT_MODEL,
    }


@app.get("/", include_in_schema=False)
async def home() -> Any:
    if INDEX_FILE.is_file():
        return FileResponse(INDEX_FILE)
    return HTMLResponse(_TEMPORARY_HOME, status_code=200)


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    return await analyze_message(request.text)
