"""
Google Vision OCR Management Router
API endpoints for managing Google Vision OCR service
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from app.services.google_vision_ocr_service import google_vision_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-vision-ocr", tags=["Google Vision OCR"])

@router.get("/status")
async def get_google_vision_ocr_status() -> Dict[str, Any]:
    """Get Google Vision OCR service status"""
    try:
        is_available = google_vision_ocr_service.is_available()
        
        status = {
            "available": is_available,
            "service": "Google Cloud Vision",
            "credentials_configured": google_vision_ocr_service.credentials_path is not None,
            "client_initialized": google_vision_ocr_service.client is not None,
            "max_image_size": google_vision_ocr_service.max_image_size,
            "timeout": google_vision_ocr_service.timeout
        }
        
        if not is_available:
            status["error_reasons"] = []
            if not google_vision_ocr_service.credentials_path:
                status["error_reasons"].append("Google credentials not found")
            if not google_vision_ocr_service.client:
                status["error_reasons"].append("Google Vision client not initialized")
        
        return status
        
    except Exception as e:
        logger.error(f"❌ Failed to get Google Vision OCR status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get OCR status: {str(e)}")

@router.get("/test")
async def test_google_vision_ocr() -> Dict[str, Any]:
    """Test Google Vision OCR service functionality"""
    try:
        # Test basic availability
        if not google_vision_ocr_service.is_available():
            return {
                "test_passed": False,
                "error": "Google Vision OCR service not available"
            }
        
        # Test credentials and client
        if not google_vision_ocr_service.client:
            return {
                "test_passed": False,
                "error": "Google Vision client not initialized"
            }
        
        return {
            "test_passed": True,
            "service": "Google Cloud Vision",
            "credentials_path": google_vision_ocr_service.credentials_path,
            "client_type": str(type(google_vision_ocr_service.client)),
            "message": "Google Vision OCR service is ready"
        }
        
    except Exception as e:
        logger.error(f"❌ Google Vision OCR test failed: {e}")
        return {
            "test_passed": False,
            "error": str(e)
        }

@router.get("/capabilities")
async def get_google_vision_capabilities() -> Dict[str, Any]:
    """Get Google Vision OCR capabilities"""
    try:
        return {
            "supported_formats": [".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".gif", ".webp"],
            "features": [
                "High-accuracy text detection",
                "Multi-language support",
                "Document structure analysis",
                "Confidence scoring",
                "Large document processing",
                "Cloud-based processing"
            ],
            "api_features": [
                "TEXT_DETECTION",
                "DOCUMENT_TEXT_DETECTION",
                "Language detection",
                "Block-level analysis",
                "Word-level confidence"
            ],
            "advantages": [
                "Google's advanced OCR technology",
                "Superior accuracy for complex documents",
                "Built-in language detection",
                "Scalable cloud processing",
                "Regular ML model updates"
            ],
            "max_image_size": google_vision_ocr_service.max_image_size,
            "timeout_settings": {
                "per_operation": f"{google_vision_ocr_service.timeout}s",
                "per_image": "60s",
                "per_batch": "120s"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get Google Vision capabilities: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {str(e)}")

@router.get("/config")
async def get_google_vision_config() -> Dict[str, Any]:
    """Get current Google Vision OCR configuration"""
    try:
        config = {
            "service_available": google_vision_ocr_service.is_available(),
            "credentials_configured": google_vision_ocr_service.credentials_path is not None,
            "credentials_path": google_vision_ocr_service.credentials_path,
            "client_initialized": google_vision_ocr_service.client is not None,
            "settings": {
                "max_image_size": google_vision_ocr_service.max_image_size,
                "timeout": google_vision_ocr_service.timeout,
                "language_hints": ["en"],  # Currently configured for English
                "confidence_threshold": 0.3  # Minimum confidence for text detection
            },
            "environment_variables": {
                "GOOGLE_APPLICATION_CREDENTIALS": google_vision_ocr_service.credentials_path,
                "OCR_ENABLED": "true",  # Should be enabled for Google Vision
                "FORCE_OCR": "false"  # Use intelligent detection
            }
        }
        
        return config
        
    except Exception as e:
        logger.error(f"❌ Failed to get Google Vision config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@router.post("/reinitialize")
async def reinitialize_google_vision() -> Dict[str, Any]:
    """Reinitialize Google Vision OCR service"""
    try:
        # Reinitialize the client
        google_vision_ocr_service._initialize_client()
        
        is_available = google_vision_ocr_service.is_available()
        
        return {
            "reinitialized": True,
            "available": is_available,
            "client_initialized": google_vision_ocr_service.client is not None,
            "credentials_path": google_vision_ocr_service.credentials_path,
            "message": "Google Vision OCR service reinitialized" if is_available else "Reinitialization failed"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to reinitialize Google Vision: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reinitialize: {str(e)}")


