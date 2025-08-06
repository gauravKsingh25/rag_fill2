#!/usr/bin/env python3
"""
Test script for enhanced PDF processing capabilities
"""
import asyncio
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.document_processor import document_processor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_pdf_processing():
    """Test the enhanced PDF processing with sample files"""
    print("🔍 Testing Enhanced PDF Processing...")
    
    # Check if we have any PDF files in uploads directory
    uploads_dir = backend_dir / "uploads"
    if not uploads_dir.exists():
        print("❌ No uploads directory found. Please upload some PDF files first.")
        return
    
    pdf_files = list(uploads_dir.glob("*.pdf"))
    if not pdf_files:
        print("❌ No PDF files found in uploads directory.")
        print("📝 Please upload some PDF files through the web interface first.")
        return
    
    print(f"📄 Found {len(pdf_files)} PDF file(s) to test:")
    for pdf_file in pdf_files:
        print(f"   - {pdf_file.name}")
    
    # Test with the first PDF file
    test_file = pdf_files[0]
    print(f"\n🧪 Testing with: {test_file.name}")
    
    try:
        # Read the PDF file
        with open(test_file, 'rb') as f:
            file_content = f.read()
        
        print(f"📊 File size: {len(file_content):,} bytes")
        
        # Test text extraction
        print("\n🔍 Testing text extraction...")
        extracted_text = await document_processor._extract_text(file_content, test_file.name)
        
        print(f"✅ Extracted text length: {len(extracted_text):,} characters")
        print(f"📝 First 500 characters:")
        print("-" * 50)
        print(extracted_text[:500])
        print("-" * 50)
        
        # Test chunking
        print("\n📦 Testing chunking...")
        chunks = document_processor._create_chunks(extracted_text)
        
        print(f"✅ Created {len(chunks)} chunks")
        if chunks:
            print(f"📊 Chunk statistics:")
            chunk_lengths = [len(chunk['content']) for chunk in chunks]
            print(f"   - Average chunk length: {sum(chunk_lengths) / len(chunk_lengths):.0f} chars")
            print(f"   - Min chunk length: {min(chunk_lengths)} chars")
            print(f"   - Max chunk length: {max(chunk_lengths)} chars")
            
            # Show content types
            content_types = {}
            for chunk in chunks:
                ctype = chunk.get('content_type', 'unknown')
                content_types[ctype] = content_types.get(ctype, 0) + 1
            
            print(f"   - Content types: {content_types}")
            
            # Show first chunk sample
            print(f"\n📄 First chunk sample:")
            print("-" * 50)
            print(chunks[0]['content'][:300])
            print("-" * 50)
        
        # Test quality assessment
        print("\n🔍 Testing quality assessment...")
        for i, chunk in enumerate(chunks[:3]):  # Test first 3 chunks
            quality = document_processor._assess_extraction_quality(chunk['content'])
            keywords = document_processor._extract_keywords(chunk['content'])
            print(f"   Chunk {i+1}: Quality={quality:.2f}, Keywords='{keywords[:50]}...'")
        
        print("\n✅ PDF processing test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

async def create_sample_pdf_info():
    """Create a sample text file that simulates PDF content for testing"""
    sample_content = """
DEVICE MASTER FILE

Section 1: Device Information

Generic name: Pulse Oximeter
Model No.: PO-2024-PRO
Document No.: PLL/DMF/001/2024
Manufacturer: ACME Medical Devices Inc.

Date: 15/03/2024
Authorized by: Dr. John Smith

Description:
The Pulse Oximeter PO-2024-PRO is a non-invasive medical device designed for continuous monitoring of oxygen saturation levels in patients. The device uses advanced LED technology to provide accurate readings in various clinical environments.

Technical Specifications:
- Measurement Range: 70-100% SpO2
- Accuracy: ±2% (70-100% range)
- Resolution: 1%
- Operating Temperature: 5°C to 40°C
- Storage Temperature: -40°C to 70°C
- Power Supply: 3V DC (2 x AA batteries)

Regulatory Information:
FDA 510(k): K241234
CE Mark: 0123
ISO 13485: Compliant
ISO 14155: Compliant

[MISSING] Clinical evaluation data
[TO BE FILLED] Risk management file reference
[TBD] Post-market surveillance plan

Quality Management:
The device is manufactured under ISO 13485 quality management system. All manufacturing processes are validated and controlled according to FDA QSR requirements.

Signature: _________________
Date: __/__/____
"""
    
    # Save sample content
    sample_file = backend_dir / "sample_medical_device_dmf.txt"
    with open(sample_file, 'w', encoding='utf-8') as f:
        f.write(sample_content)
    
    print(f"📄 Created sample medical device file: {sample_file}")
    
    # Test with sample content
    try:
        extracted_text = await document_processor._extract_text(
            sample_content.encode('utf-8'), 
            "sample_medical_device_dmf.txt"
        )
        
        chunks = document_processor._create_chunks(extracted_text)
        print(f"✅ Sample processing: {len(chunks)} chunks created")
        
        return True
    except Exception as e:
        print(f"❌ Sample processing failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Enhanced PDF Processing Test Suite")
    print("=" * 50)
    
    # Run the tests
    asyncio.run(test_pdf_processing())
    
    print("\n" + "=" * 50)
    print("🧪 Testing with sample content...")
    asyncio.run(create_sample_pdf_info())
