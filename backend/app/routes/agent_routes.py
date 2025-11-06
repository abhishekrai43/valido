from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.get("/download/windows")
async def download_windows_agent():
    """Download Windows agent executable."""
    agent_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent.exe')
    
    if not os.path.exists(agent_path):
        raise HTTPException(
            status_code=404, 
            detail="Windows agent not built yet. Please build the agent first using: cd agent && build.ps1"
        )
    
    return FileResponse(
        agent_path,
        media_type='application/octet-stream',
        filename='valido-agent.exe'
    )


@router.get("/download/mac")
async def download_mac_agent():
    """Download macOS agent executable."""
    agent_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent')
    
    if not os.path.exists(agent_path):
        raise HTTPException(
            status_code=404,
            detail="macOS agent not built yet. Please build the agent first."
        )
    
    return FileResponse(
        agent_path,
        media_type='application/octet-stream',
        filename='valido-agent'
    )


@router.get("/info")
async def agent_info():
    """Get agent build information."""
    windows_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent.exe')
    mac_path = os.path.join(os.getcwd(), 'agent', 'dist', 'valido-agent')
    
    return {
        "windows": {
            "available": os.path.exists(windows_path),
            "size": os.path.getsize(windows_path) if os.path.exists(windows_path) else 0
        },
        "mac": {
            "available": os.path.exists(mac_path),
            "size": os.path.getsize(mac_path) if os.path.exists(mac_path) else 0
        }
    }
