"""
AWS S3 Handler
Handles connection, listing, and downloading PDFs from AWS S3 buckets
"""
from typing import List, Dict, Optional
import tempfile
import os
from datetime import datetime
from app.utils.logger import get_logger

logger = get_logger("AWSS3Handler")

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False
    logger.warning("boto3 not installed. AWS S3 features unavailable.")


class AWSS3Handler:
    """
    Modular handler for AWS S3 operations.
    Keeps AWS-specific logic separate and maintainable.
    """
    
    def __init__(self, access_key_id: str, secret_access_key: str, bucket_name: str, region: str = "us-east-1"):
        """
        Initialize AWS S3 handler.
        
        Args:
            access_key_id: AWS Access Key ID
            secret_access_key: AWS Secret Access Key
            bucket_name: S3 bucket name
            region: AWS region (default: us-east-1)
        """
        if not AWS_AVAILABLE:
            raise ImportError("boto3 package is required for AWS S3 features")
        
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.region = region
        
        self.s3_client = None
        self.s3_resource = None
        
        logger.info(f"AWSS3Handler initialized for bucket: {bucket_name} in region: {region}")
    
    def connect(self) -> bool:
        """
        Establish connection to AWS S3.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )
            
            # Create S3 resource for higher-level operations
            self.s3_resource = boto3.resource(
                's3',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )
            
            # Test connection by checking if bucket exists
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"✓ Connected to AWS S3 bucket: {self.bucket_name}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                logger.error(f"Bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                logger.error(f"Access denied to bucket '{self.bucket_name}'")
            else:
                logger.error(f"AWS S3 connection error: {e}")
            return False
        except NoCredentialsError:
            logger.error("AWS credentials not found or invalid")
            return False
        except Exception as e:
            logger.error(f"AWS S3 connection failed: {e}")
            return False
    
    def test_connection(self) -> Dict:
        """
        Test connection to AWS S3.
        
        Returns:
            Dict with success status and message
        """
        try:
            if self.connect():
                return {
                    'success': True,
                    'message': f'Successfully connected to AWS S3 bucket: {self.bucket_name}'
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
        List all PDF files in the S3 bucket.
        
        Args:
            prefix: Optional prefix to filter objects
            
        Returns:
            List of dicts with file information
        """
        try:
            if not self.s3_client:
                if not self.connect():
                    return []
            
            pdf_files = []
            
            # List objects with optional prefix
            paginator = self.s3_client.get_paginator('list_objects_v2')
            pages = paginator.paginate(Bucket=self.bucket_name, Prefix=prefix)
            
            for page in pages:
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    key = obj['Key']
                    if key.lower().endswith('.pdf'):
                        pdf_files.append({
                            'name': key,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'].isoformat() if obj.get('LastModified') else None,
                            'url': f"s3://{self.bucket_name}/{key}"
                        })
            
            logger.info(f"Found {len(pdf_files)} PDF files in S3 bucket")
            return pdf_files
            
        except Exception as e:
            logger.error(f"Error listing S3 objects: {e}")
            return []
    
    def download_file(self, object_key: str, destination_path: str) -> bool:
        """
        Download a single file from S3.
        
        Args:
            object_key: S3 object key (path) to download
            destination_path: Local path to save file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.s3_client:
                if not self.connect():
                    return False
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(self.bucket_name, object_key, destination_path)
            
            logger.info(f"Downloaded S3 object: {object_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading object '{object_key}': {e}")
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
            logger.info(f"Downloading {len(pdf_files)} PDFs from S3...")
            
            for pdf_info in pdf_files:
                object_key = pdf_info['name']
                # Use just the filename for local path
                local_filename = os.path.basename(object_key)
                local_path = os.path.join(temp_dir, local_filename)
                
                if self.download_file(object_key, local_path):
                    downloaded_files.append(local_path)
                else:
                    logger.warning(f"Failed to download: {object_key}")
            
            logger.info(f"Successfully downloaded {len(downloaded_files)} PDFs from S3")
            return downloaded_files
            
        except Exception as e:
            logger.error(f"Error in batch download: {e}")
            return downloaded_files
    
    def close(self):
        """Clean up resources."""
        # boto3 clients don't need explicit closing
        logger.info("AWS S3 connection closed")
