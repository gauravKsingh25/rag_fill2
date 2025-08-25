"""
Document Reverse Processing API Router
Handles converting filled documents back to blank templates
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Dict, Any
import logging
from pathlib import Path
import os

from app.services.document_reverse_processor import document_reverse_processor
from app.routers.devices import get_device

router = APIRouter(prefix="/api/document-reverse", tags=["Document Reverse Processing"])
logger = logging.getLogger(__name__)

@router.post("/create-blank-template")
async def create_blank_template(
    device_id: str = Form(...),
    file: UploadFile = File(...)
) -> Dict[str, Any]:
    """
    Convert a filled document (PDF/Word) into a blank template
    
    - **PDF files**: Uses OCR to extract text, then creates blank template in Word format
    - **Word files**: Extracts text and creates blank template in Word format
    """
    try:
        logger.info(f"🔄 Creating blank template from {file.filename} for device {device_id}")
        
        # Verify device exists
        await get_device(device_id)
        
        # Check file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        file_extension = Path(file.filename).suffix.lower()
        supported_formats = document_reverse_processor.get_supported_formats()
        
        if file_extension not in supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}. Supported formats: {', '.join(supported_formats)}"
            )
        
        # Validate file size (limit to 10MB)
        file_content = await file.read()
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size / (1024*1024):.1f}MB"
            )
        
        # Process the document
        result = await document_reverse_processor.process_filled_document(
            file_content=file_content,
            filename=file.filename,
            device_id=device_id
        )
        
        logger.info(f"✅ Successfully created blank template from {file.filename}")
        
        return {
            "status": "success",
            "message": "Blank template created successfully",
            "device_id": device_id,
            "original_file": file.filename,
            "template_filename": Path(result["blank_template_path"]).name,
            "download_url": result["blank_template_url"],
            "processing_details": result["processing_details"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create blank template from {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create blank template: {str(e)}"
        )

@router.get("/download/{filename}")
async def download_blank_template(filename: str):
    """Download a generated blank template file"""
    try:
        file_path = document_reverse_processor.output_dir / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Verify it's a safe file within our output directory
        if not str(file_path.resolve()).startswith(str(document_reverse_processor.output_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")
        
        logger.info(f"📥 Downloading blank template: {filename}")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download file {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

@router.get("/supported-formats")
async def get_supported_formats() -> Dict[str, Any]:
    """Get information about supported input and output formats"""
    return {
        "supported_input_formats": document_reverse_processor.get_supported_formats(),
        "output_format": document_reverse_processor.get_output_format(),
        "description": {
            ".pdf": "PDF files (uses OCR to extract text)",
            ".docx": "Word documents (extracts text directly)",
            ".doc": "Legacy Word documents (extracts text directly)"
        },
        "max_file_size_mb": 10,
        "features": [
            "Automatic field detection",
            "Answer removal with blank field generation",
            "Structure preservation",
            "OCR support for scanned PDFs",
            "Word document output"
        ]
    }

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for the document reverse processing service"""
    try:
        # Check if output directory exists and is writable
        output_dir = document_reverse_processor.output_dir
        if not output_dir.exists():
            output_dir.mkdir(exist_ok=True)
        
        # Check OCR service availability
        from app.services.google_vision_ocr_service import google_vision_ocr_service
        ocr_available = google_vision_ocr_service.is_available()
        
        return {
            "status": "healthy",
            "service": "Document Reverse Processor",
            "output_directory": str(output_dir),
            "ocr_service_available": ocr_available,
            "supported_formats": document_reverse_processor.get_supported_formats()
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Service unhealthy: {str(e)}")

@router.delete("/cleanup")
async def cleanup_old_templates(older_than_hours: int = 24) -> Dict[str, Any]:
    """
    Cleanup old generated template files
    By default, removes files older than 24 hours
    """
    try:
        import time
        from datetime import datetime, timedelta
        
        output_dir = document_reverse_processor.output_dir
        if not output_dir.exists():
            return {"status": "success", "message": "No files to cleanup", "deleted_count": 0}
        
        # Calculate cutoff time
        cutoff_time = time.time() - (older_than_hours * 3600)
        
        deleted_count = 0
        for file_path in output_dir.glob("*.docx"):
            try:
                if file_path.stat().st_ctime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"🗑️ Deleted old template: {file_path.name}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete {file_path.name}: {e}")
        
        logger.info(f"🧹 Cleanup completed: {deleted_count} files deleted")
        
        return {
            "status": "success",
            "message": f"Cleanup completed successfully",
            "deleted_count": deleted_count,
            "cutoff_hours": older_than_hours
        }
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")
