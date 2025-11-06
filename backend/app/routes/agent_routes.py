from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.get("/download/windows")
async def download_windows_agent():
    """Download Windows agent executable."""
    logger.info("Downloading Windows agent")
    agent_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent.exe')
    
    # Security: Ensure path is absolute and within expected directory
    if not os.path.isabs(agent_path) or not agent_path.startswith(os.getcwd()):
        logger.error(f"Invalid agent path: {agent_path}")
        raise HTTPException(status_code=500, detail="Invalid agent path")
    
    if not os.path.exists(agent_path):
        logger.warning("Windows agent not built yet")
        raise HTTPException(
            status_code=404, 
            detail="Windows agent not built yet. Please build the agent first using: cd agent && build.ps1"
        )
    
    logger.info(f"Serving Windows agent: {agent_path}")
    return FileResponse(
        agent_path,
        media_type='application/octet-stream',
        filename='valido-agent.exe'
    )


@router.get("/download/mac")
async def download_mac_agent():
    """Download macOS agent executable."""
    logger.info("Downloading macOS agent")
    agent_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent')
    
    # Security: Ensure path is absolute and within expected directory
    if not os.path.isabs(agent_path) or not agent_path.startswith(os.getcwd()):
        logger.error(f"Invalid agent path: {agent_path}")
        raise HTTPException(status_code=500, detail="Invalid agent path")
    
    if not os.path.exists(agent_path):
        logger.warning("macOS agent not built yet")
        raise HTTPException(
            status_code=404,
            detail="macOS agent not built yet. Please build the agent first."
        )
    
    logger.info(f"Serving macOS agent: {agent_path}")
    return FileResponse(
        agent_path,
        media_type='application/octet-stream',
        filename='valido-agent'
    )


@router.get("/info")
async def agent_info():
    """Get agent build information."""
    logger.info("Getting agent info")
    windows_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent.exe')
    mac_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent')
    
    # Security checks for paths
    if not os.path.isabs(windows_path) or not windows_path.startswith(os.getcwd()):
        logger.error(f"Invalid Windows path: {windows_path}")
        raise HTTPException(status_code=500, detail="Invalid Windows path")
    if not os.path.isabs(mac_path) or not mac_path.startswith(os.getcwd()):
        logger.error(f"Invalid macOS path: {mac_path}")
        raise HTTPException(status_code=500, detail="Invalid macOS path")
    
    info = {
        "windows": {
            "available": os.path.exists(windows_path),
            "size": os.path.getsize(windows_path) if os.path.exists(windows_path) else 0
        },
        "mac": {
            "available": os.path.exists(mac_path),
            "size": os.path.getsize(mac_path) if os.path.exists(mac_path) else 0
        }
    }
    logger.info(f"Agent info: {info}")
    return info
