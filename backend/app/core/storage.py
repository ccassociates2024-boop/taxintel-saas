"""S3-compatible object storage abstraction.

Backed by boto3 against AWS S3 (ap-south-1) or Cloudflare R2.
Local dev uses MinIO via S3_ENDPOINT_URL.

All upload code paths must use this module — never write to local disk.
Storage layout: uploads/{user_id}/{client_id}/{file_hash}{ext}
              (extended to tenants/{tenant_id}/... in Phase 1A)
"""

from __future__ import annotations

import functools
import asyncio
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def _make_client():
    from app.core.config import settings

    kwargs: dict = {
        "region_name": settings.s3_region,
        "aws_access_key_id": settings.s3_access_key,
        "aws_secret_access_key": settings.s3_secret_key,
        "config": Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}),
    }
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    return boto3.client("s3", **kwargs)


@functools.lru_cache(maxsize=1)
def _client():
    return _make_client()


def _bucket() -> str:
    from app.core.config import settings
    return settings.s3_bucket


# ---------------------------------------------------------------------------
# Synchronous interface (call via asyncio.to_thread from async endpoints)
# ---------------------------------------------------------------------------

def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload raw bytes to S3 under *key*."""
    _client().put_object(
        Bucket=_bucket(),
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )


def get_signed_url(key: str, expires_in: int = 3600) -> str:
    """Return a pre-signed GET URL valid for *expires_in* seconds."""
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _bucket(), "Key": key},
        ExpiresIn=expires_in,
    )


def delete(key: str) -> None:
    """Permanently remove an object from the bucket."""
    try:
        _client().delete_object(Bucket=_bucket(), Key=key)
    except ClientError:
        pass


def object_exists(key: str) -> bool:
    """Return True if the key exists in the bucket."""
    try:
        _client().head_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError:
        return False


# ---------------------------------------------------------------------------
# Async wrappers — thin asyncio.to_thread shims for use inside async routes
# ---------------------------------------------------------------------------

async def async_put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    await asyncio.to_thread(put_bytes, key, data, content_type)


async def async_get_signed_url(key: str, expires_in: int = 3600) -> str:
    return await asyncio.to_thread(get_signed_url, key, expires_in)


async def async_delete(key: str) -> None:
    await asyncio.to_thread(delete, key)
