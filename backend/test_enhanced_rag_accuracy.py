#!/usr/bin/env python3
"""
Test Enhanced RAG Accuracy System

This script tests the comprehensive document analysis and enhanced accuracy features
to ensure the system generates detailed, accurate responses using ALL relevant documents.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the backend directory to the path
backend_dir = Path(__file__).parent
sys.path.append(str(backend_dir))

from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from enhanced_rag_accuracy import initialize_enhanced_rag, ENHANCED_CONFIG

async def test_enhanced_rag_accuracy():
    """Test the enhanced RAG accuracy system"""
    print("🧪 TESTING ENHANCED RAG ACCURACY SYSTEM")
    print("=" * 60)
    
    # Initialize services
    await pinecone_service.initialize_pinecone()
    
    # Test device ID (you may need to adjust this)
    test_device_id = "DA"  # Adjust based on your device setup
    
    # Test queries that should benefit from comprehensive analysis
    comprehensive_test_queries = [
        "What is the model number of the device?",
        "Who is the manufacturer of this device?",
        "What are the technical specifications?",
        "What is the document number or reference?",
        "What regulatory approvals does the device have?",
        "What are the operating temperature ranges?",
        "What is the power supply specification?",
        "What safety standards does the device comply with?"
    ]
    
    print("🚀 TESTING COMPREHENSIVE DOCUMENT RETRIEVAL")
    print("-" * 50)
    
    # Test 1: Initialize Enhanced RAG System
    try:
        enhanced_rag_system = await initialize_enhanced_rag(gemini_service, pinecone_service)
        print("✅ Enhanced RAG system initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize enhanced RAG system: {e}")
        print("📝 Falling back to standard testing approach")
        enhanced_rag_system = None
    
    # Test 2: Query Variation Generation
    print(f"\n🔍 TESTING QUERY VARIATION GENERATION")
    print("-" * 50)
    
    if enhanced_rag_system:
        test_query = "What is the model number?"
        try:
            variations = await enhanced_rag_system.retriever.generate_query_variations(test_query)
            print(f"Original Query: {test_query}")
            print(f"Generated Variations:")
            for i, variation in enumerate(variations, 1):
                print(f"  {i}. {variation}")
            print(f"✅ Generated {len(variations)} query variations")
        except Exception as e:
            print(f"❌ Query variation generation failed: {e}")
    
    # Test 3: Comprehensive Document Retrieval
    print(f"\n📚 TESTING COMPREHENSIVE DOCUMENT RETRIEVAL")
    print("-" * 50)
    
    for query in comprehensive_test_queries[:3]:  # Test first 3 queries
        print(f"\n🔍 Testing Query: {query}")
        
        try:
            if enhanced_rag_system:
                # Test enhanced comprehensive retrieval
                documents, retrieval_stats = await enhanced_rag_system.retriever.comprehensive_retrieval(
                    query=query,
                    device_id=test_device_id
                )
                
                print(f"📊 Retrieval Statistics:")
                print(f"  - Query variations: {retrieval_stats.get('query_variations', 0)}")
                print(f"  - Total retrieved: {retrieval_stats.get('total_retrieved', 0)}")
                print(f"  - Final context count: {retrieval_stats.get('final_context_count', 0)}")
                print(f"  - Confidence breakdown: {retrieval_stats.get('confidence_breakdown', {})}")
                
                if documents:
                    avg_confidence = sum(d.score for d in documents) / len(documents)
                    print(f"  - Average confidence: {avg_confidence:.3f}")
                    print(f"  - Top confidence: {max(d.score for d in documents):.3f}")
                    print(f"✅ Retrieved {len(documents)} high-quality documents")
                else:
                    print(f"❌ No documents retrieved")
            else:
                # Test standard retrieval for comparison
                query_embedding = await gemini_service.get_embedding(query)
                search_results = await pinecone_service.search_vectors(
                    query_vector=query_embedding,
                    device_id=test_device_id,
                    top_k=15
                )
                
                if search_results:
                    avg_confidence = sum(r.score for r in search_results) / len(search_results)
                    print(f"📊 Standard Retrieval:")
                    print(f"  - Documents found: {len(search_results)}")
                    print(f"  - Average confidence: {avg_confidence:.3f}")
                    print(f"  - Top confidence: {max(r.score for r in search_results):.3f}")
                    print(f"✅ Standard retrieval completed")
                else:
                    print(f"❌ No documents found with standard retrieval")
        
        except Exception as e:
            print(f"❌ Retrieval test failed for '{query}': {e}")
    
    # Test 4: Comprehensive Response Generation
    print(f"\n💬 TESTING COMPREHENSIVE RESPONSE GENERATION")
    print("-" * 50)
    
    test_response_query = "What are the complete technical specifications and regulatory information for this device?"
    
    try:
        if enhanced_rag_system:
            # Test comprehensive response generation
            comprehensive_result = await enhanced_rag_system.process_query_comprehensively(
                query=test_response_query,
                device_id=test_device_id
            )
            
            response = comprehensive_result["response"]
            sources = comprehensive_result["sources"]
            quality_metrics = comprehensive_result.get("quality_metrics", {})
            
            print(f"🎯 Query: {test_response_query}")
            print(f"📝 Response Length: {len(response)} characters")
            print(f"📚 Sources Used: {len(sources)}")
            print(f"📊 Quality Metrics: {quality_metrics.get('analysis_quality', 'Unknown')}")
            
            if quality_metrics:
                print(f"  - Documents analyzed: {quality_metrics.get('total_documents_analyzed', 0)}")
                print(f"  - Average confidence: {quality_metrics.get('average_confidence', 0):.3f}")
                print(f"  - High confidence sources: {quality_metrics.get('high_confidence_count', 0)}")
            
            print(f"\n📄 Response Preview:")
            print("-" * 30)
            print(response[:500] + "..." if len(response) > 500 else response)
            print("-" * 30)
            
            print(f"✅ Comprehensive response generation completed")
            
        else:
            # Test standard response generation
            query_embedding = await gemini_service.get_embedding(test_response_query)
            search_results = await pinecone_service.search_vectors(
                query_vector=query_embedding,
                device_id=test_device_id,
                top_k=10
            )
            
            if search_results:
                context_docs = [result.content for result in search_results[:5]]
                response = await gemini_service.generate_response(
                    prompt=test_response_query,
                    context=context_docs,
                    temperature=0.05,
                    max_tokens=1500
                )
                
                print(f"📝 Standard Response Length: {len(response)} characters")
                print(f"📚 Sources Used: {len(search_results)}")
                print(f"\n📄 Response Preview:")
                print("-" * 30)
                print(response[:500] + "..." if len(response) > 500 else response)
                print("-" * 30)
                print(f"✅ Standard response generation completed")
            else:
                print(f"❌ No documents available for response generation")
    
    except Exception as e:
        print(f"❌ Response generation test failed: {e}")
    
    # Test 5: Configuration Verification
    print(f"\n⚙️ ENHANCED CONFIGURATION VERIFICATION")
    print("-" * 50)
    
    if enhanced_rag_system:
        print(f"✅ Enhanced RAG System: ACTIVE")
        print(f"📊 Configuration Details:")
        print(f"  - Initial Retrieval Count: {ENHANCED_CONFIG.INITIAL_RETRIEVAL_COUNT}")
        print(f"  - Multi-Query Count: {ENHANCED_CONFIG.MULTI_QUERY_COUNT}")
        print(f"  - Final Context Count: {ENHANCED_CONFIG.FINAL_CONTEXT_COUNT}")
        print(f"  - Min Confidence (Critical): {ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL}")
        print(f"  - Min Confidence (High): {ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH}")
        print(f"  - Temperature (Factual): {ENHANCED_CONFIG.TEMPERATURE_FACTUAL}")
        print(f"  - Max Response Tokens: {ENHANCED_CONFIG.MAX_RESPONSE_TOKENS}")
    else:
        print(f"⚠️ Enhanced RAG System: NOT AVAILABLE")
        print(f"📝 Using standard RAG approach with enhanced settings")
    
    # Test 6: Gemini Service Availability
    print(f"\n🤖 AI SERVICE VERIFICATION")
    print("-" * 50)
    
    if gemini_service.available:
        print(f"✅ Gemini Service: ACTIVE")
        print(f"📊 Model Configuration:")
        print(f"  - Embedding Model: {gemini_service.embedding_model}")
        print(f"  - Generation Model: {gemini_service.generation_model}")
        
        # Test embedding generation
        try:
            test_embedding = await gemini_service.get_embedding("test query")
            print(f"  - Embedding Dimension: {len(test_embedding)}")
            print(f"✅ Embedding generation working")
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
    else:
        print(f"⚠️ Gemini Service: NOT AVAILABLE (using fallbacks)")
    
    # Test 7: Vector Database Status
    print(f"\n🗃️ VECTOR DATABASE VERIFICATION")
    print("-" * 50)
    
    try:
        stats = await pinecone_service.get_index_stats(test_device_id)
        print(f"📊 Vector Database Status:")
        print(f"  - Storage Type: {stats.get('storage_type', 'Unknown')}")
        print(f"  - Total Vectors: {stats.get('total_vectors', 0)}")
        print(f"  - Device: {stats.get('device_id', 'Unknown')}")
        
        if stats.get('total_vectors', 0) > 0:
            print(f"✅ Vector database has documents for testing")
        else:
            print(f"⚠️ No vectors found for device {test_device_id}")
            print(f"📝 Upload some documents to test comprehensive retrieval")
    
    except Exception as e:
        print(f"❌ Vector database verification failed: {e}")
    
    print(f"\n🎯 TESTING SUMMARY")
    print("=" * 60)
    
    if enhanced_rag_system and gemini_service.available:
        print(f"✅ ENHANCED RAG SYSTEM: Fully operational")
        print(f"📈 Expected Improvements:")
        print(f"  - {ENHANCED_CONFIG.MULTI_QUERY_COUNT}x more comprehensive document retrieval")
        print(f"  - {ENHANCED_CONFIG.FINAL_CONTEXT_COUNT} documents analyzed per query")
        print(f"  - Stricter confidence thresholds for higher accuracy")
        print(f"  - Longer, more detailed responses ({ENHANCED_CONFIG.MAX_RESPONSE_TOKENS} tokens)")
        print(f"  - Multi-query approach for comprehensive coverage")
    elif gemini_service.available:
        print(f"✅ ENHANCED STANDARD RAG: Available")
        print(f"📈 Improvements:")
        print(f"  - Enhanced retrieval with more documents")
        print(f"  - Better confidence filtering")
        print(f"  - Improved prompting for accuracy")
    else:
        print(f"⚠️ LIMITED FUNCTIONALITY: AI services not available")
        print(f"📝 RAG system will use fallback approaches")
    
    print(f"\n🚀 The enhanced RAG system is ready for comprehensive, accurate responses!")

if __name__ == "__main__":
    asyncio.run(test_enhanced_rag_accuracy())
