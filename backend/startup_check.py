"""
Quick startup script to verify OCR and application readiness
Run this before starting the main application
"""
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if all required dependencies are available"""
    logger.info("🔍 Checking dependencies...")
    
    missing_deps = []
    
    # Check core dependencies
    try:
        import fastapi
        logger.info("✅ FastAPI available")
    except ImportError:
        missing_deps.append("fastapi")
    
    try:
        import PIL
        logger.info("✅ Pillow available")
    except ImportError:
        missing_deps.append("pillow")
    
    # Check OCR dependencies
    ocr_available = False
    try:
        import easyocr
        logger.info("✅ EasyOCR available")
        ocr_available = True
    except ImportError:
        logger.warning("⚠️ EasyOCR not available")
    
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        logger.info("✅ Tesseract available")
        ocr_available = True
    except ImportError:
        logger.warning("⚠️ Pytesseract not available")
    except Exception:
        logger.warning("⚠️ Tesseract not properly configured")
    
    if not ocr_available:
        logger.error("❌ No OCR engines available!")
        logger.info("📦 Install with: pip install easyocr pytesseract")
        missing_deps.append("ocr-engines")
    
    # Check PDF processing
    try:
        import fitz
        logger.info("✅ PyMuPDF available")
    except ImportError:
        logger.warning("⚠️ PyMuPDF not available - PDF OCR may be limited")
        missing_deps.append("pymupdf")
    
    return missing_deps

def check_ocr_service():
    """Test the OCR service quickly"""
    try:
        from app.services.simple_ocr_service import simple_ocr_service
        
        if simple_ocr_service.is_available():
            logger.info(f"✅ OCR service ready with methods: {simple_ocr_service.available_methods}")
            return True
        else:
            logger.error("❌ OCR service not available")
            return False
    except Exception as e:
        logger.error(f"❌ OCR service error: {e}")
        return False

def main():
    """Main startup check"""
    logger.info("🚀 RAG Fill Application Startup Check")
    logger.info("=" * 50)
    
    # Check dependencies
    missing_deps = check_dependencies()
    
    if missing_deps:
        logger.error(f"❌ Missing dependencies: {', '.join(missing_deps)}")
        logger.info("📦 Install missing dependencies with:")
        logger.info("   pip install -r requirements.txt")
        return False
    
    # Check OCR service
    ocr_ready = check_ocr_service()
    
    if not ocr_ready:
        logger.error("❌ OCR service not ready")
        return False
    
    logger.info("✅ All checks passed! Application is ready to start")
    logger.info("\n🚀 Start the application with:")
    logger.info("   python main.py")
    logger.info("\n📄 Supported file types for OCR:")
    logger.info("   - PDF files (scanned documents)")
    logger.info("   - PNG, JPG, JPEG images")
    logger.info("   - TIFF, BMP images")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
