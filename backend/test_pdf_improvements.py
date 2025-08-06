#!/usr/bin/env python3
"""
Test script to validate PDF processing improvements
"""
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.document_processor import DocumentProcessor
from app.services.gemini_service import GeminiService

async def test_simple_response():
    """Test simple response generation without technical citations"""
    print("🧪 Testing simple response generation...")
    
    gemini = GeminiService()
    
    # Test with sample context
    context = [
        "The device is a pulse oximeter manufactured by ACME Medical Corp. Model number: PX-2000.",
        "Risk Control Measures: Quality Assurance procedures are managed under Quality Assurance and Management departments."
    ]
    
    # Test simple question
    response = await gemini.generate_response(
        prompt="What are the risk control measures?",
        context=context
    )
    
    print("\n📋 Response:")
    print(response)
    print("\n" + "="*50)
    
    # Check if response is clean (no technical citations)
    issues = []
    if "🎯 HIGH CONFIDENCE:" in response:
        issues.append("Contains confidence indicators")
    if "[From Chunk" in response:
        issues.append("Contains chunk references")
    if "| Quality Assurance | Quality Assurance | Management" in response:
        issues.append("Contains raw table data")
    
    if issues:
        print("❌ Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("✅ Response is clean and simple!")
    
    return len(issues) == 0

async def test_text_quality_validation():
    """Test text quality validation"""
    print("\n🧪 Testing text quality validation...")
    
    processor = DocumentProcessor()
    
    # Test good quality text
    good_text = "This is a high-quality document with proper formatting and clear content."
    is_good = processor._is_text_quality_good(good_text)
    print(f"Good text quality: {is_good} ✅" if is_good else f"Good text quality: {is_good} ❌")
    
    # Test poor quality text (garbled)
    bad_text = "â€™â€œâ€\x9dÂ ï¿½â–â€â‚¬ x x x x x x"
    is_bad = processor._is_text_quality_good(bad_text)
    print(f"Bad text quality: {not is_bad} ✅" if not is_bad else f"Bad text quality: {not is_bad} ❌")
    
    return is_good and not is_bad

async def test_chunk_validation():
    """Test chunk validation improvements"""
    print("\n🧪 Testing chunk validation...")
    
    processor = DocumentProcessor()
    
    # Test valid chunk
    valid_chunk = "The pulse oximeter device has model number PX-2000 and is manufactured by ACME Medical Corporation for clinical use in hospitals."
    is_valid = processor._is_valid_chunk(valid_chunk)
    print(f"Valid chunk: {is_valid} ✅" if is_valid else f"Valid chunk: {is_valid} ❌")
    
    # Test invalid chunk (garbled)
    invalid_chunk = "â€™â€œâ€\x9d x x x ï¿½â– yyy"
    is_invalid = processor._is_valid_chunk(invalid_chunk)
    print(f"Invalid chunk rejected: {not is_invalid} ✅" if not is_invalid else f"Invalid chunk rejected: {not is_invalid} ❌")
    
    return is_valid and not is_invalid

async def main():
    """Run all tests"""
    print("🚀 Testing PDF processing and response improvements...\n")
    
    results = []
    
    # Test 1: Simple responses
    results.append(await test_simple_response())
    
    # Test 2: Text quality validation
    results.append(await test_text_quality_validation())
    
    # Test 3: Chunk validation
    results.append(await test_chunk_validation())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"\n📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! The improvements are working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())
