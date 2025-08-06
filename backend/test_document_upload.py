#!/usr/bin/env python3
"""
Test document upload functionality
"""
import asyncio
import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.document_processor import document_processor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_document_upload():
    """Test document upload with sample content"""
    print("🧪 Testing document upload functionality...")
    
    # Create sample PDF-like content
    sample_content = """
DEVICE MASTER FILE

Section 1: Device Information

Generic Name: Advanced Pulse Oximeter
Model Number: APO-2024-Pro
Document Number: DMF-APO-2024-001
Manufacturer: MedTech Solutions Inc.
Date: 15/03/2024

Section 2: Technical Specifications

Measurement Range:
- SpO2: 70% to 100%
- Pulse Rate: 30 to 250 bpm
- Perfusion Index: 0.02% to 20%

Accuracy:
- SpO2 Accuracy: ±2% (70% to 100%)
- Pulse Rate Accuracy: ±3 bpm or ±2%

Operating Environment:
- Temperature: 5°C to 40°C
- Humidity: 15% to 95% RH
- Atmospheric Pressure: 70 kPa to 106 kPa

Section 3: Regulatory Information

FDA 510(k): K123456789
CE Mark: CE-APO-2024
ISO Standards: ISO 13485:2016, ISO 14971:2019

Section 4: Intended Use

The Advanced Pulse Oximeter is intended for non-invasive monitoring
of functional oxygen saturation (SpO2) and pulse rate in adult and
pediatric patients in hospitals, clinics, and home care settings.

Missing Fields:
[MISSING] Clinical evaluation data
[TO BE FILLED] Risk management file reference
[TBD] Post-market surveillance plan
    """.encode('utf-8')
    
    try:
        # Test document processing
        result = await document_processor.process_uploaded_file(
            file_content=sample_content,
            filename="test_device_master_file.txt",
            device_id="test_device_123"
        )
        
        print("✅ Document upload test results:")
        print(f"   - Document ID: {result['document_id']}")
        print(f"   - Filename: {result['filename']}")
        print(f"   - Device ID: {result['device_id']}")
        print(f"   - Chunks Created: {result['chunks_created']}")
        print(f"   - Status: {result['status']}")
        
        if result['chunks_created'] > 0:
            print("🎉 Document upload test PASSED!")
            return True
        else:
            print("❌ Document upload test FAILED - No chunks created")
            return False
            
    except Exception as e:
        print(f"❌ Document upload test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Document Upload Test")
    print("=" * 50)
    
    success = asyncio.run(test_document_upload())
    
    if success:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Tests failed!")
