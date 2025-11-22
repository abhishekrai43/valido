"""
WebSocket endpoint for real-time job status updates.
Enterprise-grade push notifications instead of polling.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import asyncio
import json
from app.utils.logger import get_logger

logger = get_logger("WebSocket")

router = APIRouter()

# Connection pool - all active WebSocket clients
active_connections: Set[WebSocket] = set()


@router.websocket("/ws/job-status")
async def websocket_job_status(websocket: WebSocket):
    """
    WebSocket endpoint for real-time job status updates.
    Pushes updates instantly when jobs start/complete instead of polling.
    """
    await websocket.accept()
    active_connections.add(websocket)
    client_id = id(websocket)
    logger.info(f"WebSocket client {client_id} connected. Total connections: {len(active_connections)}")
    
    try:
        # Keep connection alive with ping/pong
        while True:
            # Wait for any message from client (heartbeat)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back to confirm connection is alive
                await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Send keepalive ping
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info(f"WebSocket client {client_id} disconnected. Remaining: {len(active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        active_connections.discard(websocket)


async def broadcast_job_status(watch_folder_id: int, status: str, data: dict = None):
    """
    Broadcast job status update to all connected WebSocket clients.
    Called by worker when job state changes.
    """
    message = {
        "type": "job_status",
        "watch_folder_id": watch_folder_id,
        "status": status,
        "data": data or {},
        "timestamp": asyncio.get_event_loop().time()
    }
    
    # Send to all connected clients
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to client {id(connection)}: {e}")
            disconnected.add(connection)
    
    # Clean up dead connections
    for conn in disconnected:
        active_connections.discard(conn)
    
    if active_connections:
        logger.info(f"Broadcasted job status for folder {watch_folder_id}: {status} to {len(active_connections)} clients")


def broadcast_job_status_sync(watch_folder_id: int, status: str, data: dict = None):
    """
    Synchronous wrapper for broadcast_job_status.
    Can be called from non-async worker threads.
    """
    try:
        # Get the running event loop or create one
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule the coroutine
            asyncio.create_task(broadcast_job_status(watch_folder_id, status, data))
        else:
            # Run in new event loop
            loop.run_until_complete(broadcast_job_status(watch_folder_id, status, data))
    except RuntimeError:
        # No event loop in current thread - skip broadcast
        logger.warning(f"Cannot broadcast job status - no event loop available")
