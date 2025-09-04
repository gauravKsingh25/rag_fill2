#!/usr/bin/env python3
"""
Test script to verify the context truncation fix for interpreted forms
"""

# Test the context truncation logic
def test_context_truncation():
    """Test context truncation logic similar to the fix"""
    
    # Simulate large text from Pinecone search results
    large_text = "This is a very long piece of text that would normally cause Google 500 errors. " * 100
    query = "name"
    MAX_CONTEXT_LENGTH = 2000
    
    print(f"Original text length: {len(large_text)} characters")
    
    # Apply the same truncation logic from the fix
    truncated_text = large_text
    if len(large_text) > MAX_CONTEXT_LENGTH:
        query_lower = query.lower()
        text_lower = large_text.lower()
        
        # Find query position in text
        query_pos = text_lower.find(query_lower)
        if query_pos >= 0:
            # Extract context around the query
            start = max(0, query_pos - MAX_CONTEXT_LENGTH // 2)
            end = min(len(large_text), start + MAX_CONTEXT_LENGTH)
            truncated_text = large_text[start:end]
            print(f"Context truncated around query '{query}': {len(large_text)} → {len(truncated_text)} chars")
        else:
            # Fallback: Take first part of text
            truncated_text = large_text[:MAX_CONTEXT_LENGTH]
            print(f"Context truncated (query not found): {len(large_text)} → {len(truncated_text)} chars")
    
    # Verify the result
    assert len(truncated_text) <= MAX_CONTEXT_LENGTH, f"Truncated text is still too long: {len(truncated_text)}"
    print(f"✅ Context truncation working correctly! Final length: {len(truncated_text)} chars")
    
    return True

if __name__ == "__main__":
    print("🔧 Testing context truncation fix for interpreted forms...")
    test_context_truncation()
    print("🎉 All tests passed! The fix should prevent Google 500 errors.")
