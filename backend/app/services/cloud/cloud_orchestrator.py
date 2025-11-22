"""
Cloud Storage Orchestrator
Central coordinator for all cloud storage providers (Azure, AWS, GCP).
Provides unified interface for downloading PDFs from any cloud source.
"""
from typing import List, Dict, Optional
import tempfile
import os
import shutil
from app.utils.logger import get_logger
from app.services.cloud.azure_blob_handler import AzureBlobHandler
from app.services.cloud.aws_s3_handler import AWSS3Handler
from app.services.cloud.gcp_storage_handler import GCPStorageHandler

logger = get_logger("CloudOrchestrator")


class CloudOrchestrator:
    """
    Orchestrates cloud storage operations across multiple providers.
    Keeps cloud logic centralized and separate from worker tasks.
    """
    
    @staticmethod
    def test_connection(provider: str, config: Dict) -> Dict:
        """
        Test connection to a cloud storage provider.
        
        Args:
            provider: Cloud provider name ('azure', 'aws', 'gcp')
            config: Provider-specific configuration
            
        Returns:
            Dict with success status and message
        """
        try:
            if provider == 'azure':
                handler = AzureBlobHandler(
                    connection_string=config.get('connection_string'),
                    container_name=config.get('container_name')
                )
                return handler.test_connection()
            
            elif provider == 'aws':
                handler = AWSS3Handler(
                    access_key_id=config.get('access_key_id'),
                    secret_access_key=config.get('secret_access_key'),
                    bucket_name=config.get('bucket_name'),
                    region=config.get('region', 'us-east-1')
                )
                return handler.test_connection()
            
            elif provider == 'gcp':
                handler = GCPStorageHandler(
                    service_account_json=config.get('service_account_json'),
                    bucket_name=config.get('bucket_name')
                )
                return handler.test_connection()
            
            else:
                return {
                    'success': False,
                    'message': f'Unknown provider: {provider}'
                }
                
        except Exception as e:
            logger.error(f"Error testing {provider} connection: {e}")
            return {
                'success': False,
                'message': f'Connection test failed: {str(e)}'
            }
    
    @staticmethod
    def list_files(provider: str, config: Dict, prefix: str = "") -> Dict:
        """
        List PDF files from a cloud storage provider.
        
        Args:
            provider: Cloud provider name ('azure', 'aws', 'gcp')
            config: Provider-specific configuration
            prefix: Optional prefix to filter files
            
        Returns:
            Dict with file list and metadata
        """
        try:
            handler = None
            
            if provider == 'azure':
                handler = AzureBlobHandler(
                    connection_string=config.get('connection_string'),
                    container_name=config.get('container_name')
                )
            
            elif provider == 'aws':
                handler = AWSS3Handler(
                    access_key_id=config.get('access_key_id'),
                    secret_access_key=config.get('secret_access_key'),
                    bucket_name=config.get('bucket_name'),
                    region=config.get('region', 'us-east-1')
                )
            
            elif provider == 'gcp':
                handler = GCPStorageHandler(
                    service_account_json=config.get('service_account_json'),
                    bucket_name=config.get('bucket_name')
                )
            
            else:
                return {
                    'success': False,
                    'message': f'Unknown provider: {provider}',
                    'files': []
                }
            
            files = handler.list_pdf_files(prefix)
            handler.close()
            
            return {
                'success': True,
                'provider': provider,
                'count': len(files),
                'files': files
            }
            
        except Exception as e:
            logger.error(f"Error listing files from {provider}: {e}")
            return {
                'success': False,
                'message': str(e),
                'files': []
            }
    
    @staticmethod
    def download_pdfs_to_temp(provider: str, config: Dict, prefix: str = "") -> Dict:
        """
        Download all PDFs from cloud storage to a temporary directory.
        This is the main method used by the automation worker.
        
        Args:
            provider: Cloud provider name ('azure', 'aws', 'gcp')
            config: Provider-specific configuration
            prefix: Optional prefix to filter files
            
        Returns:
            Dict with temp directory path and list of downloaded files
        """
        temp_dir = None
        handler = None
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix=f'valido_cloud_{provider}_')
            logger.info(f"Created temp directory for {provider}: {temp_dir}")
            
            # Initialize appropriate handler
            if provider == 'azure':
                handler = AzureBlobHandler(
                    connection_string=config.get('connection_string'),
                    container_name=config.get('container_name')
                )
            
            elif provider == 'aws':
                handler = AWSS3Handler(
                    access_key_id=config.get('access_key_id'),
                    secret_access_key=config.get('secret_access_key'),
                    bucket_name=config.get('bucket_name'),
                    region=config.get('region', 'us-east-1')
                )
            
            elif provider == 'gcp':
                handler = GCPStorageHandler(
                    service_account_json=config.get('service_account_json'),
                    bucket_name=config.get('bucket_name')
                )
            
            else:
                raise ValueError(f'Unknown provider: {provider}')
            
            # Download all PDFs
            downloaded_files = handler.download_all_pdfs(temp_dir, prefix)
            handler.close()
            
            if not downloaded_files:
                # Clean up empty temp dir
                shutil.rmtree(temp_dir, ignore_errors=True)
                return {
                    'success': False,
                    'message': 'No PDF files found or download failed',
                    'temp_dir': None,
                    'files': []
                }
            
            logger.info(f"Successfully downloaded {len(downloaded_files)} files from {provider}")
            
            return {
                'success': True,
                'temp_dir': temp_dir,
                'files': downloaded_files,
                'provider': provider,
                'count': len(downloaded_files)
            }
            
        except Exception as e:
            logger.error(f"Error downloading from {provider}: {e}")
            
            # Clean up on error
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            
            if handler:
                handler.close()
            
            return {
                'success': False,
                'message': str(e),
                'temp_dir': None,
                'files': []
            }
    
    @staticmethod
    def cleanup_temp_directory(temp_dir: str):
        """
        Clean up temporary directory after processing.
        
        Args:
            temp_dir: Path to temporary directory to remove
        """
        try:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temp directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory {temp_dir}: {e}")
