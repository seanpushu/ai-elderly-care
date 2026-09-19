"""FastAPI entry point for the PausePal scaffold."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, validator

from app.analyzer import analyze_message


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


def require_demo_mode() -> str:
    """Reject unimplemented modes instead of silently returning demo results."""
    mode = os.getenv("PAUSEPAL_MODE", "demo").strip().lower()
    if mode == "demo":
        return mode
    if mode == "live":
        raise HTTPException(
            status_code=503,
            detail="Live analysis is unavailable because no AI integration is configured.",
        )
    raise HTTPException(
        status_code=503,
        detail="This analysis mode is unavailable. Use PAUSEPAL_MODE=demo.",
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "analysis_mode": "demo"}


@app.get("/", include_in_schema=False)
async def home() -> FileResponse:
    return FileResponse(INDEX_FILE)


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    require_demo_mode()
    return await analyze_message(request.text)
