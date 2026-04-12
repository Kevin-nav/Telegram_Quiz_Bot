from __future__ import annotations

from pathlib import Path

from src.core.config import get_settings
from src.infra.r2.client import create_r2_client


ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_OBJECT_BYTES = 5 * 1024 * 1024


def build_latex_object_key(
    course_id: str, question_id: str, content_hash: str, extension: str = "png"
) -> str:
    return f"latex/{course_id}/{question_id}/{content_hash}.{extension}"


def build_database_backup_object_key(
    database_name: str,
    backup_filename: str,
    *,
    prefix: str = "db-backups",
) -> str:
    normalized_prefix = prefix.strip().strip("/")
    safe_database_name = database_name.strip().strip("/")
    safe_backup_name = Path(backup_filename).name
    return f"{normalized_prefix}/{safe_database_name}/{safe_backup_name}"


class R2Storage:
    def __init__(self, client=None, bucket_name: str | None = None):
        settings = get_settings()
        self.client = client or create_r2_client()
        self.bucket_name = bucket_name or settings.r2_bucket_name
        self.public_base_url = settings.r2_public_base_url

    def validate_upload(self, content_type: str, size_bytes: int) -> None:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError("Unsupported R2 content type.")
        if size_bytes > MAX_OBJECT_BYTES:
            raise ValueError("R2 object exceeds maximum allowed size.")

    def put_object(self, key: str, body: bytes, content_type: str) -> None:
        self.validate_upload(content_type, len(body))
        self.put_bytes_object(key, body, content_type)

    def put_bytes_object(
        self,
        key: str,
        body: bytes,
        content_type: str,
        *,
        metadata: dict[str, str] | None = None,
    ) -> None:
        request: dict[str, object] = {
            "Bucket": self.bucket_name,
            "Key": key,
            "Body": body,
            "ContentType": content_type,
        }
        if metadata:
            request["Metadata"] = metadata
        self.client.put_object(
            **request,
        )

    def put_database_backup(
        self,
        key: str,
        body: bytes,
        *,
        metadata: dict[str, str] | None = None,
        content_type: str = "application/octet-stream",
    ) -> None:
        self.put_bytes_object(
            key,
            body,
            content_type,
            metadata=metadata,
        )

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket_name, Key=key)

    def object_exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False

    def get_presigned_download_url(self, key: str, expires_in: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )

    def build_public_url(self, key: str) -> str:
        if not self.public_base_url:
            raise ValueError("R2 public base URL is not configured.")
        return f"{self.public_base_url.rstrip('/')}/{key.lstrip('/')}"
