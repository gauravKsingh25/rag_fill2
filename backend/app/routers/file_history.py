from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any
import logging
import json
from pathlib import Path
from datetime import datetime

from app.services import gcs_service
from app.database import mongodb

router = APIRouter()
logger = logging.getLogger(__name__)

# When MongoDB is not available, prefer using GCS index blob if possible
GCS_INDEX_BLOB = "file_history/index.json"

# Local fallback path (backend/local_storage/file_history.json)
_backend_root = Path(__file__).resolve().parents[2]
_LOCAL_INDEX_DIR = _backend_root / "local_storage"
_LOCAL_INDEX_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_INDEX_PATH = _LOCAL_INDEX_DIR / "file_history.json"


def _load_index_local() -> List[Dict[str, Any]]:
    try:
        if not LOCAL_INDEX_PATH.exists():
            return []
        with LOCAL_INDEX_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read local file history index: {e}")
        return []


def _save_index_local(items: List[Dict[str, Any]]) -> bool:
    try:
        with LOCAL_INDEX_PATH.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved file history to local index: {LOCAL_INDEX_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to save local file history index: {e}")
        return False


async def _load_index_from_gcs() -> List[Dict[str, Any]]:
    # If GCS available, prefer it; otherwise use local fallback
    if not gcs_service.is_available():
        logger.debug("GCS not available when trying to load index; using local fallback")
        return _load_index_local()
    try:
        text = gcs_service.download_blob_as_text(GCS_INDEX_BLOB)
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Failed to load index from GCS: {e}; falling back to local index")
        return _load_index_local()


async def _save_index_to_gcs(items: List[Dict[str, Any]]):
    # If GCS available try to save; on failure fall back to local
    if not gcs_service.is_available():
        logger.debug("GCS not available when trying to save index; using local fallback")
        return _save_index_local(items)
    try:
        gcs_service.upload_json(items, GCS_INDEX_BLOB)
        return True
    except Exception as e:
        logger.error(f"Failed to save index to GCS: {e}; attempting local save")
        return _save_index_local(items)


@router.get("/", response_model=List[Dict[str, Any]])
async def get_history():
    # Try GCS index if configured; otherwise return local index
    try:
        items = await _load_index_from_gcs()
        return items
    except Exception as e:
        logger.error(f"Failed to get file history: {e}")
        raise HTTPException(status_code=500, detail="Failed to get file history")


@router.post("/", status_code=201)
async def add_history_item(
    file: UploadFile = File(None),
    filename: str = Form(None),
    type: str = Form(...),
    timestamp: str = Form(None),
):
    """Upload file to GCS (if configured) and persist metadata to index in GCS when possible."""
    try:
        record = {}
        if file is not None:
            # Build destination name with timestamp
            dest_name = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
            logger.info(f"Preparing history record for file: {file.filename} as {dest_name}")

            # attempt to determine file size (UploadFile.file may have .seek)
            try:
                pos = file.file.tell()
                file.file.seek(0, 2)
                size = file.file.tell()
                file.file.seek(pos)
            except Exception:
                size = None

            logger.info(f"File size determined: {size} bytes")

            if gcs_service.is_available():
                # Upload file to GCS and generate signed URL
                try:
                    upload_start = datetime.utcnow()
                    gcs_service.upload_fileobj(file.file, dest_name, content_type=file.content_type)
                    upload_end = datetime.utcnow()
                    logger.info(f"File upload completed for {dest_name} in {(upload_end-upload_start).total_seconds()} seconds")
                    try:
                        url = gcs_service.generate_signed_url(dest_name, expires_seconds=3600*24*7)
                    except Exception as e:
                        logger.error(f"Failed to generate signed URL after upload: {e}")
                        url = ""
                except Exception as upload_err:
                    msg = str(upload_err)
                    logger.error(f"Error during file upload to GCS: {msg}")
                    # Fall back to local metadata-only record instead of hard error
                    url = ""
                    logger.info("Falling back to local metadata storage for this upload.")
            else:
                # GCS not available: do not upload file; store metadata locally
                logger.info("GCS not available: saving metadata only to local index")
                url = ""

            record["filename"] = file.filename
            record["url"] = url
            record["type"] = type
            record["timestamp"] = timestamp or datetime.utcnow().isoformat() + "Z"
            record["content_type"] = file.content_type
            record["size_bytes"] = size if size is not None else None
        else:
            # metadata-only record (no file uploaded)
            if not filename:
                raise HTTPException(status_code=400, detail="filename is required when not uploading a file")
            record = {"filename": filename, "type": type, "url": "", "timestamp": timestamp or datetime.utcnow().isoformat() + "Z"}

        # Persist index (GCS preferred, local fallback)
        index_start = datetime.utcnow()
        items = await _load_index_from_gcs()
        items.insert(0, record)
        ok = await _save_index_to_gcs(items)
        index_end = datetime.utcnow()
        if ok:
            logger.info(f"Index updated and saved in {(index_end-index_start).total_seconds()} seconds. Total items: {len(items)}")
        else:
            logger.warning("Failed to persist index to storage after update; returning record anyway.")

        return record

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to add history item: {e}")
        raise HTTPException(status_code=500, detail="Failed to add history item")
