import os
import logging
from google.cloud import storage
from datetime import timedelta, datetime
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Expect environment variables:
# - GCS_BUCKET (optional)
# - GOOGLE_APPLICATION_CREDENTIALS (path to service account JSON; attempt to auto-resolve if relative)

GCS_BUCKET = os.getenv("GCS_BUCKET")  # do NOT raise at import-time; allow app to start without GCS
if not GCS_BUCKET or not GCS_BUCKET.strip():
    logger.warning("GCS_BUCKET environment variable is not set or blank. GCS integration disabled until configured.")
    GCS_BUCKET = None  # normalize to None

# Normalize GOOGLE_APPLICATION_CREDENTIALS if provided as a relative path (resolve against backend root)
_gac = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if _gac:
    gac_path = Path(_gac)
    if not gac_path.is_absolute():
        # backend root is three parents up from this file: backend/app/services -> backend
        backend_root = Path(__file__).resolve().parents[3]
        candidate = (backend_root / gac_path).resolve()
        if candidate.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(candidate)
            logger.info(f"Resolved relative GOOGLE_APPLICATION_CREDENTIALS to absolute path: {candidate}")
        else:
            logger.debug(f"GOOGLE_APPLICATION_CREDENTIALS provided but could not resolve relative path: {gac_path} (checked {candidate})")
else:
    logger.debug("GOOGLE_APPLICATION_CREDENTIALS is not set in environment; GCS client may not authenticate.")

_client: Optional[storage.Client] = None
_bucket: Optional[storage.Bucket] = None


def _ensure_client():
    global _client, _bucket
    if _client is not None:
        return
    if not GCS_BUCKET:
        # No bucket configured; leave client None
        logger.debug("GCS_BUCKET not configured; skipping GCS client initialization.")
        _client = None
        _bucket = None
        return
    try:
        # storage.Client will use GOOGLE_APPLICATION_CREDENTIALS if set
        _client = storage.Client()
        _bucket = _client.bucket(GCS_BUCKET)
        logger.info("Initialized GCS client and bucket reference")
    except Exception as e:
        # Do not crash the app — keep client None and log helpful guidance
        logger.warning(
            "GCS client initialization failed. GCS functionality will be disabled.\n"
            "Common causes: GOOGLE_APPLICATION_CREDENTIALS missing/invalid, or service account key expired/rotated.\n"
            f"Error: {e}"
        )
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


def upload_fileobj_to_bucket(file_obj, destination_name: str, bucket_name: str, content_type: Optional[str] = None) -> str:
    """Upload a file-like object to a specific GCS bucket and return the blob name."""
    _ensure_client()
    if not _client:
        raise RuntimeError("GCS client not available")
    
    # Use the specified bucket instead of the default bucket
    target_bucket = _client.bucket(bucket_name)
    blob = target_bucket.blob(destination_name)
    
    # Rewind if possible
    try:
        file_obj.seek(0)
    except Exception:
        pass
    try:
        blob.upload_from_file(file_obj, content_type=content_type)
    except Exception as e:
        logger.error(f"GCS upload failed for {destination_name} to bucket {bucket_name}: {e}")
        raise
    logger.info(f"Uploaded to GCS bucket {bucket_name}: {destination_name}")
    return destination_name


def generate_signed_url_from_bucket(blob_name: str, bucket_name: str, expires_seconds: int = 3600) -> str:
    """Generate signed URL for a blob in a specific bucket."""
    _ensure_client()
    if not _client:
        raise RuntimeError("GCS client not available")
    
    target_bucket = _client.bucket(bucket_name)
    blob = target_bucket.blob(blob_name)
    expiration = datetime.utcnow() + timedelta(seconds=expires_seconds)
    url = blob.generate_signed_url(expiration=expiration)
    return url


def upload_json_to_bucket(data: dict, destination_name: str, bucket_name: str, content_type: str = "application/json") -> str:
    """Upload a JSON-serializable dict to a specific bucket and return blob name."""
    _ensure_client()
    if not _client:
        raise RuntimeError("GCS client not available")
    
    import json
    target_bucket = _client.bucket(bucket_name)
    blob = target_bucket.blob(destination_name)
    blob.upload_from_string(json.dumps(data, ensure_ascii=False), content_type=content_type)
    logger.info(f"Uploaded JSON to GCS bucket {bucket_name}: {destination_name}")
    return destination_name


def download_blob_as_text_from_bucket(blob_name: str, bucket_name: str) -> str:
    """Download blob as text from a specific bucket."""
    _ensure_client()
    if not _client:
        raise RuntimeError("GCS client not available")
    
    target_bucket = _client.bucket(bucket_name)
    blob = target_bucket.blob(blob_name)
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
    try:
        blob.upload_from_file(file_obj, content_type=content_type)
    except Exception as e:
        # Attach guidance for common auth problems
        logger.error(f"GCS upload failed for {destination_name}: {e}")
        raise
    logger.info(f"Uploaded to GCS: {destination_name}")
    return destination_name


def generate_signed_url(blob_name: str, expires_seconds: int = 3600) -> str:
    _ensure_client()
    if not is_available():
        raise RuntimeError("GCS not configured")
    blob = _bucket.blob(blob_name)
    expiration = datetime.utcnow() + timedelta(seconds=expires_seconds)
    # generate_signed_url may raise helpful auth errors; let caller handle
    url = blob.generate_signed_url(expiration=expiration)
    return url


def delete_blob_from_bucket(blob_name: str, bucket_name: str) -> bool:
    """Delete a blob from a specific GCS bucket."""
    _ensure_client()
    if not _client:
        raise RuntimeError("GCS client not available")
    
    try:
        target_bucket = _client.bucket(bucket_name)
        blob = target_bucket.blob(blob_name)
        blob.delete()
        logger.info(f"Deleted blob from GCS bucket {bucket_name}: {blob_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete blob {blob_name} from bucket {bucket_name}: {e}")
        raise
