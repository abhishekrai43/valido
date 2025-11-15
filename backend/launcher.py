#!/usr/bin/env python3
"""
launcher.py - Single-process launcher for Valido backend.

Starts FastAPI server and local worker in one process for Windows-native deployment.
"""

import os
import sys
import signal
import time
import socket
import uvicorn
import webbrowser
from threading import Thread
from app.utils.logger import get_logger

logger = get_logger(__name__)


def get_local_ip():
    """Get the local IP address for network access."""
    try:
        # Create a socket to get the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connect to Google DNS
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "192.168.1.100"  # Fallback


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


def open_browser(url):
    """Open the browser to the given URL after a short delay."""
    time.sleep(2)  # Wait for server to be ready
    try:
        webbrowser.open(url)
        logger.info(f"Opened browser to {url}")
    except Exception as e:
        logger.error(f"Failed to open browser: {e}")


def main():
    """Main entry point."""
    logger.info("Starting Valido launcher in single-process mode")

    # Get network info
    local_ip = get_local_ip()
    local_url = "http://localhost:8000"
    network_url = f"http://{local_ip}:8000"

    # Show user-friendly startup message (will be hidden in windowed mode)
    print("=" * 60)
    print("🚀 VALIDO - Document Validation Server")
    print("=" * 60)
    print("Starting server...")
    print("")
    print("📱 Web Interface: {}".format(local_url))
    print("🌐 Network Access: {}".format(network_url))
    print("")
    print("Opening browser automatically...")
    print("=" * 60)
    print("")

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start worker thread
    worker_thread = Thread(target=start_worker, daemon=True, name="LocalWorker")
    worker_thread.start()
    logger.info("Worker thread started")

    # Open browser in background thread
    browser_thread = Thread(target=open_browser, args=(local_url,), daemon=True, name="BrowserOpener")
    browser_thread.start()

    # Import FastAPI app after worker is ready
    from app.main import app

    # Start FastAPI server
    logger.info("Starting FastAPI server on 0.0.0.0:8000")
    
    # Configure uvicorn logging for windowed app (no tty)
    import logging
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["default"], "level": "INFO"},
        },
    }
    
    uvicorn.run(
        app,
        host="127.0.0.1",  # Localhost only
        port=8000,
        log_level="info",
        access_log=True,
        log_config=logging_config
    )


if __name__ == "__main__":
    main()