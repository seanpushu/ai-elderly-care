"""FastAPI entry point for PausePal."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator

from app.analyzer import LiveAnalysisError, analyze_demo_message, analyze_live_message


PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = (PROJECT_DIR / "static").resolve()
INDEX_FILE = (STATIC_DIR / "index.html").resolve()

app = FastAPI(title="PausePal API")
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR), check_dir=False),
    name="static",
)


class AnalyzeRequest(BaseModel):
    text: str

    @validator("text", pre=True)
    def trim_and_validate_text(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("Text must be a string.")
        value = value.strip()
        if not value:
            raise ValueError("Text must not be empty after trimming.")
        if len(value) > 4000:
            raise ValueError("Text must be 4000 characters or fewer after trimming.")
        return value


@app.exception_handler(RequestValidationError)
async def readable_validation_error(_request: Any, exc: RequestValidationError) -> JSONResponse:
    """Keep API validation failures short and understandable."""
    error = exc.errors()[0] if exc.errors() else {}
    location = error.get("loc", ())
    message = error.get("msg", "")

    if "text" in location:
        if message in ("field required", "Field required"):
            detail = "Please include a text field in the request body."
        else:
            detail = message
    elif error.get("type") in ("json_invalid", "value_error.jsondecode"):
        detail = "Please send a valid JSON request body."
    else:
        detail = "Please send a JSON object containing a text field."

    return JSONResponse(status_code=422, content={"detail": detail})


def get_analysis_mode() -> str:
    """Return the configured analysis mode without silently changing it."""
    mode = os.getenv("PAUSEPAL_MODE", "demo").strip().lower()
    if mode in {"demo", "live"}:
        return mode
    raise HTTPException(
        status_code=503,
        detail="This analysis mode is unavailable. Use PAUSEPAL_MODE=demo or PAUSEPAL_MODE=live.",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    mode = os.getenv("PAUSEPAL_MODE", "demo").strip().lower()
    return {
        "status": "ok",
        "analysis_mode": mode if mode in {"demo", "live"} else "unavailable",
    }


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    mode = get_analysis_mode()

    if mode == "demo":
        return await analyze_demo_message(request.text)

    try:
        return await analyze_live_message(request.text)
    except LiveAnalysisError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
