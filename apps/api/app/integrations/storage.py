import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings
from app.core.exceptions import BusinessError
from app.core.logging import get_logger

logger = get_logger("storage")


class StorageAdapter:
    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
        )

    def ensure_bucket(self, bucket: str) -> None:
        try:
            self._client.head_bucket(Bucket=bucket)
            logger.info("bucket_exists", bucket=bucket)
        except ClientError:
            self._client.create_bucket(Bucket=bucket)
            logger.info("bucket_created", bucket=bucket)

    def upload_file(
        self, bucket: str, key: str, file_data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        try:
            self._client.put_object(
                Bucket=bucket,
                Key=key,
                Body=file_data,
                ContentType=content_type,
            )
        except ClientError as exc:
            logger.error("file_upload_failed", bucket=bucket, key=key, error=str(exc))
            raise BusinessError(
                f"Impossible de televerser le fichier : {exc}",
                code="STORAGE_UPLOAD_ERROR",
            ) from exc
        except Exception as exc:
            logger.error("file_upload_unexpected_error", bucket=bucket, key=key, error=str(exc))
            raise BusinessError(
                "Erreur inattendue lors du televersement du fichier",
                code="STORAGE_UPLOAD_ERROR",
            ) from exc
        logger.info("file_uploaded", bucket=bucket, key=key)
        return key

    def get_download_url(
        self,
        bucket: str,
        key: str,
        expires: int = 3600,
        extra_params: dict[str, str] | None = None,
    ) -> str:
        params: dict[str, str] = {"Bucket": bucket, "Key": key}
        if extra_params:
            params.update(extra_params)
        url = self._client.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=expires,
        )
        return url

    def download_file(self, bucket: str, key: str) -> bytes:
        """Download a file from S3/MinIO and return its raw bytes."""
        try:
            response = self._client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except ClientError as exc:
            logger.error("file_download_failed", bucket=bucket, key=key, error=str(exc))
            raise BusinessError(
                f"Impossible de telecharger le fichier : {exc}",
                code="STORAGE_DOWNLOAD_ERROR",
            ) from exc

    def delete_file(self, bucket: str, key: str) -> None:
        try:
            self._client.delete_object(Bucket=bucket, Key=key)
        except ClientError as exc:
            logger.error("file_delete_failed", bucket=bucket, key=key, error=str(exc))
            raise BusinessError(
                f"Impossible de supprimer le fichier : {exc}",
                code="STORAGE_DELETE_ERROR",
            ) from exc
        except Exception as exc:
            logger.error("file_delete_unexpected_error", bucket=bucket, key=key, error=str(exc))
            raise BusinessError(
                "Erreur inattendue lors de la suppression du fichier",
                code="STORAGE_DELETE_ERROR",
            ) from exc
        logger.info("file_deleted", bucket=bucket, key=key)


storage = StorageAdapter()
