#!/usr/bin/env python3
"""
Debug Enhanced RAG Retrieval

This script debugs the comprehensive retrieval process to see where documents are being filtered out.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent))

from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from enhanced_rag_accuracy import ComprehensiveDocumentRetriever, ENHANCED_CONFIG

async def debug_retrieval():
    """Debug the comprehensive retrieval process"""
    print("🔍 DEBUGGING COMPREHENSIVE RETRIEVAL")
    print("=" * 50)
    
    # Initialize services
    await pinecone_service.initialize_pinecone()
    
    # Create retriever
    retriever = ComprehensiveDocumentRetriever(gemini_service, pinecone_service)
    
    query = "What is the model number and manufacturer information?"
    device_id = "DA"
    
    print(f"📋 Query: {query}")
    print(f"📱 Device: {device_id}")
    
    # Step 1: Generate query variations
    print(f"\n🔀 STEP 1: Generating Query Variations")
    variations = await retriever.generate_query_variations(query)
    print(f"Generated {len(variations)} variations:")
    for i, var in enumerate(variations):
        print(f"  {i+1}. {var}")
    
    # Step 2: Test each variation
    print(f"\n📊 STEP 2: Testing Each Variation")
    all_results = []
    
    for i, query_var in enumerate(variations):
        print(f"\n🔍 Variation {i+1}: {query_var}")
        
        # Generate embedding
        query_embedding = await gemini_service.get_embedding(query_var)
        
        # Search
        search_results = await pinecone_service.search_vectors(
            query_vector=query_embedding,
            device_id=device_id,
            top_k=ENHANCED_CONFIG.INITIAL_RETRIEVAL_COUNT
        )
        
        print(f"  📈 Retrieved: {len(search_results)} documents")
        if search_results:
            avg_score = sum(r.score for r in search_results) / len(search_results)
            print(f"  📊 Avg confidence: {avg_score:.3f}")
            print(f"  🎯 Top confidence: {max(r.score for r in search_results):.3f}")
        
        all_results.extend(search_results)
    
    print(f"\n📈 Total documents before deduplication: {len(all_results)}")
    
    # Step 3: Deduplication
    unique_results = retriever._deduplicate_results(all_results)
    print(f"📈 Documents after deduplication: {len(unique_results)}")
    
    # Step 4: Apply filtering and analyze each step
    print(f"\n🔧 STEP 3: Applying Comprehensive Filtering")
    
    # Test each filter individually
    after_confidence = [r for r in unique_results if r.score >= ENHANCED_CONFIG.MIN_CONFIDENCE_ACCEPTABLE]
    print(f"📊 After confidence filter (≥{ENHANCED_CONFIG.MIN_CONFIDENCE_ACCEPTABLE}): {len(after_confidence)}")
    
    after_quality = []
    for r in after_confidence:
        if retriever._is_content_high_quality(r.content):
            after_quality.append(r)
        else:
            print(f"    ❌ Filtered out low quality: '{r.content[:50]}...' (length: {len(r.content)})")
    print(f"📊 After quality filter: {len(after_quality)}")
    
    after_relevance = []
    for r in after_quality:
        if retriever._is_relevant_to_query(r.content, query):
            after_relevance.append(r)
        else:
            print(f"    ❌ Filtered out irrelevant: '{r.content[:50]}...'")
    print(f"📊 After relevance filter: {len(after_relevance)}")
    
    # Step 5: Final results
    final_results = sorted(after_relevance, key=lambda x: x.score, reverse=True)[:ENHANCED_CONFIG.FINAL_CONTEXT_COUNT]
    print(f"📊 Final results: {len(final_results)}")
    
    if final_results:
        print(f"\n📋 FINAL RESULTS:")
        for i, result in enumerate(final_results[:5]):
            print(f"  {i+1}. Score: {result.score:.3f}")
            print(f"     File: {result.metadata.get('filename', 'Unknown')}")
            print(f"     Content: {result.content[:100]}...")
            print()
    else:
        print(f"\n❌ NO FINAL RESULTS - All documents were filtered out")
        
        # Show what was available before filtering
        print(f"\n📋 AVAILABLE DOCUMENTS BEFORE FILTERING:")
        for i, result in enumerate(unique_results[:10]):
            print(f"  {i+1}. Score: {result.score:.3f}")
            print(f"     Quality: {retriever._is_content_high_quality(result.content)}")
            print(f"     Relevant: {retriever._is_relevant_to_query(result.content, query)}")
            print(f"     Content: {result.content[:100]}...")
            print()

if __name__ == "__main__":
    asyncio.run(debug_retrieval())
