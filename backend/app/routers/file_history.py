"""
File History Management

This module handles the file history functionality for tracking processed, analyzed, and filled files.

IMPORTANT WORKFLOW DISTINCTION:
- File History: For files that are processed/analyzed by the system
  * Filled templates (docx)
  * Processed/filled CSV files  
  * Analyzed files (templates and CSV)
  * Any system-generated output files

- Favorites: ONLY for files manually uploaded by users via "Add to Favorites" button
  * User-selected files to be marked as favorites
  * Manual file uploads to favorites section
  * Should NOT be used by processing endpoints

USAGE:
- All analyze/process endpoints should use add_file_to_history()
- Only explicit user "add to favorites" actions should use favorites router
- This ensures proper separation of user-curated vs system-generated content
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime
from pathlib import Path

from app.services import gcs_service
from app.database import mongodb

router = APIRouter()
logger = logging.getLogger(__name__)

# GCS index blob for file history - uses the default GCS bucket (separate from favorites)
GCS_INDEX_BLOB = "file_history/index.json"


async def add_file_to_history(
    filename: str,
    file_path: Optional[str] = None,
    file_obj: Optional[object] = None,
    content_type: str = "application/octet-stream",
    file_type: str = "processed",
    gcs_folder: str = "processed_files"
) -> Dict[str, Any]:
    """
    Helper function to add a file to file history.
    Can be called by other routers to track processed files.
    
    Args:
        filename: Name of the file
        file_path: Local file path (if file exists locally)
        file_obj: File object (if uploading from memory)
        content_type: MIME type of the file
        file_type: Type of file (e.g., "filled", "processed", "analyzed")
        gcs_folder: GCS folder to store the file in
    
    Returns:
        Dict with file metadata including GCS URL
    """
    try:
        if not gcs_service.is_available():
            logger.warning("GCS not available - cannot add file to history")
            return {"filename": filename, "url": "", "type": file_type, "timestamp": datetime.utcnow().isoformat() + "Z"}
        
        # Generate destination name with timestamp
        timestamp_str = int(datetime.utcnow().timestamp())
        dest_name = f"{gcs_folder}/{timestamp_str}_{filename}"
        
        # Upload file to GCS
        if file_path and Path(file_path).exists():
            # Upload from local file
            with open(file_path, 'rb') as f:
                gcs_service.upload_fileobj(f, dest_name, content_type=content_type)
                logger.info(f"📁 Uploaded file to default GCS bucket (file history): {dest_name}")
        elif file_obj:
            # Upload from file object
            gcs_service.upload_fileobj(file_obj, dest_name, content_type=content_type)
            logger.info(f"📁 Uploaded file object to default GCS bucket (file history): {dest_name}")
        else:
            logger.warning(f"No valid file source provided for {filename}")
            return {"filename": filename, "url": "", "type": file_type, "timestamp": datetime.utcnow().isoformat() + "Z"}
        
        # Generate signed URL
        try:
            url = gcs_service.generate_signed_url(dest_name, expires_seconds=3600*24*7)
        except Exception as e:
            logger.error(f"Failed to generate signed URL: {e}")
            url = ""
        
        # Create record
        record = {
            "filename": filename,
            "url": url,
            "type": file_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "content_type": content_type,
            "size_bytes": Path(file_path).stat().st_size if file_path and Path(file_path).exists() else None
        }
        
        # Add to file history index
        items = await _load_index_from_gcs()
        items.insert(0, record)
        await _save_index_to_gcs(items)
        
        logger.info(f"Added file to history: {filename} -> {dest_name}")
        return record
        
    except Exception as e:
        logger.error(f"Failed to add file to history: {e}")
        return {"filename": filename, "url": "", "type": file_type, "timestamp": datetime.utcnow().isoformat() + "Z"}


async def _load_index_from_gcs() -> List[Dict[str, Any]]:
    # Only use GCS - no local fallback
    if not gcs_service.is_available():
        logger.error("GCS not available - file history requires GCS configuration")
        raise HTTPException(status_code=503, detail="File history service unavailable - GCS not configured")
    
    try:
        text = gcs_service.download_blob_as_text(GCS_INDEX_BLOB)
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Failed to load index from GCS: {e}; returning empty list")
        # Return empty list instead of falling back to local
        return []


async def _save_index_to_gcs(items: List[Dict[str, Any]]):
    # Only use GCS - no local fallback
    if not gcs_service.is_available():
        logger.error("GCS not available - cannot save file history index")
        raise HTTPException(status_code=503, detail="File history service unavailable - GCS not configured")
    
    try:
        gcs_service.upload_json(items, GCS_INDEX_BLOB)
        return True
    except Exception as e:
        logger.error(f"Failed to save index to GCS: {e}")
        raise HTTPException(status_code=500, detail="Failed to save file history to GCS")


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
                        raise HTTPException(status_code=500, detail="Failed to generate file access URL")
                except Exception as upload_err:
                    msg = str(upload_err)
                    logger.error(f"Error during file upload to GCS: {msg}")
                    raise HTTPException(status_code=500, detail="Failed to upload file to storage")
            else:
                # GCS not available: cannot proceed
                logger.error("GCS not available: file history requires GCS configuration")
                raise HTTPException(status_code=503, detail="File upload unavailable - GCS not configured")

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


@router.delete("/{filename}")
async def delete_history_item(filename: str):
    """
    Delete a file history item by filename
    """
    try:
        items = await _load_index_from_gcs()
        
        # Find the item to delete
        item_to_delete = None
        updated_items = []
        
        for item in items:
            if item.get("filename") == filename:
                item_to_delete = item
            else:
                updated_items.append(item)
        
        if item_to_delete is None:
            raise HTTPException(status_code=404, detail="File history item not found")
        
        # If the item has a GCS URL, try to delete the file from GCS
        if item_to_delete.get("url") and gcs_service.is_available():
            try:
                # Extract the blob name from the URL
                # The blob name format for file history is: processed_files/{timestamp}_{filename} or {timestamp}_{filename}
                url = item_to_delete["url"]
                if "storage.googleapis.com" in url:
                    # Try to extract blob name from URL
                    import re
                    # Look for patterns like processed_files/timestamp_filename or timestamp_filename
                    match = re.search(r'(?:processed_files/|filled_csv/|)(\d+_[^?&/]*)', url)
                    if match:
                        blob_name = match.group(0)  # This includes the folder prefix if present
                        # Use the regular delete method since file history uses the default bucket
                        gcs_service._ensure_client()
                        if gcs_service._bucket:
                            blob = gcs_service._bucket.blob(blob_name)
                            blob.delete()
                            logger.info(f"✅ Deleted file history file from GCS: {blob_name}")
            except Exception as delete_err:
                logger.warning(f"Failed to delete file history file from GCS: {delete_err}")
        
        # Save the updated index
        ok = await _save_index_to_gcs(updated_items)
        if not ok:
            logger.warning("Failed to persist file history index after deletion")
        
        logger.info(f"✅ Deleted file history item: {filename}")
        return {"message": f"File history item '{filename}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete file history item")
        raise HTTPException(status_code=500, detail="Failed to delete file history item")
