"""
Google Cloud Storage Handler
Handles connection, listing, and downloading PDFs from GCP Cloud Storage buckets
"""
from typing import List, Dict, Optional
import tempfile
import os
import json
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger("GCPStorageHandler")

try:
    from google.cloud import storage
    from google.oauth2 import service_account
    from google.api_core.exceptions import GoogleAPIError, NotFound, Forbidden
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False
    logger.warning("google-cloud-storage not installed. GCP Storage features unavailable.")


class GCPStorageHandler:
    """
    Modular handler for Google Cloud Storage operations.
    Keeps GCP-specific logic separate and maintainable.
    """
    
    def __init__(self, service_account_json: str, bucket_name: str):
        """
        Initialize GCP Storage handler.
        
        Args:
            service_account_json: Service account JSON key (as string)
            bucket_name: GCS bucket name
        """
        if not GCP_AVAILABLE:
            raise ImportError("google-cloud-storage package is required for GCP features")
        
        self.service_account_json = service_account_json
        self.bucket_name = bucket_name
        
        self.storage_client = None
        self.bucket = None
        
        logger.info(f"GCPStorageHandler initialized for bucket: {bucket_name}")
    
    def connect(self) -> bool:
        """
        Establish connection to GCP Cloud Storage.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Parse service account JSON
            credentials_dict = json.loads(self.service_account_json)
            
            # Create credentials from service account
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict
            )
            
            # Create storage client
            self.storage_client = storage.Client(
                credentials=credentials,
                project=credentials_dict.get('project_id')
            )
            
            # Get bucket
            self.bucket = self.storage_client.bucket(self.bucket_name)
            
            # Test connection by checking if bucket exists
            if self.bucket.exists():
                logger.info(f"✓ Connected to GCP bucket: {self.bucket_name}")
                return True
            else:
                logger.error(f"Bucket '{self.bucket_name}' does not exist")
                return False
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid service account JSON: {e}")
            return False
        except NotFound:
            logger.error(f"Bucket '{self.bucket_name}' not found")
            return False
        except Forbidden:
            logger.error(f"Access denied to bucket '{self.bucket_name}'")
            return False
        except Exception as e:
            logger.error(f"GCP connection failed: {e}")
            return False
    
    def test_connection(self) -> Dict:
        """
        Test connection to GCP Cloud Storage.
        
        Returns:
            Dict with success status and message
        """
        try:
            if self.connect():
                return {
                    'success': True,
                    'message': f'Successfully connected to GCP bucket: {self.bucket_name}'
                }
            else:
                return {
                    'success': False,
                    'message': 'Bucket does not exist or credentials invalid'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection error: {str(e)}'
            }
    
    def list_pdf_files(self, prefix: str = "") -> List[Dict]:
        """
        List all PDF files in the GCS bucket.
        
        Args:
            prefix: Optional prefix to filter blobs
            
        Returns:
            List of dicts with file information
        """
        try:
            if not self.bucket:
                if not self.connect():
                    return []
            
            pdf_files = []
            
            # List blobs with optional prefix
            blobs = self.bucket.list_blobs(prefix=prefix)
            
            for blob in blobs:
                if blob.name.lower().endswith('.pdf'):
                    pdf_files.append({
                        'name': blob.name,
                        'size': blob.size,
                        'last_modified': blob.updated.isoformat() if blob.updated else None,
                        'url': f"gs://{self.bucket_name}/{blob.name}"
                    })
            
            logger.info(f"Found {len(pdf_files)} PDF files in GCP bucket")
            return pdf_files
            
        except Exception as e:
            logger.error(f"Error listing GCS blobs: {e}")
            return []
    
    def download_file(self, blob_name: str, destination_path: str) -> bool:
        """
        Download a single file from GCS.
        
        Args:
            blob_name: Name of blob to download
            destination_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.bucket:
                if not self.connect():
                    return False
            
            # Get blob
            blob = self.bucket.blob(blob_name)
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Download blob
            blob.download_to_filename(destination_path)
            
            logger.info(f"Downloaded GCS blob: {blob_name}")
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
            logger.info(f"Downloading {len(pdf_files)} PDFs from GCS...")
            
            for pdf_info in pdf_files:
                blob_name = pdf_info['name']
                # Use just the filename for local path
                local_filename = os.path.basename(blob_name)
                local_path = os.path.join(temp_dir, local_filename)
                
                if self.download_file(blob_name, local_path):
                    downloaded_files.append(local_path)
                else:
                    logger.warning(f"Failed to download: {blob_name}")
            
            logger.info(f"Successfully downloaded {len(downloaded_files)} PDFs from GCS")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error in batch download: {e}")
            return downloaded_files
    
    def close(self):
        """Clean up resources."""
        if self.storage_client:
            self.storage_client.close()
            logger.info("GCP connection closed")
