#!/usr/bin/env python3
"""
Test script to verify template processing optimizations with parallel processing
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.gemini_service import gemini_service

async def test_batch_operations():
    """Test the new batch operations"""
    
    # Reset API counter for testing
    gemini_service.reset_api_counter()
    
    print("🧪 Testing Template Processing Optimizations with Parallel Processing")
    print("=" * 60)
    
    # Test 1: Batch question generation
    print("\n1. Testing Batch Question Generation...")
    
    sample_fields = [
        {
            'field_name': 'Document Number',
            'context': 'Document Number: _____________'
        },
        {
            'field_name': 'Brand Name', 
            'context': 'Brand Name: _____________'
        },
        {
            'field_name': 'Model Number',
            'context': 'Model Number: _____________'
        },
        {
            'field_name': 'Manufacturing Site',
            'context': 'Manufacturing Site: _____________'
        },
        {
            'field_name': 'Device Classification',
            'context': 'Classification of Device: _____________'
        }
    ]
    
    try:
        questions_result = await gemini_service.generate_questions_batch(sample_fields)
        print(f"✅ Generated questions for {len(questions_result)} fields")
        for field, questions in questions_result.items():
            print(f"   {field}: {len(questions)} questions")
    except Exception as e:
        print(f"❌ Batch question generation failed: {e}")
    
    # Test 2: Enhanced Parallel Processing (NEW)
    print("\n2. Testing Enhanced Parallel Processing...")
    
    try:
        # Configure for testing
        gemini_service.configure_parallel_processing(
            max_concurrent_api_calls=2,
            min_delay_between_calls=0.5,  # Faster for testing
            max_batch_size=8
        )
        
        # Test the new parallel processing method
        parallel_results = await gemini_service.process_template_fields_parallel(
            field_infos=sample_fields,
            device_id="test_device_parallel",
            max_batch_size=3,  # Small batches for testing
            max_concurrent_batches=2
        )
        
        print(f"✅ Parallel processing completed for {len(parallel_results)} fields")
        for field_name, result in parallel_results.items():
            questions = result.get('questions', [])
            value = result.get('value', 'NOT_FOUND')
            print(f"   {field_name}: {len(questions)} questions, value: {value}")
        
    except Exception as e:
        print(f"❌ Enhanced parallel processing failed: {e}")
    
    # Test 3: Batch field filling (Original)
    print("\n3. Testing Original Batch Field Filling...")
    
    sample_fields_data = [
        {
            'field_name': 'Document Number',
            'field_context': 'Document Number: _____________',
            'questions': ['What is the document number?'],
            'context_docs': ['DMF Document Number: PLL/DMF/001', 'Reference: Medical Device File']
        },
        {
            'field_name': 'Brand Name',
            'field_context': 'Brand Name: _____________', 
            'questions': ['What is the brand name?'],
            'context_docs': ['Manufacturer: Dr. Odin Healthcare', 'Brand: Dr. Odin Pulse Oximeter']
        }
    ]
    
    try:
        fill_result = await gemini_service.fill_template_fields_batch(sample_fields_data, "test_device")
        print(f"✅ Filled {len(fill_result)} fields")
        for field, value in fill_result.items():
            print(f"   {field}: {value}")
    except Exception as e:
        print(f"❌ Batch field filling failed: {e}")
    
    # Test 4: API usage stats
    print("\n4. API Usage Statistics...")
    stats = gemini_service.get_api_usage_stats()
    print(f"✅ Total API calls made: {stats['total_api_calls']}")
    print(f"✅ Cache entries: {stats['cache_size']}")
    print(f"✅ Service available: {stats['service_available']}")
    
    # Test 5: Performance comparison
    print("\n5. Performance Analysis...")
    total_fields = len(sample_fields)
    print("\n" + "=" * 60)
    print("🎯 Optimization Benefits with Parallel Processing:")
    print(f"   • Total fields processed: {total_fields}")
    print(f"   • Old approach would need: ~{total_fields * 2} API calls (2 per field)")
    print(f"   • Enhanced parallel approach used: {stats['total_api_calls']} API calls")
    
    if stats['total_api_calls'] > 0:
        reduction = ((total_fields * 2) - stats['total_api_calls']) / (total_fields * 2) * 100
        print(f"   • API call reduction: {reduction:.1f}%")
        
        # Calculate fields per API call efficiency
        efficiency = total_fields / stats['total_api_calls'] if stats['total_api_calls'] > 0 else 0
        print(f"   • Fields processed per API call: {efficiency:.1f}")
    
    print("\n🚀 Parallel Processing Benefits:")
    print("   • Intelligent throttling prevents rate limit clustering")
    print("   • Concurrent batch processing with semaphore control")
    print("   • Smart delay management between API calls")
    print("   • Fallback protection for failed operations")
    print("   • Context gathering optimization with parallel search")

async def test_rate_limit_handling():
    """Test rate limit handling specifically"""
    print("\n" + "=" * 60)
    print("🛡️ Testing Rate Limit Protection...")
    
    # Reset counter
    gemini_service.reset_api_counter()
    
    # Configure very conservative settings
    gemini_service.configure_parallel_processing(
        max_concurrent_api_calls=1,  # Only 1 concurrent call
        min_delay_between_calls=2.0,  # 2 second delays
        max_batch_size=15  # Larger batches to reduce calls
    )
    
    # Create a larger set of fields to test rate limiting
    large_field_set = []
    for i in range(12):  # 12 fields to test batching
        large_field_set.append({
            'field_name': f'Test Field {i+1}',
            'context': f'Test Field {i+1}: _____________'
        })
    
    print(f"📝 Testing with {len(large_field_set)} fields...")
    
    start_time = asyncio.get_event_loop().time()
    
    try:
        # This should process efficiently with minimal API calls
        results = await gemini_service.process_template_fields_parallel(
            field_infos=large_field_set,
            device_id="rate_limit_test",
            max_batch_size=15,  # Large batch size
            max_concurrent_batches=1  # Single batch to minimize calls
        )
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        final_stats = gemini_service.get_api_usage_stats()
        
        print(f"✅ Rate limit test completed successfully!")
        print(f"   • Processing time: {processing_time:.2f} seconds")
        print(f"   • Total API calls: {final_stats['total_api_calls']}")
        print(f"   • Fields processed: {len(results)}")
        print(f"   • API efficiency: {len(results)/final_stats['total_api_calls']:.1f} fields per call")
        
    except Exception as e:
        print(f"❌ Rate limit test failed: {e}")

if __name__ == "__main__":
    async def run_all_tests():
        await test_batch_operations()
        await test_rate_limit_handling()
    
    asyncio.run(run_all_tests())
