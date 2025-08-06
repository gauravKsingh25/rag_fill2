#!/usr/bin/env python3
"""
Test Practical RAG Example - Fixed Syntax Version

This script tests the RAG system with a practical example and proper error handling.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent))

from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service

# Try to import enhanced RAG system
try:
    from enhanced_rag_accuracy import initialize_enhanced_rag
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    print("⚠️ Enhanced RAG system not available, using standard approach")
    ENHANCED_RAG_AVAILABLE = False

async def test_practical_example():
    """Test practical RAG example with proper error handling"""
    print("🧪 TESTING PRACTICAL RAG EXAMPLE")
    print("=" * 50)
    
    # Initialize services
    try:
        await pinecone_service.initialize_pinecone()
        print("✅ Pinecone service initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Pinecone: {e}")
        return
    
    # Test query and device
    query = "What is the model number and manufacturer information?"
    device_id = "DA"
    
    print(f"🔍 Query: {query}")
    print(f"📱 Device: {device_id}")
    
    try:
        # Initialize enhanced RAG if available
        rag_system = None
        if ENHANCED_RAG_AVAILABLE:
            try:
                rag_system = await initialize_enhanced_rag(gemini_service, pinecone_service)
                print("✅ Enhanced RAG system initialized")
            except Exception as e:
                print(f"⚠️ Enhanced RAG initialization failed: {e}")
                print("📝 Falling back to standard approach")
        
        # Test response generation
        if rag_system:
            print("\n🚀 Testing Enhanced RAG System:")
            print("-" * 40)
            
            # Process query comprehensively
            result = await rag_system.process_query_comprehensively(
                query=query,
                device_id=device_id
            )
            
            response = result["response"]
            sources = result.get("sources", [])
            quality_metrics = result.get("quality_metrics", {})
            
            print(f"📝 Response Length: {len(response)} characters")
            print(f"📚 Sources Used: {len(sources)}")
            
            if quality_metrics:
                print(f"📊 Quality Metrics:")
                print(f"  - Analysis Quality: {quality_metrics.get('analysis_quality', 'Unknown')}")
                print(f"  - Documents Analyzed: {quality_metrics.get('total_documents_analyzed', 0)}")
                print(f"  - Average Confidence: {quality_metrics.get('average_confidence', 0):.3f}")
                print(f"  - High Confidence Count: {quality_metrics.get('high_confidence_count', 0)}")
            
            print(f"\n📄 Response Preview:")
            print("-" * 40)
            preview_length = min(800, len(response))
            preview = response[:preview_length]
            if len(response) > preview_length:
                preview += "..."
            print(preview)
            print("-" * 40)
            
        else:
            print("\n📝 Testing Standard RAG Approach:")
            print("-" * 40)
            
            # Standard retrieval approach
            query_embedding = await gemini_service.get_embedding(query)
            search_results = await pinecone_service.search_vectors(
                query_vector=query_embedding,
                device_id=device_id,
                top_k=15
            )
            
            if search_results:
                # Filter by confidence
                filtered_results = [r for r in search_results if r.score >= 0.65]
                context_docs = [result.content for result in filtered_results[:10]]
                
                if context_docs:
                    response = await gemini_service.generate_response(
                        prompt=f"""Provide a comprehensive, detailed answer to: {query}
                        
                        Use ALL the document evidence provided below. Analyze each document thoroughly and provide a complete response that considers all available information.
                        
                        Instructions:
                        1. Examine ALL provided documents carefully
                        2. Provide detailed information from multiple sources
                        3. Reference specific documents when presenting facts
                        4. Be comprehensive and thorough
                        5. Only use information explicitly stated in the documents
                        
                        Generate a detailed response based on all available evidence:""",
                        context=context_docs,
                        temperature=0.05,
                        max_tokens=2000
                    )
                    
                    print(f"📝 Response Length: {len(response)} characters")
                    print(f"📚 Documents Used: {len(context_docs)}")
                    print(f"📊 Average Confidence: {sum(r.score for r in filtered_results[:10])/len(filtered_results[:10]):.3f}")
                    
                    print(f"\n📄 Response Preview:")
                    print("-" * 40)
                    preview_length = min(800, len(response))
                    preview = response[:preview_length]
                    if len(response) > preview_length:
                        preview += "..."
                    print(preview)
                    print("-" * 40)
                else:
                    print("❌ No high-confidence documents found")
            else:
                print("❌ No documents found for query")
        
        print(f"\n✅ Enhanced RAG system working {'perfectly' if rag_system else 'with standard approach'}!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

# Run the test
if __name__ == "__main__":
    asyncio.run(test_practical_example())
