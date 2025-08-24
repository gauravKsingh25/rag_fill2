"""
Google Vision Billing and API Status Checker
Specifically tests for billing and API enablement issues
"""

import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

try:
    from google.cloud import vision
    from google.api_core import exceptions as api_exceptions
    import google.auth
    GOOGLE_VISION_AVAILABLE = True
except ImportError as e:
    GOOGLE_VISION_AVAILABLE = False
    print(f"❌ Import error: {e}")

def test_billing_and_api():
    """Test specifically for billing and API issues"""
    print("🔍 GOOGLE VISION BILLING & API TEST")
    print("=" * 50)
    
    if not GOOGLE_VISION_AVAILABLE:
        print("❌ Google Vision library not available")
        return False
    
    try:
        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "rag-fill-py-d1a683dcf003.json"
        
        # Create client
        client = vision.ImageAnnotatorClient()
        print("✅ Vision client created")
        
        # Try the simplest possible API call
        # Using a basic feature that should work if API is enabled
        try:
            # Create a minimal valid image request
            # This is a 1x1 white pixel PNG encoded in base64
            import base64
            minimal_png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==')
            
            image = vision.Image(content=minimal_png)
            
            # Make the API call
            response = client.text_detection(image=image)
            
            if response.error.message:
                error = response.error.message
                print(f"❌ API Error: {error}")
                
                # Analyze specific error types
                if "BILLING_DISABLED" in error or "billing" in error.lower():
                    print("\n💳 BILLING ISSUE DETECTED!")
                    print("🔧 SOLUTION:")
                    print("   1. Go to: https://console.cloud.google.com/billing?project=rag-fill-py")
                    print("   2. Link a billing account to this project")
                    print("   3. Even free tier requires billing account setup")
                    return False
                    
                elif "SERVICE_DISABLED" in error:
                    print("\n🚫 API NOT ENABLED!")
                    print("🔧 SOLUTION:")
                    print("   1. Go to: https://console.cloud.google.com/apis/library/vision.googleapis.com?project=rag-fill-py")
                    print("   2. Click ENABLE (if not already enabled)")
                    print("   3. Wait 5-10 minutes")
                    return False
                    
                elif "PERMISSION_DENIED" in error:
                    print("\n🔑 PERMISSION ISSUE!")
                    print("🔧 SOLUTION:")
                    print("   1. Go to: https://console.cloud.google.com/iam-admin/iam?project=rag-fill-py")
                    print("   2. Edit service account: rag-fill@rag-fill-py.iam.gserviceaccount.com")
                    print("   3. Add role: 'Cloud Vision API Service Agent'")
                    return False
                    
                else:
                    print(f"\n❓ UNKNOWN ERROR: {error}")
                    return False
            else:
                print("✅ API call successful!")
                print(f"📝 Detected {len(response.text_annotations)} text elements")
                return True
                
        except api_exceptions.PermissionDenied as e:
            print(f"❌ Permission Denied: {e}")
            print("\n🔑 PERMISSION ISSUE!")
            print("🔧 Add 'Cloud Vision API Service Agent' role to service account")
            return False
            
        except api_exceptions.FailedPrecondition as e:
            print(f"❌ Failed Precondition: {e}")
            print("\n💳 LIKELY BILLING ISSUE!")
            print("🔧 Enable billing for this project")
            return False
            
        except Exception as e:
            error_str = str(e)
            print(f"❌ API Test Error: {error_str}")
            
            if "billing" in error_str.lower():
                print("\n💳 BILLING ISSUE DETECTED!")
                print("🔧 Enable billing account")
            elif "400" in error_str and "invalid" in error_str.lower():
                print("\n⚠️ POSSIBLE CAUSES:")
                print("   1. 💳 Billing not enabled")
                print("   2. ⏱️ API still propagating (wait 5-10 min)")
                print("   3. 🔑 Insufficient permissions")
                
            return False
            
    except Exception as e:
        print(f"❌ Client creation failed: {e}")
        return False

def main():
    print("🧪 GOOGLE VISION BILLING & API STATUS CHECK")
    print("=" * 60)
    
    # Test the API
    success = test_billing_and_api()
    
    print(f"\n📊 TEST RESULT")
    print("=" * 60)
    
    if success:
        print("✅ GOOGLE VISION API IS WORKING!")
        print("🎉 Ready to process documents with OCR")
        print("🚀 Your 44-page PDF should work now!")
        
    else:
        print("❌ GOOGLE VISION API IS NOT WORKING")
        print("\n🔧 MOST COMMON FIXES:")
        print("1. 💳 BILLING: Link billing account (even for free tier)")
        print("   https://console.cloud.google.com/billing?project=rag-fill-py")
        print("")
        print("2. ⏱️ WAIT: API enablement can take 5-10 minutes")
        print("")
        print("3. 🔑 PERMISSIONS: Add Vision API role to service account")
        print("   https://console.cloud.google.com/iam-admin/iam?project=rag-fill-py")
        
    print(f"\n📋 QUICK LINKS:")
    print(f"🏠 Project Dashboard: https://console.cloud.google.com/home/dashboard?project=rag-fill-py")
    print(f"💳 Billing: https://console.cloud.google.com/billing?project=rag-fill-py")
    print(f"🔑 IAM: https://console.cloud.google.com/iam-admin/iam?project=rag-fill-py")
    print(f"📡 APIs: https://console.cloud.google.com/apis/dashboard?project=rag-fill-py")

if __name__ == "__main__":
    main()
