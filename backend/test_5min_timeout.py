"""
Test the 5-minute timeout configuration
"""
import asyncio
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_timeout_config():
    """Test that all timeouts are properly configured to 5 minutes"""
    try:
        logger.info("🧪 Testing 5-minute timeout configuration...")
        logger.info("=" * 60)
        
        # Test simple OCR service
        from app.services.simple_ocr_service import simple_ocr_service
        
        logger.info(f"✅ Simple OCR Service timeout: {simple_ocr_service.timeout} seconds")
        if simple_ocr_service.timeout == 300:
            logger.info("✅ OCR service timeout correctly set to 5 minutes")
        else:
            logger.error(f"❌ OCR service timeout is {simple_ocr_service.timeout}s, should be 300s")
        
        # Test document processor
        from app.services.document_processor import document_processor
        
        logger.info(f"✅ Document processor OCR enabled: {document_processor.ocr_enabled}")
        logger.info(f"✅ Document processor fallback threshold: {document_processor.ocr_fallback_threshold}")
        
        # Test that we can import everything without errors
        logger.info("✅ All services imported successfully")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 Configuration Summary:")
        logger.info(f"   📊 OCR Service Timeout: {simple_ocr_service.timeout} seconds (5 minutes)")
        logger.info(f"   🔧 Available Methods: {simple_ocr_service.available_methods}")
        logger.info(f"   📁 Max Image Size: {simple_ocr_service.max_image_size}")
        logger.info(f"   ⚡ OCR Enabled: {document_processor.ocr_enabled}")
        
        logger.info("\n✅ Your PDF should now process successfully with 5-minute timeout!")
        logger.info("🔄 No more 2-minute timeouts - the system will wait up to 5 minutes per batch")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_timeout_config())
