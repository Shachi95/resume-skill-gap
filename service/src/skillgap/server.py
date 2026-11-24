"""FastAPI server exposing the skill-gap pipeline over HTTP."""

from __future__ import annotations

import hmac
import os
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from skillgap.cli import compute_ranked
from skillgap.models import RankedGap

app = FastAPI(title="skillgap")


class AnalyzeRequest(BaseModel):
    """Request body for /analyze."""

    postings: list[str]
    resume: str = ""


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    """Reject requests whose X-API-Key does not match SKILLGAP_API_KEY."""
    expected = os.environ.get("SKILLGAP_API_KEY", "")
    if not expected or not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe; no auth required."""
    return {"status": "ok"}


@app.post("/analyze", dependencies=[Depends(require_api_key)])
def analyze(body: AnalyzeRequest) -> list[RankedGap]:
    """Return ranked skill gaps for the resume against the postings."""
    return compute_ranked(body.resume, body.postings)
