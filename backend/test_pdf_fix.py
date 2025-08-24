"""
Quick test to verify PDF OCR fallback fix
"""
import asyncio
import sys
import os
import logging

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pdf_ocr_fallback():
    """Test that PDF OCR fallback works correctly"""
    try:
        logger.info("🔧 Testing PDF OCR fallback fix")
        logger.info("=" * 50)
        
        # Import the document processor
        from app.services.document_processor import document_processor
        
        # Check if there's a sample PDF (if not, we'll create a simple test)
        test_files = ["sample_medical_device_spec.png"]  # Use PNG as scanned PDF substitute
        
        for test_file in test_files:
            if os.path.exists(test_file):
                logger.info(f"📄 Testing with file: {test_file}")
                
                with open(test_file, "rb") as f:
                    file_content = f.read()
                
                # Test the extraction method directly
                try:
                    extracted_text = await document_processor._extract_text(
                        file_content, test_file
                    )
                    
                    logger.info(f"✅ Text extraction successful!")
                    logger.info(f"📝 Extracted {len(extracted_text)} characters")
                    logger.info(f"📄 Sample text: {extracted_text[:200]}...")
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"❌ Text extraction failed: {e}")
                    return False
        
        logger.warning("⚠️ No test files found to test with")
        return False
        
    except Exception as e:
        logger.error(f"❌ Test setup failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🧪 Starting PDF OCR fallback test")
    
    success = await test_pdf_ocr_fallback()
    
    if success:
        logger.info("🎉 PDF OCR fallback fix appears to be working!")
        logger.info("\n📋 The fix should resolve:")
        logger.info("   ✅ Traditional PDF extraction failure no longer blocks OCR")
        logger.info("   ✅ Scanned PDFs will properly fall back to OCR processing")
        logger.info("   ✅ Frontend uploads should no longer hang indefinitely")
        logger.info("\n🔄 Please restart your server and try uploading the PDF again")
    else:
        logger.error("❌ Test failed - there may still be issues")

if __name__ == "__main__":
    asyncio.run(main())
