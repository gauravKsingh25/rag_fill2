"""
Quick test to verify OCR fix for async/blocking issue
"""
import asyncio
import sys
import os
import logging
from pathlib import Path

# Add the backend directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_ocr_fix():
    """Test that OCR no longer blocks the event loop"""
    try:
        logger.info("🔧 Testing OCR fix for async/blocking issue")
        logger.info("=" * 50)
        
        # Import the OCR service
        from app.services.ocr_service import ocr_service
        
        # Check if sample image exists
        sample_image_path = Path("sample_medical_device_spec.png")
        if not sample_image_path.exists():
            logger.error("❌ Sample image not found - creating a simple test image")
            
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a test image
            img = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add test text
            try:
                font = ImageFont.load_default()
                draw.text((50, 50), "TEST DOCUMENT", fill='black', font=font)
                draw.text((50, 100), "Medical Device: Model XYZ", fill='black', font=font)
                draw.text((50, 150), "Serial Number: 12345", fill='black', font=font)
            except:
                draw.text((50, 50), "TEST DOCUMENT", fill='black')
                draw.text((50, 100), "Medical Device: Model XYZ", fill='black')
                draw.text((50, 150), "Serial Number: 12345", fill='black')
            
            img.save("test_image.png")
            sample_image_path = Path("test_image.png")
            logger.info("✅ Created test image: test_image.png")
        
        # Test OCR with timeout
        logger.info("🔍 Testing OCR processing with new async fix...")
        
        with open(sample_image_path, "rb") as f:
            image_bytes = f.read()
        
        # This should no longer block the event loop
        start_time = asyncio.get_event_loop().time()
        
        try:
            result_text, result_metadata = await asyncio.wait_for(
                ocr_service.process_document(image_bytes, str(sample_image_path), force_ocr=True),
                timeout=30.0  # 30 second timeout for test
            )
            
            end_time = asyncio.get_event_loop().time()
            processing_time = end_time - start_time
            
            logger.info(f"✅ OCR processing completed in {processing_time:.2f} seconds")
            logger.info(f"📝 Extracted text length: {len(result_text)} characters")
            logger.info(f"📊 OCR metadata: {result_metadata}")
            
            if result_text.strip():
                logger.info(f"📄 Sample extracted text: {result_text[:200]}...")
                logger.info("✅ OCR fix successful - processing completed without blocking")
            else:
                logger.warning("⚠️ No text extracted, but processing completed without hanging")
            
            return True
            
        except asyncio.TimeoutError:
            logger.error("❌ OCR processing still hangs - timeout reached")
            return False
        except Exception as e:
            logger.error(f"❌ OCR processing failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test setup failed: {e}")
        return False

async def main():
    """Main test function"""
    logger.info("🧪 Starting OCR fix verification test")
    
    # Run multiple tests to ensure reliability
    success_count = 0
    total_tests = 2
    
    for i in range(total_tests):
        logger.info(f"\n🔄 Test run {i+1}/{total_tests}")
        if await test_ocr_fix():
            success_count += 1
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    logger.info(f"\n📊 Test Results: {success_count}/{total_tests} successful")
    
    if success_count == total_tests:
        logger.info("🎉 All tests passed! OCR fix appears to be working")
        logger.info("\n📋 Next steps:")
        logger.info("   1. Restart your FastAPI server")
        logger.info("   2. Try uploading the problematic PDF from frontend")
        logger.info("   3. Check server logs for any remaining issues")
    else:
        logger.error("❌ Some tests failed - OCR may still have issues")
        logger.info("\n🔧 Debugging suggestions:")
        logger.info("   1. Check EasyOCR installation: pip install easyocr")
        logger.info("   2. Verify PIL/Pillow compatibility: pip install --upgrade Pillow")
        logger.info("   3. Check available memory and CPU resources")

if __name__ == "__main__":
    asyncio.run(main())
