"""
Debug script to check which OCR service is being used
"""
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_ocr_imports():
    """Check which OCR services are available and being used"""
    logger.info("🔍 Checking OCR service imports...")
    
    # Check simple OCR service
    try:
        from app.services.simple_ocr_service import simple_ocr_service
        logger.info(f"✅ Simple OCR Service available: {simple_ocr_service.is_available()}")
        logger.info(f"🔧 Methods: {simple_ocr_service.available_methods}")
        logger.info(f"⏰ Timeout: {simple_ocr_service.timeout} seconds")
    except Exception as e:
        logger.error(f"❌ Simple OCR Service not available: {e}")
    
    # Check old OCR service
    try:
        from app.services.ocr_service import ocr_service
        logger.info(f"⚠️ OLD OCR Service still importable!")
        logger.info(f"⚠️ This might be causing conflicts!")
    except Exception as e:
        logger.info(f"✅ Old OCR Service not importable: {e}")
    
    # Check document processor
    try:
        from app.services.document_processor import document_processor
        logger.info(f"✅ Document processor imported successfully")
        logger.info(f"🔧 OCR enabled: {document_processor.ocr_enabled}")
        logger.info(f"⏰ OCR fallback threshold: {document_processor.ocr_fallback_threshold}")
    except Exception as e:
        logger.error(f"❌ Document processor import failed: {e}")

def check_module_cache():
    """Check if old modules are cached"""
    logger.info("\n🔍 Checking module cache...")
    
    cached_modules = [name for name in sys.modules.keys() if 'ocr' in name.lower()]
    
    for module in cached_modules:
        logger.info(f"📦 Cached module: {module}")
        
    # Specifically check for OCR services
    if 'app.services.ocr_service' in sys.modules:
        logger.warning("⚠️ OLD OCR SERVICE IS CACHED - This could cause conflicts!")
    
    if 'app.services.simple_ocr_service' in sys.modules:
        logger.info("✅ Simple OCR service is cached")

if __name__ == "__main__":
    logger.info("🚀 Starting OCR service debug check...")
    logger.info("=" * 60)
    
    check_ocr_imports()
    check_module_cache()
    
    logger.info("\n" + "=" * 60)
    logger.info("🔧 Recommendations:")
    logger.info("   1. Restart your server completely to clear module cache")
    logger.info("   2. Check for any remaining imports of old OCR service") 
    logger.info("   3. Verify simple_ocr_service is being used")
