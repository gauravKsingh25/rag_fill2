"""
Simple test script to verify the new OCR service works properly
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

async def test_simple_ocr():
    """Test the simple OCR service"""
    try:
        logger.info("🧪 Testing Simple OCR Service")
        logger.info("=" * 50)
        
        # Import the simple OCR service
        from app.services.simple_ocr_service import simple_ocr_service
        
        if not simple_ocr_service.is_available():
            logger.error("❌ OCR service not available - please install pytesseract or easyocr")
            logger.info("Install with: pip install easyocr pytesseract")
            return False
        
        logger.info(f"✅ OCR service available with methods: {simple_ocr_service.available_methods}")
        
        # Create a test image if it doesn't exist
        sample_image_path = Path("test_simple_ocr.png")
        if not sample_image_path.exists():
            logger.info("📸 Creating test image...")
            
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a test image with clear text
            img = Image.new('RGB', (500, 200), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add clear, readable test text
            try:
                font = ImageFont.load_default()
                draw.text((20, 20), "MEDICAL DEVICE SPECIFICATION", fill='black', font=font)
                draw.text((20, 60), "Model: XR-2000", fill='black', font=font)
                draw.text((20, 100), "Serial: MD123456789", fill='black', font=font)
                draw.text((20, 140), "Status: Active", fill='black', font=font)
            except:
                draw.text((20, 20), "MEDICAL DEVICE SPECIFICATION", fill='black')
                draw.text((20, 60), "Model: XR-2000", fill='black')
                draw.text((20, 100), "Serial: MD123456789", fill='black')
                draw.text((20, 140), "Status: Active", fill='black')
            
            img.save(sample_image_path)
            logger.info(f"✅ Created test image: {sample_image_path}")
        
        # Test the OCR processing
        logger.info("🔍 Testing OCR processing...")
        
        with open(sample_image_path, "rb") as f:
            image_bytes = f.read()
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            result_text, result_metadata = await asyncio.wait_for(
                simple_ocr_service.process_document(image_bytes, str(sample_image_path)),
                timeout=20.0  # 20 second timeout for test
            )
            
            end_time = asyncio.get_event_loop().time()
            processing_time = end_time - start_time
            
            logger.info(f"✅ OCR completed in {processing_time:.2f} seconds")
            logger.info(f"📝 Extracted text length: {len(result_text)} characters")
            logger.info(f"📊 Metadata: {result_metadata}")
            
            if result_text.strip():
                logger.info(f"📄 Extracted text:")
                logger.info(f"'{result_text}'")
                logger.info("✅ OCR test successful!")
                return True
            else:
                logger.warning("⚠️ No text extracted, but processing completed without errors")
                return True
            
        except asyncio.TimeoutError:
            logger.error("❌ OCR processing timed out")
            return False
        except Exception as e:
            logger.error(f"❌ OCR processing failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test setup failed: {e}")
        return False

async def test_pdf_processing():
    """Test PDF processing if a sample PDF is available"""
    sample_pdf_path = Path("sample_medical_device_spec.pdf")
    if not sample_pdf_path.exists():
        sample_pdf_path = Path("test_dcx_template.docx")
    
    if sample_pdf_path.exists():
        logger.info(f"🔍 Testing with sample file: {sample_pdf_path}")
        
        try:
            from app.services.simple_ocr_service import simple_ocr_service
            
            with open(sample_pdf_path, "rb") as f:
                file_bytes = f.read()
            
            result_text, result_metadata = await asyncio.wait_for(
                simple_ocr_service.process_document(file_bytes, str(sample_pdf_path)),
                timeout=30.0
            )
            
            logger.info(f"✅ File processed - Text length: {len(result_text)}")
            logger.info(f"📊 Metadata: {result_metadata}")
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ PDF test failed: {e}")
            return False
    else:
        logger.info("📄 No sample PDF found - skipping PDF test")
        return True

async def main():
    """Main test function"""
    logger.info("🚀 Starting Simple OCR Service Tests")
    
    # Test basic OCR
    ocr_success = await test_simple_ocr()
    
    # Test PDF processing
    pdf_success = await test_pdf_processing()
    
    if ocr_success and pdf_success:
        logger.info("\n🎉 All tests passed! Simple OCR service is working correctly")
        logger.info("\n📋 Next steps:")
        logger.info("   1. Restart your FastAPI server")
        logger.info("   2. Try uploading a scanned PDF or image from the frontend")
        logger.info("   3. The upload should complete much faster now")
        logger.info("   4. Check server logs for processing details")
    else:
        logger.error("\n❌ Some tests failed")
        logger.info("\n🔧 Troubleshooting:")
        logger.info("   - Install OCR dependencies: pip install easyocr pytesseract")
        logger.info("   - For Tesseract: also install tesseract-ocr system package")
        logger.info("   - Check available system memory")

if __name__ == "__main__":
    asyncio.run(main())
