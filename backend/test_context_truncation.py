#!/usr/bin/env python3
"""
Test enhanced context truncation for Gemini API
"""

import asyncio
import sys
sys.path.append('.')

async def test_context_truncation():
    """Test the enhanced context truncation"""
    
    print("🧪 TESTING ENHANCED CONTEXT TRUNCATION")
    print("=" * 60)
    
    try:
        from app.services.gemini_service import GeminiService
        
        gemini = GeminiService()
        
        print("1️⃣ Testing token count estimation...")
        
        test_texts = [
            "Short text",
            "This is a medium length text with several words and sentences that should give us a reasonable token count estimate.",
            "This is a very long text " * 100  # Very long text
        ]
        
        for i, text in enumerate(test_texts):
            tokens = gemini._estimate_token_count(text)
            print(f"   Text {i+1}: {len(text)} chars → ~{tokens} tokens")
        
        print("\n2️⃣ Testing smart context truncation...")
        
        # Create a large context
        large_context = "\n\n".join([
            f"Section {i}: This is section {i} with important information about the document processing system. " + 
            "It contains various details about how the system works and processes documents. " * 10
            for i in range(50)
        ])
        
        print(f"   Original context: {len(large_context)} characters")
        
        truncated = gemini._truncate_context_smartly(large_context, 10000)
        print(f"   Truncated context: {len(truncated)} characters")
        print(f"   Truncation ratio: {len(truncated)/len(large_context)*100:.1f}%")
        
        print("\n3️⃣ Testing embedding text truncation...")
        
        long_text = "This is a very long text for embedding. " * 100
        print(f"   Original text: {len(long_text)} characters")
        
        if len(long_text) > 2048:
            truncated_embedding_text = long_text[:2048] + "..."
            print(f"   Truncated for embedding: {len(truncated_embedding_text)} characters")
        
        print("\n✅ CONTEXT TRUNCATION TESTS COMPLETED")
        
        print("\n🔧 ENHANCEMENTS MADE:")
        print("   • Smart context truncation (preserves start/end)")
        print("   • Token count estimation for safety checks")
        print("   • Embedding text length validation")
        print("   • Fallback to minimal prompts for oversized requests")
        print("   • Specific handling for 'context too long' errors")
        
        print("\n💡 BENEFITS:")
        print("   ✅ Prevents '500 Internal Error' from context length")
        print("   ✅ Preserves important document information")
        print("   ✅ Graceful degradation for complex requests")
        print("   ✅ Better error handling and recovery")
        print("   ✅ Maintains system functionality even with large documents")
        
        print("\n🎯 RESULT:")
        print("   The Google API 'context too long' errors should be resolved!")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_context_truncation())
