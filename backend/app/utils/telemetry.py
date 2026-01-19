"""Telemetry utilities.

Goals:
- Best-effort only: telemetry must never break app behavior.
- Low noise: optional de-dupe for high-frequency events.
- Works in PyInstaller exe mode.

This module intentionally has no FastAPI dependencies (safe to import anywhere).
"""

from __future__ import annotations

import os
import threading
import time
from typing import Optional

from app.utils.cloud_license_manager import CloudLicenseManager


def _stamp_dir() -> str:
    # Where we store lightweight state for telemetry de-dupe.
    # Prefer a user-specific folder (HOME/.valido) to be stable across installs.
    base = os.environ.get("VALIDO_STATE_DIR")
    if base:
        return base

    home = os.path.expanduser("~")
    return os.path.join(home, ".valido")


def _stamp_path(key: str) -> str:
    safe = "".join((c if c.isalnum() or c in ("-", "_", ".") else "_") for c in key)
    return os.path.join(_stamp_dir(), f"telemetry_{safe}.stamp")


def _read_stamp(path: str) -> Optional[float]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = (f.read() or "").strip()
        return float(raw)
    except Exception:
        return None


def _write_stamp(path: str, ts: float) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(str(ts))
    except Exception:
        # never fail
        return


def get_app_version(fallback: str = "unknown") -> str:
    """Best-effort version resolution.

    Priority:
    1) VALIDO_APP_VERSION env var (set at build/runtime)
    2) fallback argument
    """

    try:
        v = (os.environ.get("VALIDO_APP_VERSION") or "").strip()
        return v or fallback
    except Exception:
        return fallback


def ping(
    action: str,
    app_version: Optional[str] = None,
    *,
    dedupe_window_s: Optional[int] = None,
    dedupe_key: Optional[str] = None,
) -> None:
    """Fire-and-forget usage ping.

    Args:
        action: event/action name
        app_version: version string (optional). If omitted, resolved via get_app_version().
        dedupe_window_s: if set, skip pings within this number of seconds.
        dedupe_key: override stamp key used by de-dupe.

    Returns:
        None. Never raises.
    """

    try:
        version = app_version or get_app_version()

        # Optional de-dupe
        if dedupe_window_s is not None and dedupe_window_s > 0:
            key = dedupe_key or action
            path = _stamp_path(key)
            last = _read_stamp(path)
            now = time.time()
            if last is not None and (now - last) < float(dedupe_window_s):
                return
            _write_stamp(path, now)

        def _do_ping():
            try:
                CloudLicenseManager.ping_usage(version, action)
            except Exception:
                return

        threading.Thread(target=_do_ping, daemon=True).start()
    except Exception:
        return
