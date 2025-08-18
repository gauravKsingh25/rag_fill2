import os
import logging
from google.cloud import storage
from datetime import timedelta, datetime
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Expect environment variables:
# - GCS_BUCKET
# - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON)

GCS_BUCKET = os.getenv("GCS_BUCKET")
if not GCS_BUCKET or not GCS_BUCKET.strip():
    logger.error("GCS_BUCKET environment variable is not set or blank. GCS integration will not work.")
    raise RuntimeError("GCS_BUCKET environment variable is required and must not be blank.")

# Ensure GOOGLE_APPLICATION_CREDENTIALS is set via environment variable only
if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
    logger.warning("GOOGLE_APPLICATION_CREDENTIALS environment variable is not set. GCS client may not work.")

_client: Optional[storage.Client] = None
_bucket: Optional[storage.Bucket] = None


def _ensure_client():
    global _client, _bucket
    if _client is not None:
        return
    try:
        # storage.Client will use GOOGLE_APPLICATION_CREDENTIALS if set
        _client = storage.Client()
        if GCS_BUCKET:
            _bucket = _client.bucket(GCS_BUCKET)
        logger.info("Initialized GCS client")
    except Exception as e:
        logger.warning(f"GCS client not available: {e}")
        _client = None
        _bucket = None


def is_available() -> bool:
    _ensure_client()
    return _client is not None and _bucket is not None


def upload_json(data: dict, destination_name: str, content_type: str = "application/json") -> str:
    """Upload a JSON-serializable dict as a blob and return blob name."""
    _ensure_client()
    if not is_available():
        raise RuntimeError("GCS not configured")
    import json
    blob = _bucket.blob(destination_name)
    blob.upload_from_string(json.dumps(data, ensure_ascii=False), content_type=content_type)
    logger.info(f"Uploaded JSON to GCS: {destination_name}")
    return destination_name


def list_blobs(prefix: str = ""):
    _ensure_client()
    if not is_available():
        raise RuntimeError("GCS not configured")
    return list(_bucket.list_blobs(prefix=prefix))


def download_blob_as_text(blob_name: str) -> str:
    _ensure_client()
    if not is_available():
        raise RuntimeError("GCS not configured")
    blob = _bucket.blob(blob_name)
    return blob.download_as_text()


def upload_fileobj(file_obj, destination_name: str, content_type: Optional[str] = None) -> str:
    """Upload a file-like object to GCS and return the blob name."""
    _ensure_client()
    if not is_available():
        raise RuntimeError("GCS not configured")
    blob = _bucket.blob(destination_name)
    # Rewind if possible
    try:
        file_obj.seek(0)
    except Exception:
        pass
    blob.upload_from_file(file_obj, content_type=content_type)
    logger.info(f"Uploaded to GCS: {destination_name}")
    return destination_name


def generate_signed_url(blob_name: str, expires_seconds: int = 3600) -> str:
    _ensure_client()
    if not is_available():
        raise RuntimeError("GCS not configured")
    blob = _bucket.blob(blob_name)
    expiration = datetime.utcnow() + timedelta(seconds=expires_seconds)
    url = blob.generate_signed_url(expiration=expiration)
    return url
