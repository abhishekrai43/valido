"""
Cloud Sources Routes
API endpoints for managing saved cloud storage configurations
Allows users to save/list/delete cloud credentials for reuse
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from datetime import datetime
from app.models import CloudSource
from app.db import get_session
from app.services.cloud.cloud_orchestrator import CloudOrchestrator
from app.utils.logger import get_logger

logger = get_logger("CloudSourcesRoutes")
router = APIRouter(prefix="/api/v1/cloud-sources", tags=["cloud-sources"])


@router.post("/")
def create_cloud_source(source: CloudSource, session: Session = Depends(get_session)):
    """
    Save a new cloud storage configuration.
    
    Args:
        source: CloudSource with name, provider, and config
        
    Returns:
        Created cloud source with ID
    """
    try:
        logger.info(f"Creating cloud source: {source.name} ({source.provider})")
        
        # Test connection before saving
        test_result = CloudOrchestrator.test_connection(source.provider, source.config)
        if not test_result.get('success'):
            raise HTTPException(
                status_code=400, 
                detail=f"Connection test failed: {test_result.get('message')}"
            )
        
        # Save to database
        session.add(source)
        session.commit()
        session.refresh(source)
        
        logger.info(f"✓ Cloud source created: {source.id}")
        return source
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating cloud source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[CloudSource])
def list_cloud_sources(session: Session = Depends(get_session)):
    """
    List all saved cloud storage configurations.
    
    Returns:
        List of cloud sources, ordered by last_used desc
    """
    try:
        statement = select(CloudSource).order_by(CloudSource.last_used.desc(), CloudSource.created_at.desc())
        sources = session.exec(statement).all()
        
        logger.info(f"Listed {len(sources)} cloud sources")
        return sources
        
    except Exception as e:
        logger.error(f"Error listing cloud sources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{source_id}")
def get_cloud_source(source_id: int, session: Session = Depends(get_session)):
    """
    Get a specific cloud source by ID.
    
    Args:
        source_id: Cloud source ID
        
    Returns:
        CloudSource object
    """
    try:
        source = session.get(CloudSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Cloud source not found")
        
        return source
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cloud source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{source_id}")
def update_cloud_source(source_id: int, updated_source: CloudSource, session: Session = Depends(get_session)):
    """
    Update a cloud source configuration.
    
    Args:
        source_id: Cloud source ID
        updated_source: Updated cloud source data
        
    Returns:
        Updated cloud source
    """
    try:
        source = session.get(CloudSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Cloud source not found")
        
        # Test new configuration before saving
        test_result = CloudOrchestrator.test_connection(updated_source.provider, updated_source.config)
        if not test_result.get('success'):
            raise HTTPException(
                status_code=400, 
                detail=f"Connection test failed: {test_result.get('message')}"
            )
        
        # Update fields
        source.name = updated_source.name
        source.provider = updated_source.provider
        source.config = updated_source.config
        
        session.add(source)
        session.commit()
        session.refresh(source)
        
        logger.info(f"✓ Cloud source updated: {source_id}")
        return source
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating cloud source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{source_id}")
def delete_cloud_source(source_id: int, session: Session = Depends(get_session)):
    """
    Delete a cloud source.
    
    Args:
        source_id: Cloud source ID
        
    Returns:
        Success message
    """
    try:
        source = session.get(CloudSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Cloud source not found")
        
        session.delete(source)
        session.commit()
        
        logger.info(f"✓ Cloud source deleted: {source_id}")
        return {"success": True, "message": "Cloud source deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting cloud source: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{source_id}/test")
def test_cloud_source_connection(source_id: int, session: Session = Depends(get_session)):
    """
    Test connection for a saved cloud source.
    
    Args:
        source_id: Cloud source ID
        
    Returns:
        Connection test result
    """
    try:
        source = session.get(CloudSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Cloud source not found")
        
        result = CloudOrchestrator.test_connection(source.provider, source.config)
        
        # Update last_used timestamp on successful test
        if result.get('success'):
            source.last_used = datetime.utcnow()
            session.add(source)
            session.commit()
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing cloud source: {e}")
        raise HTTPException(status_code=500, detail=str(e))
