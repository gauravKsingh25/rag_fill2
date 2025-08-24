"""
Test Google Vision OCR Service
Verify that Google Vision OCR is properly configured and working
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the backend directory to sys.path to import our modules
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.google_vision_ocr_service import google_vision_ocr_service

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_google_vision_ocr():
    """Test Google Vision OCR service configuration and functionality"""
    
    print("🧪 Testing Google Vision OCR Service...")
    print("=" * 60)
    
    try:
        # Test 1: Check availability
        print("📋 Test 1: Service Availability")
        is_available = google_vision_ocr_service.is_available()
        print(f"   ✅ Service Available: {is_available}")
        
        if not is_available:
            print("   ❌ Google Vision OCR service is not available")
            print(f"   📝 Credentials path: {google_vision_ocr_service.credentials_path}")
            print(f"   📝 Client initialized: {google_vision_ocr_service.client is not None}")
            return False
        
        # Test 2: Configuration check
        print("\n📋 Test 2: Configuration")
        print(f"   🔧 Max image size: {google_vision_ocr_service.max_image_size}")
        print(f"   ⏱️ Timeout: {google_vision_ocr_service.timeout}s")
        print(f"   🔐 Credentials path: {google_vision_ocr_service.credentials_path}")
        print(f"   🤖 Client type: {type(google_vision_ocr_service.client)}")
        
        # Test 3: Supported file types
        print("\n📋 Test 3: Supported File Types")
        test_files = ["test.pdf", "test.png", "test.jpg", "test.jpeg", "test.tiff", "test.bmp", "test.gif", "test.webp", "test.txt"]
        for filename in test_files:
            should_process = google_vision_ocr_service.should_process_with_ocr(filename)
            status = "✅" if should_process else "❌"
            print(f"   {status} {filename}: {'Supported' if should_process else 'Not supported'}")
        
        print("\n" + "=" * 60)
        print("🎯 Google Vision OCR Service Configuration Summary:")
        print(f"   📊 Service Status: {'✅ Ready' if is_available else '❌ Not Ready'}")
        print(f"   🔧 Max Image Size: {google_vision_ocr_service.max_image_size}")
        print(f"   ⚡ Timeout: {google_vision_ocr_service.timeout} seconds")
        print(f"   🔐 Authentication: {'✅ Configured' if google_vision_ocr_service.credentials_path else '❌ Missing'}")
        print(f"   🤖 Google Vision Client: {'✅ Initialized' if google_vision_ocr_service.client else '❌ Failed'}")
        
        if is_available:
            print("\n🚀 Google Vision OCR is ready to process documents!")
            print("   📄 Supported formats: PDF, PNG, JPG, JPEG, TIFF, BMP, GIF, WEBP")
            print("   ⚡ Features: High-accuracy text detection, multi-language support")
            print("   🔧 Advantages: Superior accuracy, cloud-based processing, regular updates")
        else:
            print("\n⚠️ Google Vision OCR needs configuration:")
            if not google_vision_ocr_service.credentials_path:
                print("   - Set up Google Cloud credentials (GOOGLE_APPLICATION_CREDENTIALS)")
            if not google_vision_ocr_service.client:
                print("   - Ensure Google Cloud Vision library is installed")
                print("   - Verify credentials have Vision API access")
        
        return is_available
        
    except Exception as e:
        logger.error(f"❌ Google Vision OCR test failed: {e}")
        print(f"\n❌ Test failed with error: {e}")
        return False

def main():
    """Run the Google Vision OCR test"""
    print("🔍 Google Vision OCR Service Test")
    print("=================================")
    
    try:
        # Run the async test
        result = asyncio.run(test_google_vision_ocr())
        
        if result:
            print("\n✅ All tests passed! Google Vision OCR is ready.")
            return 0
        else:
            print("\n❌ Some tests failed. Please check the configuration.")
            return 1
            
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test failed with unexpected error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
