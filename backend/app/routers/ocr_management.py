"""
Minimal OCR Management Router
Prevents import errors during transition
"""

from fastapi import APIRouter

# Create a minimal router to prevent import errors
router = APIRouter(prefix="/ocr-deprecated", tags=["OCR Management - Deprecated"])

@router.get("/status")
async def deprecated_status():
    """Deprecated endpoint"""
    return {
        "message": "This endpoint is deprecated. Use /api/ocr/status instead",
        "available": False,
        "enabled": False
    }

@router.get("/health")  
async def deprecated_health():
    """Deprecated health check"""
    return {
        "status": "deprecated",
        "message": "Use /api/ocr/health instead"
    }
