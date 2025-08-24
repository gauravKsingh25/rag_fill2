"""
Google Vision API Enablement Checker
Helps verify if Google Cloud Vision API is enabled and provides troubleshooting
"""

import os
import sys
from pathlib import Path

# Add the backend directory to sys.path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    from google.cloud import vision
    from google.auth import exceptions as auth_exceptions
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

def check_credentials():
    """Check if credentials are properly configured"""
    print("🔐 CREDENTIALS CHECK")
    print("-" * 40)
    
    # Check environment variable
    env_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if env_creds:
        print(f"✅ Environment variable set: {env_creds}")
    else:
        print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set in environment")
    
    # Check default file
    default_file = "rag-fill-py-d1a683dcf003.json"
    if os.path.exists(default_file):
        print(f"✅ Credentials file found: {default_file}")
        
        # Read project info
        try:
            import json
            with open(default_file, 'r') as f:
                creds_data = json.load(f)
                project_id = creds_data.get('project_id')
                client_email = creds_data.get('client_email')
                print(f"📋 Project ID: {project_id}")
                print(f"📧 Service Account: {client_email}")
                return project_id
        except Exception as e:
            print(f"❌ Error reading credentials: {e}")
    else:
        print(f"❌ Credentials file not found: {default_file}")
    
    return None

def test_vision_api(project_id):
    """Test if Vision API is accessible"""
    print(f"\n🔍 TESTING GOOGLE VISION API")
    print("-" * 40)
    
    if not GOOGLE_VISION_AVAILABLE:
        print("❌ Google Cloud Vision library not installed")
        return False
    
    try:
        # Set credentials path
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rag-fill-py-d1a683dcf003.json"
        
        # Try to create client
        client = vision.ImageAnnotatorClient()
        print("✅ Vision client created successfully")
        
        # Try a simple API call (this will fail if API is not enabled)
        # We'll create a minimal test image
        image = vision.Image()
        # Set minimal content to test API availability
        image.content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00IEND\xaeB`\x82'
        
        # Test the API
        response = client.text_detection(image=image)
        
        if response.error.message:
            print(f"❌ API Error: {response.error.message}")
            
            if "SERVICE_DISABLED" in response.error.message:
                print(f"\n🔧 SOLUTION: Enable Google Cloud Vision API")
                print(f"   1. Go to: https://console.cloud.google.com/apis/library/vision.googleapis.com?project={project_id}")
                print(f"   2. Click 'ENABLE'")
                print(f"   3. Wait 2-3 minutes for propagation")
                print(f"   4. Re-run this test")
                
            return False
        else:
            print("✅ Google Vision API is working!")
            return True
            
    except Exception as e:
        print(f"❌ Vision API test failed: {e}")
        
        if "SERVICE_DISABLED" in str(e):
            print(f"\n🔧 SOLUTION: Enable Google Cloud Vision API")
            print(f"   📋 Your project: {project_id}")
            print(f"   🔗 Enable here: https://console.cloud.google.com/apis/library/vision.googleapis.com?project={project_id}")
            print(f"   ⏱️  Wait 2-3 minutes after enabling")
            
        elif "403" in str(e):
            print(f"\n🔧 POSSIBLE SOLUTIONS:")
            print(f"   1. Enable Vision API in Google Cloud Console")
            print(f"   2. Check service account permissions")
            print(f"   3. Verify billing is enabled for project")
            
        return False

def main():
    print("🧪 GOOGLE VISION API DIAGNOSTIC TOOL")
    print("=" * 50)
    
    # Step 1: Check credentials
    project_id = check_credentials()
    
    if not project_id:
        print("\n❌ Cannot proceed without valid credentials")
        return
    
    # Step 2: Test API
    api_works = test_vision_api(project_id)
    
    # Step 3: Provide summary
    print(f"\n📊 DIAGNOSTIC SUMMARY")
    print("-" * 40)
    
    if api_works:
        print("✅ Google Vision API is ready to use!")
        print("   Your OCR service should work now.")
    else:
        print("❌ Google Vision API is not accessible")
        print("\n🔧 NEXT STEPS:")
        print(f"   1. Enable Vision API: https://console.cloud.google.com/apis/library/vision.googleapis.com?project={project_id}")
        print("   2. Wait 2-3 minutes after enabling")
        print("   3. Re-run this diagnostic")
        print("   4. If still fails, check billing is enabled")
    
    print(f"\n📋 KEY INFORMATION:")
    print(f"   🏷️  Project ID: {project_id}")
    print(f"   📁 Credentials: rag-fill-py-d1a683dcf003.json")
    print(f"   🔗 Console: https://console.cloud.google.com/home/dashboard?project={project_id}")

if __name__ == "__main__":
    main()
