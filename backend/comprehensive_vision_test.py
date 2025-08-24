"""
Improved Google Vision API Test
More comprehensive test with better error handling
"""

import os
import sys
import json
from pathlib import Path
import base64

# Add the backend directory to sys.path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    from google.cloud import vision
    from google.auth import exceptions as auth_exceptions
    import google.auth
    GOOGLE_VISION_AVAILABLE = True
except ImportError as e:
    GOOGLE_VISION_AVAILABLE = False
    print(f"❌ Google Vision import error: {e}")

def test_service_account_permissions():
    """Test if service account has proper permissions"""
    print("🔐 SERVICE ACCOUNT PERMISSIONS TEST")
    print("-" * 50)
    
    try:
        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rag-fill-py-d1a683dcf003.json"
        
        # Test authentication
        credentials, project = google.auth.default()
        print(f"✅ Authentication successful")
        print(f"📋 Project from auth: {project}")
        print(f"🔑 Credentials type: {type(credentials)}")
        
        return True, project
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False, None

def test_vision_api_simple():
    """Test Vision API with a simple valid request"""
    print("\n🔍 GOOGLE VISION API TEST")
    print("-" * 50)
    
    if not GOOGLE_VISION_AVAILABLE:
        print("❌ Google Cloud Vision library not available")
        return False
    
    try:
        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rag-fill-py-d1a683dcf003.json"
        
        # Create client
        client = vision.ImageAnnotatorClient()
        print("✅ Vision client created successfully")
        
        # Create a simple 1x1 white PNG image for testing
        # This is a valid minimal PNG
        png_data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77QgAAAABJRU5ErkJggg=='
        )
        
        # Create image object
        image = vision.Image(content=png_data)
        
        # Test text detection
        print("🧪 Testing text detection...")
        response = client.text_detection(image=image)
        
        # Check for errors
        if response.error.message:
            print(f"❌ API Error: {response.error.message}")
            
            if "PERMISSION_DENIED" in response.error.message:
                print("\n🔧 SOLUTION: Service account needs Cloud Vision API permissions")
                print("   1. Go to Google Cloud Console")
                print("   2. Navigate to IAM & Admin > IAM")
                print("   3. Find your service account: rag-fill@rag-fill-py.iam.gserviceaccount.com")
                print("   4. Add role: 'Cloud Vision API Service Agent' or 'Editor'")
                
            elif "SERVICE_DISABLED" in response.error.message:
                print("\n🔧 SOLUTION: Wait a few more minutes for API enablement to propagate")
                
            return False
        else:
            print("✅ Text detection API call successful!")
            print(f"📝 Response: {len(response.text_annotations)} text annotations found")
            return True
            
    except Exception as e:
        error_str = str(e)
        print(f"❌ Vision API test failed: {error_str}")
        
        if "403" in error_str and "PERMISSION_DENIED" in error_str:
            print(f"\n🔧 SOLUTION: Service Account Permissions Issue")
            print(f"   📧 Service Account: rag-fill@rag-fill-py.iam.gserviceaccount.com")
            print(f"   🔗 Go to: https://console.cloud.google.com/iam-admin/iam?project=rag-fill-py")
            print(f"   ➕ Add Role: 'Cloud Vision API Service Agent'")
            
        elif "403" in error_str and "SERVICE_DISABLED" in error_str:
            print(f"\n🔧 SOLUTION: API Still Propagating")
            print(f"   ⏱️  Wait 5-10 minutes after enabling")
            print(f"   🔄 API enablement can take time to propagate")
            
        elif "400" in error_str or "invalid argument" in error_str.lower():
            print(f"\n🔧 SOLUTION: Check API Request Format")
            print(f"   📝 This might be a temporary issue")
            print(f"   🔄 Try again in a few minutes")
            
        return False

def check_billing():
    """Check if billing is enabled (indirectly)"""
    print("\n💳 BILLING CHECK")
    print("-" * 50)
    
    print("⚠️  Important: Google Cloud Vision API requires billing to be enabled")
    print("🔗 Check billing: https://console.cloud.google.com/billing?project=rag-fill-py")
    print("💡 Even if you have free credits, billing account must be linked")

def main():
    print("🧪 COMPREHENSIVE GOOGLE VISION API TEST")
    print("=" * 60)
    
    # Step 1: Test authentication
    auth_success, project = test_service_account_permissions()
    
    if not auth_success:
        print("\n❌ Cannot proceed - authentication failed")
        return
    
    # Step 2: Test Vision API
    api_success = test_vision_api_simple()
    
    # Step 3: Billing reminder
    check_billing()
    
    # Step 4: Final summary
    print(f"\n📊 COMPREHENSIVE TEST SUMMARY")
    print("=" * 60)
    
    if api_success:
        print("✅ GOOGLE VISION API IS WORKING!")
        print("   🎉 Your OCR service should work perfectly now")
        print("   🚀 Ready to process your 44-page PDF")
    else:
        print("❌ GOOGLE VISION API IS NOT WORKING")
        print("\n🔧 MOST LIKELY CAUSES:")
        print("   1. ⏱️  API enablement still propagating (wait 5-10 min)")
        print("   2. 🔑 Service account lacks Vision API permissions")
        print("   3. 💳 Billing not enabled on project")
        
        print(f"\n🛠️  TROUBLESHOOTING STEPS:")
        print(f"   1. Check IAM: https://console.cloud.google.com/iam-admin/iam?project=rag-fill-py")
        print(f"   2. Add role 'Cloud Vision API Service Agent' to rag-fill@rag-fill-py.iam.gserviceaccount.com")
        print(f"   3. Check billing: https://console.cloud.google.com/billing?project=rag-fill-py")
        print(f"   4. Wait 5-10 minutes and re-test")

if __name__ == "__main__":
    main()
