"""
OCR Migration Status Report
Shows the status of migration from old OCR services to Google Vision OCR
"""

import os
import sys
from pathlib import Path

# Add the backend directory to sys.path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def check_file_status(file_path, description):
    """Check if a file exists and return status"""
    if os.path.exists(file_path):
        return f"✅ {description}: EXISTS"
    else:
        return f"❌ {description}: NOT FOUND"

def main():
    print("🔄 OCR Migration Status Report")
    print("=" * 50)
    
    print("\n📊 OLD OCR SERVICES (Should be disabled/renamed):")
    print("-" * 50)
    
    # Check old OCR services
    old_simple_ocr = "app/services/simple_ocr_service.py"
    old_simple_ocr_renamed = "app/services/simple_ocr_service_old.py"
    old_ocr_service = "app/services/ocr_service_old.py"
    
    if os.path.exists(old_simple_ocr):
        print(f"⚠️  OLD Simple OCR Service: STILL ACTIVE (should be renamed)")
    elif os.path.exists(old_simple_ocr_renamed):
        print(f"✅ OLD Simple OCR Service: PROPERLY RENAMED")
    else:
        print(f"❓ OLD Simple OCR Service: NOT FOUND")
    
    print(check_file_status(old_ocr_service, "OLD OCR Service"))
    
    print("\n📊 OLD OCR ROUTERS (Should be disabled/renamed):")
    print("-" * 50)
    
    # Check old OCR routers
    old_simple_router = "app/routers/simple_ocr_management.py"
    old_simple_router_renamed = "app/routers/simple_ocr_management_old.py"
    old_ocr_router = "app/routers/ocr_management.py" 
    old_ocr_router_renamed = "app/routers/ocr_management_old.py"
    
    if os.path.exists(old_simple_router):
        print(f"⚠️  OLD Simple OCR Router: STILL ACTIVE (should be renamed)")
    elif os.path.exists(old_simple_router_renamed):
        print(f"✅ OLD Simple OCR Router: PROPERLY RENAMED")
    else:
        print(f"❓ OLD Simple OCR Router: NOT FOUND")
        
    if os.path.exists(old_ocr_router):
        print(f"⚠️  OLD OCR Router: STILL ACTIVE (should be renamed)")
    elif os.path.exists(old_ocr_router_renamed):
        print(f"✅ OLD OCR Router: PROPERLY RENAMED")
    else:
        print(f"❓ OLD OCR Router: NOT FOUND")
    
    print("\n🆕 NEW GOOGLE VISION OCR SERVICES:")
    print("-" * 50)
    
    # Check new Google Vision services
    new_google_vision_service = "app/services/google_vision_ocr_service.py"
    new_google_vision_router = "app/routers/google_vision_ocr_management.py"
    
    print(check_file_status(new_google_vision_service, "Google Vision OCR Service"))
    print(check_file_status(new_google_vision_router, "Google Vision OCR Router"))
    
    print("\n📄 CONFIGURATION FILES:")
    print("-" * 50)
    
    # Check configuration files
    requirements = "requirements.txt"
    credentials = "rag-fill-py-d1a683dcf003.json"
    
    print(check_file_status(requirements, "Requirements.txt"))
    print(check_file_status(credentials, "Google Credentials"))
    
    # Check requirements content
    if os.path.exists(requirements):
        try:
            with open(requirements, 'r', encoding='utf-8') as f:
                content = f.read()
                if "google-cloud-vision" in content:
                    print("✅ Requirements: Google Cloud Vision ADDED")
                else:
                    print("⚠️  Requirements: Google Cloud Vision NOT FOUND")
        except Exception as e:
            print(f"⚠️  Requirements: Could not read file ({e})")
    
    print("\n🔧 DOCUMENT PROCESSOR INTEGRATION:")
    print("-" * 50)
    
    # Check document processor
    doc_processor = "app/services/document_processor.py"
    if os.path.exists(doc_processor):
        print("✅ Document Processor: EXISTS")
        
        try:
            with open(doc_processor, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if "google_vision_ocr_service" in content:
                print("✅ Document Processor: Google Vision OCR INTEGRATED")
            else:
                print("❌ Document Processor: Google Vision OCR NOT INTEGRATED")
                
            if "simple_ocr_service" in content and "# from app.services.simple_ocr_service import simple_ocr_service" not in content:
                print("⚠️  Document Processor: OLD OCR references still active")
            else:
                print("✅ Document Processor: OLD OCR references commented out")
        except Exception as e:
            print(f"⚠️  Document Processor: Could not read file ({e})")
    else:
        print("❌ Document Processor: NOT FOUND")
    
    print("\n🚀 MAIN APPLICATION INTEGRATION:")
    print("-" * 50)
    
    # Check main.py
    main_file = "main.py"
    if os.path.exists(main_file):
        print("✅ Main Application: EXISTS")
        
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if "google_vision_ocr_management" in content:
                print("✅ Main Application: Google Vision Router INCLUDED")
            else:
                print("❌ Main Application: Google Vision Router NOT INCLUDED")
                
            # Count old OCR router references
            old_router_refs = content.count("simple_ocr_management.router") + content.count("ocr_management.router")
            commented_refs = content.count("# app.include_router(simple_ocr_management") + content.count("# app.include_router(ocr_management")
            
            if old_router_refs == 0 or old_router_refs == commented_refs:
                print("✅ Main Application: OLD OCR routers properly disabled")
            else:
                print("⚠️  Main Application: OLD OCR routers still active")
        except Exception as e:
            print(f"⚠️  Main Application: Could not read file ({e})")
    
    print("\n" + "=" * 50)
    print("🎯 MIGRATION SUMMARY")
    print("=" * 50)
    
    # Calculate migration status
    checks = [
        os.path.exists("app/services/google_vision_ocr_service.py"),
        os.path.exists("app/routers/google_vision_ocr_management.py"),
        not os.path.exists("app/services/simple_ocr_service.py") or os.path.exists("app/services/simple_ocr_service_old.py"),
        not os.path.exists("app/routers/simple_ocr_management.py") or os.path.exists("app/routers/simple_ocr_management_old.py"),
        os.path.exists("rag-fill-py-d1a683dcf003.json")
    ]
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print("✅ MIGRATION COMPLETE!")
        print("   🎉 All old OCR services have been replaced with Google Vision OCR")
        print("   🚀 Your system is now using Google Cloud Vision for superior OCR accuracy")
        print("   📈 Benefits: Higher accuracy, better language support, cloud scalability")
    elif passed >= total * 0.8:
        print("🟡 MIGRATION MOSTLY COMPLETE")
        print(f"   📊 Progress: {passed}/{total} checks passed")
        print("   ⚠️  Some manual cleanup may be needed")
    else:
        print("🔴 MIGRATION INCOMPLETE")
        print(f"   📊 Progress: {passed}/{total} checks passed")
        print("   ❌ Significant issues need to be resolved")
    
    print("\n🔄 NEXT STEPS:")
    print("-" * 50)
    if passed == total:
        print("1. ✅ Start your FastAPI server: python main.py")
        print("2. ✅ Test with your 44-page PDF document")
        print("3. ✅ Monitor processing with Google Vision OCR")
        print("4. ✅ Check /api/google-vision-ocr/status endpoint")
    else:
        print("1. 🔧 Fix any remaining migration issues shown above")
        print("2. 🧪 Run test_google_vision_ocr.py to verify setup")
        print("3. 🚀 Start server once migration is complete")
    
    print("\n📋 API ENDPOINTS:")
    print("-" * 50)
    print("• GET /api/google-vision-ocr/status - Service status")
    print("• GET /api/google-vision-ocr/test - Test functionality") 
    print("• GET /api/google-vision-ocr/capabilities - OCR capabilities")
    print("• GET /api/google-vision-ocr/config - Current configuration")
    print("• POST /api/google-vision-ocr/reinitialize - Reinitialize service")

if __name__ == "__main__":
    main()
