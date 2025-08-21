"""
Favorites Management

This module handles the favorites functionality for user-curated files.

IMPORTANT: This should ONLY be used for:
- Files manually uploaded by users via "Add to Favorites" button
- User-selected files to be marked as favorites
- Explicit user actions to favorite content

Do NOT use this for:
- System-processed files (use file_history instead)
- Analyzed templates or CSV files
- Filled/processed content
- Any automated system operations

For automated file tracking, use file_history.add_file_to_history() instead.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any
import logging
import json
from pathlib import Path
from datetime import datetime

from app.services import gcs_service
from app.database import mongodb  # optional usage if you want DB persistence

router = APIRouter(prefix="/api/favorites", tags=["Favorites"])
logger = logging.getLogger(__name__)

# Hardcoded GCS bucket name for favorites (separate from file history)
FAVORITES_GCS_BUCKET = "rag-fav"
GCS_INDEX_BLOB = "favorites/index.json"

_backend_root = Path(__file__).resolve().parents[2]
_LOCAL_INDEX_DIR = _backend_root / "local_storage"
_LOCAL_INDEX_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_INDEX_PATH = _LOCAL_INDEX_DIR / "favorites.json"


def _load_index_local() -> List[Dict[str, Any]]:
    try:
        if not LOCAL_INDEX_PATH.exists():
            return []
        with LOCAL_INDEX_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read local favorites index: {e}")
        return []


def _save_index_local(items: List[Dict[str, Any]]) -> bool:
    try:
        with LOCAL_INDEX_PATH.open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved favorites to local index: {LOCAL_INDEX_PATH}")
        return True
    except Exception as e:
        logger.error(f"Failed to save local favorites index: {e}")
        return False


async def _load_index_from_gcs() -> List[Dict[str, Any]]:
    if not gcs_service.is_available():
        return _load_index_local()
    try:
        # Use the favorites-specific bucket
        text = gcs_service.download_blob_as_text_from_bucket(GCS_INDEX_BLOB, FAVORITES_GCS_BUCKET)
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Failed to load favorites index from GCS bucket {FAVORITES_GCS_BUCKET}: {e}")
        # Initialize empty favorites index in the bucket instead of falling back to local
        try:
            empty_index = []
            gcs_service.upload_json_to_bucket(empty_index, GCS_INDEX_BLOB, FAVORITES_GCS_BUCKET)
            logger.info(f"✅ Initialized empty favorites index in bucket '{FAVORITES_GCS_BUCKET}'")
            return empty_index
        except Exception as init_error:
            logger.error(f"Failed to initialize favorites index in bucket: {init_error}; falling back to local")
            return _load_index_local()


async def _save_index_to_gcs(items: List[Dict[str, Any]]):
    if not gcs_service.is_available():
        return _save_index_local(items)
    try:
        # Use the favorites-specific bucket
        gcs_service.upload_json_to_bucket(items, GCS_INDEX_BLOB, FAVORITES_GCS_BUCKET)
        return True
    except Exception as e:
        logger.error(f"Failed to save favorites index to GCS bucket {FAVORITES_GCS_BUCKET}: {e}; falling back to local")
        return _save_index_local(items)


@router.get("/", response_model=List[Dict[str, Any]])
async def get_favorites():
    try:
        items = await _load_index_from_gcs()
        return items
    except Exception as e:
        logger.exception("Failed to load favorites")
        raise HTTPException(status_code=500, detail="Failed to load favorites")


@router.post("/", status_code=201)
async def add_favorite(
    file: UploadFile = File(None),
    filename: str = Form(None),
    type: str = Form(...),
    timestamp: str = Form(None),
):
    try:
        record: Dict[str, Any] = {}
        if file is not None:
            dest_name = f"fav_{int(datetime.utcnow().timestamp())}_{file.filename}"
            logger.info(f"📁 Uploading favorite file to bucket '{FAVORITES_GCS_BUCKET}': {file.filename}")
            
            size = None
            try:
                pos = file.file.tell()
                file.file.seek(0, 2)
                size = file.file.tell()
                file.file.seek(pos)
            except Exception:
                size = None

            if gcs_service.is_available():
                try:
                    # Upload to the favorites-specific bucket
                    gcs_service.upload_fileobj_to_bucket(file.file, dest_name, FAVORITES_GCS_BUCKET, content_type=file.content_type)
                    try:
                        # Generate signed URL from the favorites bucket
                        url = gcs_service.generate_signed_url_from_bucket(dest_name, FAVORITES_GCS_BUCKET, expires_seconds=3600*24*7)
                        logger.info(f"✅ Successfully uploaded favorite to bucket '{FAVORITES_GCS_BUCKET}': {dest_name}")
                    except Exception:
                        url = ""
                except Exception as upload_err:
                    logger.error(f"Failed to upload favorite to GCS bucket {FAVORITES_GCS_BUCKET}: {upload_err}")
                    url = ""
            else:
                url = ""
                logger.warning(f"GCS not available - favorite will be stored locally only")

            record = {
                "filename": file.filename,
                "url": url,
                "type": type,
                "timestamp": timestamp or datetime.utcnow().isoformat() + "Z",
                "content_type": file.content_type,
                "size_bytes": size,
            }
        else:
            if not filename:
                raise HTTPException(status_code=400, detail="filename is required when not uploading a file")
            record = {"filename": filename, "type": type, "url": "", "timestamp": timestamp or datetime.utcnow().isoformat() + "Z"}

        items = await _load_index_from_gcs()
        items.insert(0, record)
        ok = await _save_index_to_gcs(items)
        if not ok:
            logger.warning("Failed to persist favorites index after update")
        return record

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to add favorite")
        raise HTTPException(status_code=500, detail="Failed to add favorite")
