"""
Storage service for certificate files using S3/MinIO
"""
import logging
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
from minio import Minio
from minio.error import S3Error
import io

from config import config

logger = logging.getLogger(__name__)

class StorageService:
    """Storage service abstraction for S3/MinIO operations"""
    
    def __init__(self):
        self.backend = config.storage.backend
        self.bucket_name = config.storage.bucket_name
        self.s3_client = None
        self.minio_client = None
        
    async def initialize(self):
        """Initialize the storage backend"""
        try:
            if self.backend == "s3":
                await self._initialize_s3()
            elif self.backend == "minio":
                await self._initialize_minio()
            else:
                raise ValueError(f"Unsupported storage backend: {self.backend}")
            
            # Ensure bucket exists
            await self._ensure_bucket_exists()
            
            logger.info(f"Storage service initialized with backend: {self.backend}")
            
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {e}")
            raise
    
    async def _initialize_s3(self):
        """Initialize AWS S3 client"""
        try:
            # Configure boto3 for S3 compatibility
            boto_config = Config(
                signature_version="s3v4",
                retries={'max_attempts': 3},
                connect_timeout=10,
                read_timeout=30
            )
            
            # Handle MinIO endpoint override for S3-compatible services
            if config.storage.s3_endpoint_url:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=config.storage.s3_endpoint_url,
                    aws_access_key_id=config.storage.minio_access_key,
                    aws_secret_access_key=config.storage.minio_secret_key,
                    region_name=config.storage.aws_region,
                    config=boto_config
                )
            else:
                # Standard AWS S3
                self.s3_client = boto3.client(
                    's3',
                    aws_access_key_id=config.storage.aws_access_key_id,
                    aws_secret_access_key=config.storage.aws_secret_access_key,
                    region_name=config.storage.aws_region,
                    config=boto_config
                )
            
            logger.info("S3 client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            raise
    
    async def _initialize_minio(self):
        """Initialize MinIO client"""
        try:
            self.minio_client = Minio(
                endpoint=config.storage.minio_endpoint,
                access_key=config.storage.minio_access_key,
                secret_key=config.storage.minio_secret_key,
                secure=config.storage.minio_secure
            )
            
            logger.info("MinIO client initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {e}")
            raise
    
    async def _ensure_bucket_exists(self):
        """Ensure the certificates bucket exists"""
        try:
            if self.backend == "s3" and self.s3_client:
                # Check if bucket exists
                try:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    logger.info(f"S3 bucket '{self.bucket_name}' exists")
                except ClientError as e:
                    error_code = int(e.response['Error']['Code'])
                    if error_code == 404:
                        # Create bucket
                        self.s3_client.create_bucket(Bucket=self.bucket_name)
                        logger.info(f"Created S3 bucket: {self.bucket_name}")
                    else:
                        raise
            
            elif self.backend == "minio" and self.minio_client:
                # Check if bucket exists
                if not self.minio_client.bucket_exists(self.bucket_name):
                    self.minio_client.make_bucket(self.bucket_name)
                    logger.info(f"Created MinIO bucket: {self.bucket_name}")
                else:
                    logger.info(f"MinIO bucket '{self.bucket_name}' exists")
                    
        except Exception as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            raise
    
    async def upload_file(
        self, 
        file_data: bytes, 
        file_name: str, 
        content_type: str = "application/pdf",
        metadata: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Upload file to storage backend"""
        try:
            # Calculate file hash
            file_hash = hashlib.sha256(file_data).hexdigest()
            file_size = len(file_data)
            
            # Prepare metadata
            upload_metadata = {
                "Content-Type": content_type,
                "X-Certificate-Hash": file_hash,
                "X-Upload-Timestamp": datetime.utcnow().isoformat()
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            if self.backend == "s3" and self.s3_client:
                # Upload to S3
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=file_name,
                    Body=file_data,
                    ContentType=content_type,
                    Metadata=upload_metadata
                )
                
                file_url = f"s3://{self.bucket_name}/{file_name}"
                
            elif self.backend == "minio" and self.minio_client:
                # Upload to MinIO
                self.minio_client.put_object(
                    bucket_name=self.bucket_name,
                    object_name=file_name,
                    data=io.BytesIO(file_data),
                    length=file_size,
                    content_type=content_type,
                    metadata=upload_metadata
                )
                
                file_url = f"minio://{self.bucket_name}/{file_name}"
            
            else:
                raise RuntimeError("No storage client available")
            
            logger.info(f"File uploaded successfully: {file_name}")
            
            return {
                "file_url": file_url,
                "file_size": file_size,
                "file_hash": file_hash,
                "content_type": content_type
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
    
    async def generate_download_url(
        self, 
        file_name: str, 
        expiry_seconds: Optional[int] = None
    ) -> str:
        """Generate pre-signed download URL"""
        try:
            expiry = expiry_seconds or config.storage.presigned_url_expiry
            
            if self.backend == "s3" and self.s3_client:
                # Generate S3 pre-signed URL
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket_name, 'Key': file_name},
                    ExpiresIn=expiry
                )
                
            elif self.backend == "minio" and self.minio_client:
                # Generate MinIO pre-signed URL
                url = self.minio_client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=file_name,
                    expires=timedelta(seconds=expiry)
                )
            
            else:
                raise RuntimeError("No storage client available")
            
            logger.info(f"Generated download URL for: {file_name}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate download URL: {e}")
            raise
    
    async def delete_file(self, file_name: str) -> bool:
        """Delete file from storage"""
        try:
            if self.backend == "s3" and self.s3_client:
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=file_name
                )
                
            elif self.backend == "minio" and self.minio_client:
                self.minio_client.remove_object(
                    bucket_name=self.bucket_name,
                    object_name=file_name
                )
            
            else:
                raise RuntimeError("No storage client available")
            
            logger.info(f"File deleted successfully: {file_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False
    
    async def file_exists(self, file_name: str) -> bool:
        """Check if file exists in storage"""
        try:
            if self.backend == "s3" and self.s3_client:
                try:
                    self.s3_client.head_object(
                        Bucket=self.bucket_name,
                        Key=file_name
                    )
                    return True
                except ClientError:
                    return False
                    
            elif self.backend == "minio" and self.minio_client:
                try:
                    self.minio_client.stat_object(
                        bucket_name=self.bucket_name,
                        object_name=file_name
                    )
                    return True
                except S3Error:
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to check file existence: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get storage service status"""
        try:
            status = {
                "backend": self.backend,
                "bucket": self.bucket_name,
                "connected": False,
                "bucket_exists": False
            }
            
            if self.backend == "s3" and self.s3_client:
                # Test S3 connection
                try:
                    self.s3_client.head_bucket(Bucket=self.bucket_name)
                    status["connected"] = True
                    status["bucket_exists"] = True
                except ClientError:
                    status["connected"] = True
                    status["bucket_exists"] = False
                except Exception:
                    status["connected"] = False
                    
            elif self.backend == "minio" and self.minio_client:
                # Test MinIO connection
                try:
                    bucket_exists = self.minio_client.bucket_exists(self.bucket_name)
                    status["connected"] = True
                    status["bucket_exists"] = bucket_exists
                except Exception:
                    status["connected"] = False
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get storage status: {e}")
            return {
                "backend": self.backend,
                "connected": False,
                "error": str(e)
            }
    
    async def close(self):
        """Clean up storage connections"""
        try:
            # No explicit cleanup needed for boto3/minio clients
            logger.info("Storage service connections closed")
        except Exception as e:
            logger.error(f"Error closing storage connections: {e}")