#!/usr/bin/env python3
"""
Test script to verify simple, readable responses without technical citations
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.gemini_service import gemini_service

async def test_simple_responses():
    """Test that responses are clean and readable"""
    print("🧪 Testing simple response generation...")
    
    # Test with sample context that might previously cause technical responses
    context = [
        "Risk Control Measures document shows that Quality Assurance procedures are managed under Quality Assurance and Management departments. The document outlines safety protocols.",
        "Device specifications indicate model number PX-2000 manufactured by ACME Medical Corp. The device meets ISO 13485 standards.",
        "Clinical evaluation shows the pulse oximeter provides accurate readings. FDA approval was received in March 2024."
    ]
    
    test_questions = [
        "What are the risk control measures?",
        "What is the model number?", 
        "Who is the manufacturer?",
        "What about FDA approval?",
        "Tell me about quality assurance"
    ]
    
    all_passed = True
    
    for question in test_questions:
        print(f"\n❓ Question: {question}")
        
        response = await gemini_service.generate_response(
            prompt=question,
            context=context,
            temperature=0.1
        )
        
        print(f"💬 Response: {response}")
        
        # Check for issues that indicate technical/verbose responses
        issues = []
        
        if "🎯 HIGH CONFIDENCE:" in response:
            issues.append("Contains confidence indicators")
        
        if "[From Chunk" in response:
            issues.append("Contains chunk references")
        
        if "| Quality Assurance | Quality Assurance | Management" in response:
            issues.append("Contains raw table data")
        
        if "[Document:" in response:
            issues.append("Contains document metadata")
        
        if "Confidence:" in response:
            issues.append("Contains confidence scores")
        
        # Check for reasonable response length (not too verbose)
        if len(response) > 500:
            issues.append("Response too verbose")
        
        if issues:
            print(f"❌ Issues found: {', '.join(issues)}")
            all_passed = False
        else:
            print("✅ Response is clean and readable!")
        
        print("-" * 60)
    
    return all_passed

async def test_pdf_text_cleaning():
    """Test PDF text cleaning functionality"""
    print("\n🧪 Testing PDF text cleaning...")
    
    from app.services.document_processor import DocumentProcessor
    processor = DocumentProcessor()
    
    # Test text with common PDF encoding issues
    garbled_text = """
    â€™s implementation of quality assurance procedures â€œensuresâ€\x9d that 
    all medical devices meet regulatory standards. The â€"systemic approachâ€"
    includes Â comprehensive documentation and Ã¡dherence to ISO standards.
    
    ï¿½ Invalid character sequences and â–various encoding artifacts should
    be cleaned up properly. The system must handle â€¦multiple types of
    corruption including Â®trademark symbols and â‚¬currency indicators.
    """
    
    print("Original text sample:")
    print(garbled_text[:200] + "...")
    
    # Clean the text
    cleaned_text = processor._clean_extracted_text(garbled_text)
    
    print("\nCleaned text sample:")
    print(cleaned_text[:200] + "...")
    
    # Check if text quality improved
    is_original_good = processor._is_text_quality_good(garbled_text)
    is_cleaned_good = processor._is_text_quality_good(cleaned_text)
    
    print(f"\nOriginal text quality: {'Good' if is_original_good else 'Poor'}")
    print(f"Cleaned text quality: {'Good' if is_cleaned_good else 'Poor'}")
    
    # Count artifacts before and after
    artifacts = ['â€', 'Â', 'ï¿½', 'â–', 'â€œ', 'â€\x9d']
    original_artifacts = sum(garbled_text.count(artifact) for artifact in artifacts)
    cleaned_artifacts = sum(cleaned_text.count(artifact) for artifact in artifacts)
    
    print(f"Artifacts removed: {original_artifacts} → {cleaned_artifacts}")
    
    return cleaned_artifacts < original_artifacts and is_cleaned_good

async def main():
    """Run all tests"""
    print("🚀 Testing response quality and PDF processing improvements...\n")
    
    results = []
    
    # Test 1: Simple responses
    results.append(await test_simple_responses())
    
    # Test 2: PDF text cleaning
    results.append(await test_pdf_text_cleaning())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The fixes are working correctly.")
        print("✅ Responses should now be clean and readable")
        print("✅ PDF text processing should handle encoding issues better")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
