"""
Simple OCR Management Router
Provides basic OCR service status and statistics
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

from app.core.auth import get_current_user
from app.models import User

# Simple OCR Service
try:
    from app.services.simple_ocr_service import simple_ocr_service
    OCR_AVAILABLE = simple_ocr_service.is_available()
except ImportError:
    OCR_AVAILABLE = False

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ocr", tags=["OCR Management"])

class OCRStatusResponse(BaseModel):
    """OCR service status response"""
    available: bool
    enabled: bool
    available_methods: List[str]
    configuration: Dict[str, Any]
    processing_statistics: Optional[Dict[str, Any]] = None

@router.get("/status", response_model=OCRStatusResponse)
async def get_ocr_status(current_user: User = Depends(get_current_user)):
    """Get current OCR service status and configuration"""
    try:
        if not OCR_AVAILABLE:
            return OCRStatusResponse(
                available=False,
                enabled=False,
                available_methods=[],
                configuration={"error": "OCR service not available"},
                processing_statistics=None
            )
        
        return OCRStatusResponse(
            available=True,
            enabled=True,
            available_methods=simple_ocr_service.available_methods,
            configuration={
                "timeout": simple_ocr_service.timeout,
                "max_image_size": simple_ocr_service.max_image_size,
                "available_methods": simple_ocr_service.available_methods,
                "service_type": "simple_ocr_service"
            },
            processing_statistics={
                "service_available": OCR_AVAILABLE,
                "methods_count": len(simple_ocr_service.available_methods),
                "timeout_seconds": simple_ocr_service.timeout
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to get OCR status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get OCR status: {e}")

@router.get("/test")
async def test_ocr_service(current_user: User = Depends(get_current_user)):
    """Test OCR service availability"""
    try:
        if not OCR_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "OCR service is not available",
                "available_methods": []
            }
        
        return {
            "status": "available",
            "message": "OCR service is working",
            "available_methods": simple_ocr_service.available_methods,
            "timeout": simple_ocr_service.timeout,
            "service_type": "simple_ocr_service"
        }
        
    except Exception as e:
        logger.error(f"❌ OCR test failed: {e}")
        return {
            "status": "error",
            "message": f"OCR test failed: {e}",
            "available_methods": []
        }

@router.get("/methods")
async def get_ocr_methods(current_user: User = Depends(get_current_user)):
    """Get available OCR methods and their status"""
    try:
        if not OCR_AVAILABLE:
            return {
                "available_methods": [],
                "recommendations": ["Install pytesseract or easyocr to enable OCR"]
            }
        
        methods_info = []
        for method in simple_ocr_service.available_methods:
            if method == "tesseract":
                methods_info.append({
                    "name": "tesseract",
                    "status": "available",
                    "description": "Fast text recognition for most documents",
                    "best_for": "typed text, documents with good quality"
                })
            elif method == "easyocr":
                methods_info.append({
                    "name": "easyocr",
                    "status": "available", 
                    "description": "Deep learning OCR with good accuracy",
                    "best_for": "handwritten text, complex layouts, multiple languages"
                })
        
        recommendations = []
        if not methods_info:
            recommendations.append("No OCR methods available - install pytesseract or easyocr")
        elif len(methods_info) == 1:
            recommendations.append("Consider installing additional OCR engines for better results")
        
        return {
            "available_methods": methods_info,
            "recommendations": recommendations,
            "timeout_seconds": simple_ocr_service.timeout
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get OCR methods: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get OCR methods: {e}")

@router.get("/health")
async def ocr_health_check():
    """Health check endpoint for OCR service"""
    try:
        health_status = {
            "service": "OCR Management",
            "status": "healthy" if OCR_AVAILABLE else "unavailable",
            "ocr_available": OCR_AVAILABLE,
            "timestamp": "2025-08-23T16:00:00Z"
        }
        
        if OCR_AVAILABLE:
            health_status.update({
                "available_methods": simple_ocr_service.available_methods,
                "timeout_configured": simple_ocr_service.timeout,
                "max_image_size": simple_ocr_service.max_image_size
            })
        
        return health_status
        
    except Exception as e:
        logger.error(f"❌ OCR health check failed: {e}")
        return {
            "service": "OCR Management",
            "status": "error",
            "error": str(e),
            "ocr_available": False
        }
