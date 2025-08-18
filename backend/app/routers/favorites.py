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
        text = gcs_service.download_blob_as_text(GCS_INDEX_BLOB)
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Failed to load favorites index from GCS: {e}; falling back to local")
        return _load_index_local()


async def _save_index_to_gcs(items: List[Dict[str, Any]]):
    if not gcs_service.is_available():
        return _save_index_local(items)
    try:
        gcs_service.upload_json(items, GCS_INDEX_BLOB)
        return True
    except Exception as e:
        logger.error(f"Failed to save favorites index to GCS: {e}; falling back to local")
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
                    gcs_service.upload_fileobj(file.file, dest_name, content_type=file.content_type)
                    try:
                        url = gcs_service.generate_signed_url(dest_name, expires_seconds=3600*24*7)
                    except Exception:
                        url = ""
                except Exception as upload_err:
                    logger.error(f"Failed to upload favorite to GCS: {upload_err}")
                    url = ""
            else:
                url = ""

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
