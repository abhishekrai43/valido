"""
Azure Blob Storage Handler
Handles connection, listing, and downloading PDFs from Azure Blob Storage
"""
from typing import List, Dict, Optional, BinaryIO
import tempfile
import os
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger("AzureBlobHandler")

try:
    from azure.storage.blob import BlobServiceClient, ContainerClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("azure-storage-blob not installed. Azure Blob Storage features unavailable.")


class AzureBlobHandler:
    """
    Modular handler for Azure Blob Storage operations.
    Keeps Azure-specific logic separate and maintainable.
    """
    
    def __init__(self, connection_string: str, container_name: str):
        """
        Initialize Azure Blob Storage handler.
        
        Args:
            connection_string: Azure Storage connection string (from Azure Portal)
            container_name: Container name to access
        """
        if not AZURE_AVAILABLE:
            raise ImportError("azure-storage-blob package is required for Azure features")
        
        self.connection_string = connection_string
        self.container_name = container_name
        
        self.blob_service_client: Optional[BlobServiceClient] = None
        self.container_client: Optional[ContainerClient] = None
        
        logger.info(f"AzureBlobHandler initialized for container: {container_name}")
    
    def connect(self) -> bool:
        """
        Establish connection to Azure Blob Storage.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
            self.container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            # Test connection by checking if container exists
            exists = self.container_client.exists()
            if exists:
                logger.info(f"✓ Connected to Azure container: {self.container_name}")
                return True
            else:
                logger.error(f"Container '{self.container_name}' does not exist")
                return False
                
        except Exception as e:
            logger.error(f"Azure connection failed: {e}")
            return False
    
    def test_connection(self) -> Dict:
        """
        Test connection to Azure Blob Storage.
        
        Returns:
            Dict with success status and message
        """
        try:
            if self.connect():
                return {
                    'success': True,
                    'message': f'Successfully connected to Azure container: {self.container_name}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Container does not exist or credentials invalid'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection error: {str(e)}'
            }
    
    def list_pdf_files(self, prefix: str = "") -> List[Dict]:
        """
        List all PDF files in the container.
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of dicts with file information
        """
        try:
            if not self.container_client:
                if not self.connect():
                    return []
            
            pdf_files = []
            blobs = self.container_client.list_blobs(name_starts_with=prefix)
            
            for blob in blobs:
                if blob.name.lower().endswith('.pdf'):
                    # Get blob URL directly from the blob client
                    blob_client = self.container_client.get_blob_client(blob.name)
                    pdf_files.append({
                        'name': blob.name,
                        'size': blob.size,
                        'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                        'url': blob_client.url
                    })
            
            logger.info(f"Found {len(pdf_files)} PDF files in Azure container")
            return pdf_files
            
        except Exception as e:
            logger.error(f"Error listing Azure blobs: {e}")
            return []
    
    def download_file(self, blob_name: str, destination_path: str) -> bool:
        """
        Download a single file from Azure Blob Storage.
        
        Args:
            blob_name: Name of blob to download
            destination_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.container_client:
                if not self.connect():
                    return False
            
            blob_client = self.container_client.get_blob_client(blob_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Download blob
            with open(destination_path, "wb") as file:
                download_stream = blob_client.download_blob()
                file.write(download_stream.readall())
            
            logger.info(f"Downloaded Azure blob: {blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading blob '{blob_name}': {e}")
            return False
    
    def download_all_pdfs(self, temp_dir: str, prefix: str = "") -> List[str]:
        """
        Download all PDF files to a temporary directory.
        
        Args:
            temp_dir: Temporary directory to download files
            prefix: Optional prefix to filter files
            
        Returns:
            List of downloaded file paths
        """
        downloaded_files = []
        
        try:
            pdf_files = self.list_pdf_files(prefix)
            logger.info(f"Downloading {len(pdf_files)} PDFs from Azure...")
            
            for pdf_info in pdf_files:
                blob_name = pdf_info['name']
                # Use just the filename for local path
                local_filename = os.path.basename(blob_name)
                local_path = os.path.join(temp_dir, local_filename)
                
                if self.download_file(blob_name, local_path):
                    downloaded_files.append(local_path)
                else:
                    logger.warning(f"Failed to download: {blob_name}")
            
            logger.info(f"Successfully downloaded {len(downloaded_files)} PDFs from Azure")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error in batch download: {e}")
            return downloaded_files
    
    def close(self):
        """Clean up resources."""
        if self.blob_service_client:
            self.blob_service_client.close()
            logger.info("Azure connection closed")
