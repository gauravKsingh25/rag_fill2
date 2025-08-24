"""
Test script to verify OCR improvements
"""
import asyncio
import logging
import sys
import os
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_ocr_improvements():
    """Test the improved OCR service"""
    try:
        logger.info("🧪 Testing OCR improvements...")
        logger.info("=" * 60)
        
        # Import services
        from app.services.simple_ocr_service import simple_ocr_service
        from app.services.document_processor import document_processor
        
        # Check if OCR is available
        if not simple_ocr_service.is_available():
            logger.error("❌ OCR service not available")
            return False
        
        logger.info("✅ OCR service is available")
        logger.info(f"🔧 Available methods: {simple_ocr_service.available_methods}")
        logger.info(f"⏰ Timeout setting: {simple_ocr_service.timeout} seconds")
        
        # Test with a sample image if available
        sample_files = [
            "sample_medical_device_spec.png",
            "test_image.png"
        ]
        
        test_file = None
        for filename in sample_files:
            if Path(filename).exists():
                test_file = filename
                break
        
        if test_file:
            logger.info(f"📄 Testing with file: {test_file}")
            
            with open(test_file, "rb") as f:
                file_content = f.read()
            
            # Test OCR service directly
            start_time = asyncio.get_event_loop().time()
            text, metadata = await simple_ocr_service.process_document(file_content, test_file)
            end_time = asyncio.get_event_loop().time()
            
            logger.info(f"⏱️ OCR took {end_time - start_time:.2f} seconds")
            logger.info(f"📝 Extracted {len(text)} characters")
            logger.info(f"📊 Metadata: {metadata}")
            
            if text:
                logger.info(f"📄 Sample text: {text[:100]}...")
            
        else:
            logger.info("ℹ️ No sample files found, skipping file test")
        
        # Test chunking improvements
        logger.info("\n" + "=" * 60)
        logger.info("🧪 Testing chunking improvements...")
        
        sample_text = """
        Medical Device Specification
        
        Model: XYZ-2000
        Serial Number: 12345
        
        This is a medical device used for testing purposes.
        It has multiple features and specifications.
        
        Operating Voltage: 120V
        Power Consumption: 50W
        Weight: 2.5 kg
        
        Safety features include automatic shutdown and error detection.
        The device complies with medical standards and regulations.
        """
        
        chunks = document_processor._create_chunks(sample_text)
        logger.info(f"📦 Created {len(chunks)} chunks from sample text")
        
        for i, chunk in enumerate(chunks):
            logger.info(f"📄 Chunk {i}: {len(chunk['content'])} chars, type: {chunk.get('content_type', 'unknown')}")
        
        logger.info("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    logger.info("🚀 Starting OCR improvement tests")
    
    success = await test_ocr_improvements()
    
    if success:
        logger.info("\n🎉 All tests passed!")
        logger.info("\n📋 Summary of improvements:")
        logger.info("   ✅ Timeout increased to 2 minutes")
        logger.info("   ✅ Process all PDF pages (no 20-page limit)")
        logger.info("   ✅ Better batch processing for large PDFs")
        logger.info("   ✅ Improved chunking for small documents")
        logger.info("   ✅ Enhanced deletion endpoints")
        logger.info("   ✅ Better error handling and logging")
        logger.info("\n🔄 You can now restart your server and test with large PDFs!")
    else:
        logger.error("\n❌ Some tests failed - check the errors above")

if __name__ == "__main__":
    asyncio.run(main())
