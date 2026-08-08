"""Optional MinIO/S3 object storage. Failures never block report generation."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_object_store_enabled() -> bool:
    return bool(os.getenv("MINIO_ENDPOINT") or os.getenv("S3_ENDPOINT"))


class ObjectStore:
    """Thin MinIO wrapper with local-disk fallback."""

    def __init__(self) -> None:
        self.enabled = False
        self._client = None
        self.bucket = os.getenv("MINIO_BUCKET", "gptr-artifacts")
        endpoint = os.getenv("MINIO_ENDPOINT") or os.getenv("S3_ENDPOINT")
        if not endpoint:
            return
        try:
            from minio import Minio

            access = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            secret = os.getenv("MINIO_SECRET_KEY", "minioadmin")
            secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
            self._client = Minio(
                endpoint.replace("http://", "").replace("https://", ""),
                access_key=access,
                secret_key=secret,
                secure=secure,
            )
            if not self._client.bucket_exists(self.bucket):
                self._client.make_bucket(self.bucket)
            self.enabled = True
            logger.info("Object store enabled (bucket=%s)", self.bucket)
        except Exception as exc:
            logger.warning("Object store unavailable, using local disk: %s", exc)
            self.enabled = False
            self._client = None

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream", tenant_id: str | None = None) -> Optional[str]:
        """Upload bytes. Returns object key on success, None on failure (non-fatal)."""
        if not self.enabled or self._client is None:
            return None
        try:
            from io import BytesIO
            from security import object_key, tenant_id_for

            final_key = key
            if tenant_id or not key.startswith("tenants/"):
                final_key = object_key(tenant_id or tenant_id_for(None), key)

            self._client.put_object(
                self.bucket,
                final_key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return final_key
        except Exception as exc:
            logger.warning("Object upload failed (non-fatal): %s", exc)
            return None

    def put_text(self, key: str, text: str, content_type: str = "text/plain; charset=utf-8") -> Optional[str]:
        return self.put_bytes(key, text.encode("utf-8"), content_type=content_type)

    def put_file(self, key: str, path: Path) -> Optional[str]:
        if not self.enabled or self._client is None:
            return None
        try:
            self._client.fput_object(self.bucket, key, str(path))
            return key
        except Exception as exc:
            logger.warning("Object file upload failed (non-fatal): %s", exc)
            return None


_store: Optional[ObjectStore] = None


def get_object_store() -> ObjectStore:
    global _store
    if _store is None:
        _store = ObjectStore()
    return _store
