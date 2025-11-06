#!/usr/bin/env python3
"""
launcher.py - Single-process launcher for Valido backend.

Starts FastAPI server and local worker in one process for Windows-native deployment.
"""

import os
import sys
import signal
import time
import uvicorn
from threading import Thread
from app.utils.logger import get_logger

logger = get_logger(__name__)


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    from local_worker import shutdown_worker
    shutdown_worker()
    sys.exit(0)


def start_worker():
    """Start the local worker in a background thread."""
    logger.info("Starting local worker thread")
    # Worker is initialized lazily when first task is submitted
    # Keep thread alive for task processing
    while True:
        time.sleep(1)  # Keep thread alive


def main():
    """Main entry point."""
    logger.info("Starting Valido launcher in single-process mode")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start worker thread
    worker_thread = Thread(target=start_worker, daemon=True, name="LocalWorker")
    worker_thread.start()
    logger.info("Worker thread started")

    # Import FastAPI app after worker is ready
    from app.main import app

    # Start FastAPI server
    logger.info("Starting FastAPI server on 0.0.0.0:8000")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()