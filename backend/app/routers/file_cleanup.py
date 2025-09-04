"""
File Cleanup Router

Provides endpoints for managing local file cleanup.
Files are stored locally temporarily for download but should be cleaned up
since they are already backed up to GCS.

Endpoints:
- GET /storage-info - Get current storage usage information
- POST /cleanup-old - Clean up files older than specified age
- POST /cleanup-all - Clean up all local files (use with caution)
- DELETE /cleanup/{filename} - Clean up a specific file
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional
import logging

from app.services.file_cleanup_service import file_cleanup_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/storage-info")
async def get_storage_info():
    """
    Get information about current local storage usage for filled templates and CSVs.
    Shows file count, total size, and individual file details.
    """
    try:
        info = await file_cleanup_service.get_storage_info()
        logger.info(f"📊 Storage info requested - {info.get('total_files', 0)} files, {info.get('total_size_mb', 0)} MB")
        return info
        
    except Exception as e:
        logger.error(f"❌ Failed to get storage info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {e}")

@router.post("/cleanup-old")
async def cleanup_old_files(
    max_age_hours: Optional[int] = Query(24, description="Clean files older than this many hours")
):
    """
    Clean up local files older than the specified age.
    Default is 24 hours. Files are already backed up to GCS via file history.
    """
    try:
        if max_age_hours < 1:
            raise HTTPException(status_code=400, detail="max_age_hours must be at least 1")
        
        result = await file_cleanup_service.cleanup_old_files(max_age_hours)
        
        if result['success']:
            logger.info(f"🧹 Old files cleanup completed: {result['message']}")
        else:
            logger.warning(f"⚠️ Old files cleanup had issues: {result.get('message', 'Unknown error')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cleanup old files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup old files: {e}")

@router.post("/cleanup-all")
async def cleanup_all_files():
    """
    Clean up ALL local files in the filled templates directory.
    ⚠️  Use with caution - this removes all local copies.
    Files are already backed up to GCS via file history.
    """
    try:
        result = await file_cleanup_service.cleanup_all_files()
        
        if result['success']:
            logger.info(f"🧹 All files cleanup completed: {result['message']}")
        else:
            logger.warning(f"⚠️ All files cleanup had issues: {result.get('message', 'Unknown error')}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to cleanup all files: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup all files: {e}")

@router.delete("/cleanup/{filename}")
async def cleanup_specific_file(filename: str):
    """
    Clean up a specific file by filename.
    File must exist in the filled templates directory.
    """
    try:
        # Basic filename validation
        if not filename or '..' in filename or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        result = await file_cleanup_service.cleanup_specific_file(filename)
        
        if result['success']:
            logger.info(f"🧹 Specific file cleanup completed: {result['message']}")
        else:
            logger.warning(f"⚠️ Specific file cleanup had issues: {result.get('message', 'Unknown error')}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cleanup specific file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup specific file: {e}")

@router.post("/auto-cleanup")
async def trigger_auto_cleanup():
    """
    Trigger automatic cleanup based on default policies:
    - Remove files older than 24 hours
    - Clean up if more than 10 files or total size > 100MB
    """
    try:
        # Get current storage info
        storage_info = await file_cleanup_service.get_storage_info()
        
        cleanup_needed = False
        cleanup_reason = []
        
        # Check if cleanup is recommended
        recommendations = storage_info.get('cleanup_recommendations', {})
        
        if recommendations.get('old_files_count', 0) > 0:
            cleanup_needed = True
            cleanup_reason.append(f"{recommendations['old_files_count']} files older than 24 hours")
        
        if recommendations.get('should_cleanup', False):
            cleanup_needed = True
            if storage_info.get('total_files', 0) > 10:
                cleanup_reason.append(f"{storage_info['total_files']} files (threshold: 10)")
            if storage_info.get('total_size_mb', 0) > 100:
                cleanup_reason.append(f"{storage_info['total_size_mb']} MB (threshold: 100 MB)")
        
        if not cleanup_needed:
            return {
                'success': True,
                'cleanup_performed': False,
                'message': 'No cleanup needed',
                'storage_info': storage_info
            }
        
        # Perform cleanup
        result = await file_cleanup_service.cleanup_old_files()
        
        logger.info(f"🤖 Auto-cleanup triggered: {', '.join(cleanup_reason)}")
        
        return {
            'success': result['success'],
            'cleanup_performed': True,
            'cleanup_reason': cleanup_reason,
            'cleanup_result': result,
            'message': f"Auto-cleanup completed: {result.get('message', 'Unknown result')}"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to perform auto cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to perform auto cleanup: {e}")
