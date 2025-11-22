"""
Cloud Storage Routes
API endpoints for testing connections and listing files from cloud storage providers
Kept separate from main validation routes for modularity
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.cloud.cloud_orchestrator import CloudOrchestrator
from app.utils.logger import get_logger

logger = get_logger("CloudStorageRoutes")
router = APIRouter(prefix="/api/v1/cloud", tags=["cloud-storage"])


# Request Models
class AzureConfig(BaseModel):
    connection_string: str
    container_name: str


class AWSConfig(BaseModel):
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    region: Optional[str] = "us-east-1"


class GCPConfig(BaseModel):
    service_account_json: str
    bucket_name: str


class CloudConnectionTest(BaseModel):
    provider: str  # 'azure', 'aws', or 'gcp'
    config: Dict[str, Any]


class CloudFileList(BaseModel):
    provider: str
    config: Dict[str, Any]
    prefix: Optional[str] = ""


# Routes
@router.post("/test-connection")
def test_cloud_connection(request: CloudConnectionTest):
    """
    Test connection to a cloud storage provider.
    
    Args:
        request: CloudConnectionTest with provider and config
        
    Returns:
        Connection test result
    """
    try:
        logger.info(f"Testing connection to {request.provider}")
        result = CloudOrchestrator.test_connection(request.provider, request.config)
        
        if result['success']:
            logger.info(f"✓ {request.provider} connection successful")
        else:
            logger.warning(f"✗ {request.provider} connection failed: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in test_cloud_connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/list-files")
def list_cloud_files(request: CloudFileList):
    """
    List PDF files from a cloud storage provider.
    
    Args:
        request: CloudFileList with provider, config, and optional prefix
        
    Returns:
        List of PDF files with metadata
    """
    try:
        logger.info(f"Listing files from {request.provider}")
        result = CloudOrchestrator.list_files(
            request.provider,
            request.config,
            request.prefix
        )
        
        if result['success']:
            logger.info(f"Found {result['count']} files in {request.provider}")
        else:
            logger.warning(f"Failed to list files from {request.provider}: {result.get('message')}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in list_cloud_files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers")
def get_supported_providers():
    """
    Get list of supported cloud storage providers.
    
    Returns:
        List of provider information
    """
    return {
        'providers': [
            {
                'id': 'azure',
                'name': 'Azure Blob Storage',
                'icon': '/enterprise-icons/azure-icon.png',
                'fields': [
                    {'name': 'connection_string', 'label': 'Connection String', 'type': 'textarea', 'required': True, 'placeholder': 'DefaultEndpointsProtocol=https;AccountName=...'},
                    {'name': 'container_name', 'label': 'Container Name', 'type': 'text', 'required': True}
                ]
            },
            {
                'id': 'aws',
                'name': 'AWS S3',
                'icon': '/enterprise-icons/aws-icon.png',
                'fields': [
                    {'name': 'access_key_id', 'label': 'Access Key ID', 'type': 'text', 'required': True},
                    {'name': 'secret_access_key', 'label': 'Secret Access Key', 'type': 'password', 'required': True},
                    {'name': 'bucket_name', 'label': 'Bucket Name', 'type': 'text', 'required': True},
                    {'name': 'region', 'label': 'Region', 'type': 'text', 'required': False, 'default': 'us-east-1'}
                ]
            },
            {
                'id': 'gcp',
                'name': 'Google Cloud Storage',
                'icon': '/enterprise-icons/gcp-icon.png',
                'fields': [
                    {'name': 'service_account_json', 'label': 'Service Account JSON', 'type': 'textarea', 'required': True},
                    {'name': 'bucket_name', 'label': 'Bucket Name', 'type': 'text', 'required': True}
                ]
            }
        ]
    }
