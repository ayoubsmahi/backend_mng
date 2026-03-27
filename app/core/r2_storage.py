import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from fastapi import HTTPException
from fastapi.responses import StreamingResponse


@dataclass(frozen=True)
class R2Settings:
    bucket: str
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    region: str = "auto"
    key_prefix: str = ""


def _clean_prefix(prefix: str) -> str:
    prefix = (prefix or "").strip().strip("/")
    return prefix


@lru_cache(maxsize=1)
def get_r2_settings() -> Optional[R2Settings]:
    bucket = os.getenv("R2_BUCKET", "").strip()
    endpoint_url = os.getenv("R2_ENDPOINT_URL", "").strip()
    access_key_id = os.getenv("R2_ACCESS_KEY_ID", "").strip()
    secret_access_key = os.getenv("R2_SECRET_ACCESS_KEY", "").strip()
    region = os.getenv("R2_REGION", "auto").strip() or "auto"
    key_prefix = _clean_prefix(os.getenv("R2_KEY_PREFIX", ""))

    if not bucket or not endpoint_url or not access_key_id or not secret_access_key:
        return None

    return R2Settings(
        bucket=bucket,
        endpoint_url=endpoint_url,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        region=region,
        key_prefix=key_prefix,
    )


def r2_enabled() -> bool:
    return get_r2_settings() is not None


@lru_cache(maxsize=1)
def _s3_client():
    settings = get_r2_settings()
    if settings is None:
        raise RuntimeError("R2 is not configured. Missing R2_* environment variables.")

    return boto3.client(
        "s3",
        endpoint_url=settings.endpoint_url,
        aws_access_key_id=settings.access_key_id,
        aws_secret_access_key=settings.secret_access_key,
        region_name=settings.region,
        config=Config(signature_version="s3v4"),
    )


def build_r2_key(entity_type: str, entity_id: int, unique_filename: str) -> str:
    settings = get_r2_settings()
    if settings is None:
        raise RuntimeError("R2 is not configured.")

    base = f"{entity_type}/{entity_id}/{unique_filename}".lstrip("/")
    if settings.key_prefix:
        return f"{settings.key_prefix}/{base}"
    return base


def normalize_db_path_to_r2_key(db_file_path: str) -> str:
    # Backward-compat: some rows may contain a local path like "uploads/expense/12/uuid_name.pdf".
    path = (db_file_path or "").strip()
    if path.startswith("r2:"):
        path = path[len("r2:") :]
    path = path.lstrip("/")
    if path.startswith("uploads/"):
        path = path[len("uploads/") :]
    return path


def upload_bytes_to_r2(*, key: str, content: bytes, content_type: Optional[str]) -> None:
    settings = get_r2_settings()
    if settings is None:
        raise RuntimeError("R2 is not configured.")

    try:
        _s3_client().put_object(
            Bucket=settings.bucket,
            Key=key,
            Body=content,
            ContentType=(content_type or "application/octet-stream"),
        )
    except ClientError:
        raise HTTPException(status_code=500, detail="Failed to upload file to object storage.")


def delete_r2_object(*, key: str) -> None:
    settings = get_r2_settings()
    if settings is None:
        raise RuntimeError("R2 is not configured.")

    try:
        _s3_client().delete_object(Bucket=settings.bucket, Key=key)
    except ClientError:
        # Deleting a non-existent object should not block DB cleanup.
        return


def _is_missing_object(err: ClientError) -> bool:
    code = (err.response.get("Error", {}) or {}).get("Code")
    return code in {"NoSuchKey", "NotFound", "404"}


def stream_r2_object(*, key: str, download_name: str, content_type: Optional[str]):
    settings = get_r2_settings()
    if settings is None:
        raise RuntimeError("R2 is not configured.")

    try:
        obj = _s3_client().get_object(Bucket=settings.bucket, Key=key)
    except ClientError as err:
        if _is_missing_object(err):
            raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=500, detail="Failed to download file from object storage.")

    body = obj.get("Body")
    if body is None:
        raise HTTPException(status_code=404, detail="File not found")

    def iterator() -> Iterable[bytes]:
        while True:
            chunk = body.read(1024 * 1024)
            if not chunk:
                break
            yield chunk

    headers = {
        "Content-Disposition": f'attachment; filename="{download_name}"',
    }
    media_type = content_type or obj.get("ContentType") or "application/octet-stream"
    return StreamingResponse(iterator(), media_type=media_type, headers=headers)
