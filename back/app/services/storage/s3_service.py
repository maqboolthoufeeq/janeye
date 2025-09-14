# Standard library imports
from io import BytesIO

# Third-party imports
from minio import Minio

# Local application imports
from app.settings import settings


class S3Service:
    def __init__(self):
        self.client = Minio(
            settings.S3_URL.replace("http://", "").replace("https://", ""),
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
            secure=False,
        )
        self.bucket_name = settings.S3_PUBLIC_BUCKET_NAME
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Ensure the bucket exists, create if not"""
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    async def upload_file(self, file_data: bytes, file_key: str, content_type: str | None = None) -> str:
        """Upload file to S3 and return public URL"""
        self.client.put_object(
            self.bucket_name,
            file_key,
            BytesIO(file_data),
            len(file_data),
            content_type=content_type,
        )

        # Return public URL
        return f"{settings.S3_URL}/{self.bucket_name}/{file_key}"

    def delete_file(self, file_key: str):
        """Delete file from S3"""
        self.client.remove_object(self.bucket_name, file_key)

    def get_presigned_url(self, file_key: str, expiry: int = 3600) -> str:
        """Get presigned URL for file access"""
        return self.client.presigned_get_object(self.bucket_name, file_key, expiry=expiry)
