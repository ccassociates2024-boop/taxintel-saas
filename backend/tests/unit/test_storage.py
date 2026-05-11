"""Unit tests for backend/app/core/storage.py (mocked via moto)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def reset_storage_client():
    """Clear the cached boto3 client between tests."""
    import app.core.storage as storage_mod
    storage_mod._client.cache_clear()
    yield
    storage_mod._client.cache_clear()


class TestStorageModule:
    def test_put_bytes_calls_s3(self):
        mock_client = MagicMock()
        with patch("app.core.storage._client", return_value=mock_client):
            with patch("app.core.storage._bucket", return_value="test-bucket"):
                from app.core import storage

                storage.put_bytes("some/key.pdf", b"data", "application/pdf")
                mock_client.put_object.assert_called_once_with(
                    Bucket="test-bucket",
                    Key="some/key.pdf",
                    Body=b"data",
                    ContentType="application/pdf",
                    ServerSideEncryption="AES256",
                )

    def test_get_signed_url_calls_s3(self):
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://signed-url"
        with patch("app.core.storage._client", return_value=mock_client):
            with patch("app.core.storage._bucket", return_value="test-bucket"):
                from app.core import storage

                url = storage.get_signed_url("some/key.pdf", expires_in=600)
                assert url == "https://signed-url"
                mock_client.generate_presigned_url.assert_called_once_with(
                    "get_object",
                    Params={"Bucket": "test-bucket", "Key": "some/key.pdf"},
                    ExpiresIn=600,
                )

    def test_delete_swallows_client_error(self):
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}}, "DeleteObject"
        )
        with patch("app.core.storage._client", return_value=mock_client):
            with patch("app.core.storage._bucket", return_value="test-bucket"):
                from app.core import storage

                storage.delete("missing/key.pdf")  # must not raise

    def test_object_exists_returns_true(self):
        mock_client = MagicMock()
        mock_client.head_object.return_value = {"ContentLength": 123}
        with patch("app.core.storage._client", return_value=mock_client):
            with patch("app.core.storage._bucket", return_value="test-bucket"):
                from app.core import storage

                assert storage.object_exists("existing/key.pdf") is True

    def test_object_exists_returns_false_on_missing(self):
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        mock_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
        )
        with patch("app.core.storage._client", return_value=mock_client):
            with patch("app.core.storage._bucket", return_value="test-bucket"):
                from app.core import storage

                assert storage.object_exists("missing/key.pdf") is False

    @pytest.mark.asyncio
    async def test_async_put_bytes(self):
        mock_client = MagicMock()
        with patch("app.core.storage._client", return_value=mock_client):
            with patch("app.core.storage._bucket", return_value="test-bucket"):
                from app.core import storage

                await storage.async_put_bytes("key", b"bytes")
                mock_client.put_object.assert_called_once()
