import io
import os

from dotenv import load_dotenv
from fastapi import HTTPException
from minio import Minio
from minio.error import S3Error

from config.logger import logger

load_dotenv()


class MinioHandler:
    def __init__(self):
        self.client = Minio(
            endpoint="localhost:9000",
            access_key="minio",
            secret_key="minio123",
            secure=False,  # Set to True if using HTTPS
        )

    async def upload_file(self, bucket_name: str, file_path: str, content: bytes):
        """Upload a file to the specified bucket"""
        try:
            # Check if bucket exists, if not create it
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket {bucket_name}")

            # Upload the content
            result = self.client.put_object(
                bucket_name,
                file_path,
                data=io.BytesIO(content),
                length=len(content),
                content_type="text/plain",
            )
            logger.info(
                f"Created {result.object_name} object; etag: {result.etag}, "
                f"version-id: {result.version_id}"
            )
            return True
        except S3Error as e:
            logger.error(f"Error uploading file: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file: {str(e)}"
            )
