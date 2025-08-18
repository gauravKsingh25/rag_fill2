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

# Ensure GCS_BUCKET is set and not blank
if not gcs_service.GCS_BUCKET or not gcs_service.GCS_BUCKET.strip():
	logger.error("GCS_BUCKET environment variable is not set or blank. File history API will not work.")
	raise HTTPException(status_code=503, detail="GCS_BUCKET environment variable is required and must not be blank.")

# When MongoDB is not available, store metadata index in GCS at 'file_history/index.json'
GCS_INDEX_BLOB = "file_history/index.json"


async def _load_index_from_gcs() -> List[Dict[str, Any]]:
	try:
		text = gcs_service.download_blob_as_text(GCS_INDEX_BLOB)
		import json
		return json.loads(text)
	except Exception:
		return []


async def _save_index_to_gcs(items: List[Dict[str, Any]]):
	try:
		import json
		gcs_service.upload_json(items, GCS_INDEX_BLOB)
		return True
	except Exception as e:
		logger.error(f"Failed to save index to GCS: {e}")
		return False


@router.get("/", response_model=List[Dict[str, Any]])
async def get_history():
	# Always use GCS for file history
	try:
		return await _load_index_from_gcs()
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
	"""Upload file to GCS (if configured) and persist metadata to DB or local file."""
	try:
		record = {}
		if file is not None:
			# Build destination name with timestamp
			dest_name = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
			if gcs_service.is_available():
				# Upload to GCS
				# attempt to determine file size (UploadFile.file may have .seek)
				try:
					logger.info(f"Starting upload for file: {file.filename} as {dest_name}")
					upload_start = datetime.utcnow()
					try:
						record = {}
						if file is not None:
							# Build destination name with timestamp
							dest_name = f"{int(datetime.utcnow().timestamp())}_{file.filename}"
							if gcs_service.is_available():
								logger.info(f"Starting upload for file: {file.filename} as {dest_name}")
								upload_start = datetime.utcnow()
								# Upload to GCS
								# attempt to determine file size (UploadFile.file may have .seek)
								try:
									pos = file.file.tell()
									file.file.seek(0, 2)
									size = file.file.tell()
									file.file.seek(pos)
								except Exception:
									size = None

								logger.info(f"File size determined: {size} bytes")
								try:
									gcs_service.upload_fileobj(file.file, dest_name, content_type=file.content_type)
								except Exception as upload_err:
									logger.error(f"Error during file upload to GCS: {upload_err}")
									raise HTTPException(status_code=500, detail="File upload failed")
								upload_end = datetime.utcnow()
								logger.info(f"File upload completed for {dest_name} in {(upload_end-upload_start).total_seconds()} seconds")

								url_start = datetime.utcnow()
								# Generate a signed url for download
								url = gcs_service.generate_signed_url(dest_name, expires_seconds=3600*24*7)
								url_end = datetime.utcnow()
								logger.info(f"Signed URL generated for {dest_name} in {(url_end-url_start).total_seconds()} seconds: {url}")
							else:
								# If GCS not available, we do not save the file (per user's request to avoid local storage)
								raise HTTPException(status_code=503, detail="Storage backend not configured")

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

						# Persist index to GCS only
						index_start = datetime.utcnow()
						items = await _load_index_from_gcs()
						items.insert(0, record)
						await _save_index_to_gcs(items)
						index_end = datetime.utcnow()
						logger.info(f"Index updated and saved to GCS in {(index_end-index_start).total_seconds()} seconds. Total items: {len(items)}")
						return record

					except HTTPException:
						raise
					except Exception as e:
						logger.error(f"Failed to add history item: {e}")
						raise HTTPException(status_code=500, detail="Failed to add history item")
