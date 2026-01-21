"""Telemetry endpoints.

These are intentionally minimal and best-effort. They accept anonymous events from
frontend UX (guided tour, step navigation), but never block core work.

They forward to CloudLicenseManager.ping_usage(action=...).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any, Dict, Optional

from app.utils.telemetry import ping as telemetry_ping


router = APIRouter(prefix="/api/v1", tags=["telemetry"])


class TelemetryEvent(BaseModel):
    action: str
    details: Optional[Dict[str, Any]] = None


@router.post("/telemetry")
async def post_telemetry(event: TelemetryEvent, request: Request):
    # Best-effort only; never fail the caller.
    try:
        # Get app version from the FastAPI app instance
        app_version = getattr(request.app, 'version', None)
        # We currently only support the action dimension in the cloud ping.
        # details is accepted so we can expand later without breaking clients.
        telemetry_ping(event.action, app_version=app_version, details=event.details)
    except Exception:
        pass

    return {"ok": True}


@router.get("/telemetry")
async def get_telemetry():
    """Compatibility endpoint.

    The frontend is expected to POST, but some environments/tools may probe URLs
    with GET (e.g., link prefetchers, health checks). Returning 200 avoids noisy
    405 errors in the browser console.
    """

    return {"ok": True}
