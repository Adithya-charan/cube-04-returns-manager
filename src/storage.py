import os
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Optional, BinaryIO
import logging

logger = logging.getLogger("returns_manager.storage")

class ObjectStorageProvider:
    def __init__(self):
        self.endpoint_url = os.getenv("OBJECT_STORAGE_ENDPOINT")
        self.bucket = os.getenv("OBJECT_STORAGE_BUCKET")
        self.access_key = os.getenv("OBJECT_STORAGE_ACCESS_KEY")
        self.secret_key = os.getenv("OBJECT_STORAGE_SECRET_KEY")
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        ) if self.endpoint_url else None
        
        # Local fallback if absolutely needed / for testing if no env
        self.fallback_dir = "fixtures/returns"
        os.makedirs(self.fallback_dir, exist_ok=True)

    def is_configured(self) -> bool:
        return self.s3_client is not None and bool(self.bucket)

    def upload_file(self, file_obj: BinaryIO, filename: str, content_type: str) -> str:
        """
        Uploads an image to S3-compatible storage. 
        Returns the object key or storage reference.
        """
        object_key = f"returns/{uuid.uuid4().hex}_{filename}"
        
        if self.is_configured():
            try:
                self.s3_client.upload_fileobj(
                    file_obj,
                    self.bucket,
                    object_key,
                    ExtraArgs={'ContentType': content_type}
                )
                logger.info(f"Uploaded {filename} to S3 bucket {self.bucket} at {object_key}")
                return object_key
            except ClientError as e:
                logger.error(f"S3 upload failed: {e}")
                raise e
        else:
            # Fallback local storage
            logger.warning("Object storage not fully configured, falling back to local storage")
            safe_filename = object_key.replace("/", "_")
            storage_path = os.path.join(self.fallback_dir, safe_filename).replace("\\", "/")
            with open(storage_path, "wb") as f:
                f.write(file_obj.read())
            return storage_path

    def get_file_content(self, storage_ref: str) -> Optional[bytes]:
        """
        Fetches the bytes of the file for vision inference or frontend viewing.
        """
        if self.is_configured() and not storage_ref.startswith("fixtures"):
            try:
                response = self.s3_client.get_object(Bucket=self.bucket, Key=storage_ref)
                return response['Body'].read()
            except ClientError as e:
                logger.error(f"S3 get failed: {e}")
                return None
        else:
            try:
                with open(storage_ref, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Local file get failed: {e}")
                return None
