"""S3-compatible object storage abstraction.

Production: AWS S3 ap-south-1 or Cloudflare R2 (via S3_ENDPOINT_URL).
Local dev:  Falls back to local filesystem under LOCAL_STORAGE_DIR when
            APP_ENV=local and S3_ACCESS_KEY is the placeholder 'minioadmin'.

All upload code paths must use this module — never write to local disk directly.
"""

from __future__ import annotations

import asyncio
import functools
import io
import os
from pathlib import Path
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


# ---------------------------------------------------------------------------
# Local-filesystem backend (used when MinIO / S3 not available)
# ---------------------------------------------------------------------------

def _local_root() -> Path:
    raw = os.environ.get("LOCAL_STORAGE_DIR", "local_uploads")
    # Always resolve to an absolute path so it works regardless of CWD
    # (important when called from asyncio thread-pool workers).
    root = Path(raw) if os.path.isabs(raw) else Path(__file__).resolve().parent.parent.parent / raw
    root.mkdir(parents=True, exist_ok=True)
    return root


def _is_local() -> bool:
    from app.core.config import settings
    return settings.app_env == "local" and settings.s3_access_key in ("minioadmin", "test", "")


class _LocalBackend:
    """Flat-file store that mirrors the S3 key hierarchy on disk."""

    def put_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        # Split on "/" so pathlib handles OS-specific sep correctly
        path = _local_root().joinpath(*key.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get_signed_url(self, key: str, expires_in: int = 3600) -> str:
        # For local dev return a /files/ URL served by a simple static route
        return f"http://localhost:8000/api/v1/files/{key}"

    def delete(self, key: str) -> None:
        path = _local_root().joinpath(*key.split("/"))
        path.unlink(missing_ok=True)

    def object_exists(self, key: str) -> bool:
        return _local_root().joinpath(*key.split("/")).exists()


_local_backend = _LocalBackend()


# ---------------------------------------------------------------------------
# S3 backend
# ---------------------------------------------------------------------------

def _make_s3_client():
    from app.core.config import settings
    kwargs: dict[str, Any] = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


@functools.lru_cache(maxsize=1)
def _s3():
    return _make_s3_client()


def _bucket() -> str:
    from app.core.config import settings
    return settings.s3_bucket


# ---------------------------------------------------------------------------
# Public synchronous interface
# ---------------------------------------------------------------------------

def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    if _is_local():
        _local_backend.put_bytes(key, data, content_type)
        return
    _s3().put_object(
        Bucket=_bucket(), Key=key, Body=data,
        ContentType=content_type, ServerSideEncryption="AES256",
    )


def get_signed_url(key: str, expires_in: int = 3600) -> str:
    if _is_local():
        return _local_backend.get_signed_url(key, expires_in)
    return _s3().generate_presigned_url(
        "get_object", Params={"Bucket": _bucket(), "Key": key}, ExpiresIn=expires_in,
    )


def delete(key: str) -> None:
    if _is_local():
        _local_backend.delete(key)
        return
    try:
        _s3().delete_object(Bucket=_bucket(), Key=key)
    except ClientError:
        pass


def object_exists(key: str) -> bool:
    if _is_local():
        return _local_backend.object_exists(key)
    try:
        _s3().head_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError:
        return False


# ---------------------------------------------------------------------------
# Async wrappers
# ---------------------------------------------------------------------------

async def async_put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    await asyncio.to_thread(put_bytes, key, data, content_type)


async def async_get_signed_url(key: str, expires_in: int = 3600) -> str:
    return await asyncio.to_thread(get_signed_url, key, expires_in)


async def async_delete(key: str) -> None:
    await asyncio.to_thread(delete, key)
