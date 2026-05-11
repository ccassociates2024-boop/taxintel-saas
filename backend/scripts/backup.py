#!/usr/bin/env python3
"""Phase 1G — Automated pg_dump backup to S3.

Usage (cron or Railway cron job):
    python backend/scripts/backup.py

Env vars required: DATABASE_URL, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY,
                   S3_REGION, PII_ENCRYPTION_KEY
"""
from __future__ import annotations

import gzip
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import boto3
import structlog

log = structlog.get_logger(__name__)


def _s3_client():
    return boto3.client(
        "s3",
        region_name=os.environ.get("S3_REGION", "ap-south-1"),
        aws_access_key_id=os.environ["S3_ACCESS_KEY"],
        aws_secret_access_key=os.environ["S3_SECRET_KEY"],
        endpoint_url=os.environ.get("S3_ENDPOINT_URL"),
    )


def run_backup() -> str:
    db_url = os.environ["DATABASE_URL"]
    parsed = urlparse(db_url)

    env = {
        **os.environ,
        "PGPASSWORD": parsed.password or "",
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    s3_key = f"backups/{stamp}.sql.gz"

    with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            "pg_dump",
            "--no-password",
            "--format=plain",
            "--no-owner",
            "--no-acl",
            f"--host={parsed.hostname}",
            f"--port={parsed.port or 5432}",
            f"--username={parsed.username}",
            f"--dbname={parsed.path.lstrip('/')}",
            f"--file={tmp_path}",
        ]
        log.info("backup.pg_dump_start", host=parsed.hostname, db=parsed.path.lstrip("/"))
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            log.error("backup.pg_dump_failed", stderr=result.stderr)
            sys.exit(1)

        # Gzip the dump
        gz_path = tmp_path + ".gz"
        with open(tmp_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            f_out.write(f_in.read())

        size_mb = Path(gz_path).stat().st_size / (1024 * 1024)

        # Upload to S3
        bucket = os.environ["S3_BUCKET"]
        _s3_client().upload_file(
            gz_path,
            bucket,
            s3_key,
            ExtraArgs={"ServerSideEncryption": "AES256"},
        )
        log.info("backup.uploaded", s3_key=s3_key, size_mb=f"{size_mb:.2f}")
        return s3_key

    finally:
        for p in (tmp_path, tmp_path + ".gz"):
            try:
                os.unlink(p)
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    # Configure minimal structlog for script use
    import structlog
    structlog.configure(
        processors=[
            structlog.dev.ConsoleRenderer(),
        ]
    )
    key = run_backup()
    print(f"✓ Backup complete: {key}")
