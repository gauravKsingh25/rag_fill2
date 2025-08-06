#!/usr/bin/env python3
"""
Enhanced Debug Script for Pinecone Vector Issues

This script will:
1. Check if vectors are being stored locally
2. Check if vectors are being uploaded to Pinecone
3. Test namespace access
4. Verify embedding generation
"""

import asyncio
import logging
import os
import sys
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.pinecone_service import pinecone_service
from app.services.gemini_service import gemini_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def detailed_debug():
    """Detailed debugging of vector storage and retrieval"""
    logger.info("🔍 DETAILED PINECONE DEBUG")
    logger.info("="*80)
    
    device_id = "test_comprehensive_coverage"
    
    # Step 1: Check local storage
    logger.info("📁 STEP 1: Checking Local Storage")
    local_file = backend_dir / "local_vector_storage" / f"device_{device_id}_vectors.json"
    
    if local_file.exists():
        logger.info(f"✅ Local storage file exists: {local_file}")
        
        with open(local_file, 'r', encoding='utf-8') as f:
            local_vectors = json.load(f)
        
        logger.info(f"📊 Local vectors count: {len(local_vectors)}")
        
        if local_vectors:
            # Examine first vector
            first_vector = local_vectors[0]
            logger.info(f"📄 First vector keys: {list(first_vector.keys())}")
            
            if 'metadata' in first_vector:
                metadata = first_vector['metadata']
                logger.info(f"📊 Metadata keys: {list(metadata.keys())}")
                logger.info(f"   Device ID: {metadata.get('device_id', 'NOT_FOUND')}")
                logger.info(f"   Filename: {metadata.get('filename', 'NOT_FOUND')}")
                logger.info(f"   Content preview: {metadata.get('content', 'NO_CONTENT')[:100]}...")
                
            if 'values' in first_vector:
                logger.info(f"📊 Vector dimension: {len(first_vector['values'])}")
            else:
                logger.info("❌ No 'values' key in vector!")
    else:
        logger.error(f"❌ Local storage file not found: {local_file}")
        return
    
    # Step 2: Initialize Pinecone and check connection
    logger.info("\n🔗 STEP 2: Pinecone Connection")
    await pinecone_service.initialize_pinecone()
    
    if pinecone_service.index is None:
        logger.error("❌ Pinecone not initialized!")
        return
    
    # Step 3: Check index stats
    logger.info("\n📊 STEP 3: Index Statistics")
    stats = pinecone_service.index.describe_index_stats()
    logger.info(f"Total vectors: {stats.total_vector_count}")
    logger.info(f"Namespaces: {list(stats.namespaces.keys())}")
    
    expected_namespace = f"device_{device_id}"
    logger.info(f"Expected namespace: {expected_namespace}")
    
    if expected_namespace in stats.namespaces:
        namespace_count = stats.namespaces[expected_namespace].vector_count
        logger.info(f"✅ Namespace exists with {namespace_count} vectors")
    else:
        logger.warning(f"❌ Expected namespace not found in: {list(stats.namespaces.keys())}")
        
        # Try to upload one vector to test
        logger.info("🧪 Testing vector upload...")
        if local_vectors:
            test_vector = local_vectors[0]
            try:
                pinecone_service.index.upsert(
                    vectors=[test_vector], 
                    namespace=expected_namespace
                )
                logger.info("✅ Test vector uploaded successfully")
                
                # Check stats again
                stats = pinecone_service.index.describe_index_stats()
                if expected_namespace in stats.namespaces:
                    logger.info(f"✅ Namespace now exists with {stats.namespaces[expected_namespace].vector_count} vectors")
                else:
                    logger.warning("❌ Namespace still not found after upload")
                    
            except Exception as e:
                logger.error(f"❌ Failed to upload test vector: {e}")
    
    # Step 4: Test search directly on Pinecone
    logger.info("\n🔍 STEP 4: Direct Pinecone Search")
    
    test_query = "VitalWatch Pro"
    query_embedding = await gemini_service.get_embedding(test_query)
    logger.info(f"Generated embedding for '{test_query}' (dim: {len(query_embedding)})")
    
    try:
        # Search in the expected namespace
        results = pinecone_service.index.query(
            vector=query_embedding,
            top_k=5,
            include_metadata=True,
            namespace=expected_namespace
        )
        
        logger.info(f"📊 Direct search results: {len(results.matches)}")
        
        for i, match in enumerate(results.matches):
            logger.info(f"  Result {i+1}: ID={match.id}, Score={match.score:.4f}")
            if match.metadata:
                filename = match.metadata.get('filename', 'NO_FILENAME')
                content = match.metadata.get('content', 'NO_CONTENT')[:100]
                logger.info(f"    File: {filename}")
                logger.info(f"    Content: {content}...")
        
    except Exception as e:
        logger.error(f"❌ Direct search failed: {e}")
    
    # Step 5: Test service method
    logger.info("\n🔧 STEP 5: Service Method Test")
    
    try:
        service_results = await pinecone_service.search_vectors(
            query_vector=query_embedding,
            device_id=device_id,
            top_k=5
        )
        
        logger.info(f"📊 Service method results: {len(service_results)}")
        
        for i, result in enumerate(service_results):
            logger.info(f"  Service Result {i+1}: Score={result.score:.4f}")
            logger.info(f"    Content: {result.content[:100]}...")
            
    except Exception as e:
        logger.error(f"❌ Service method failed: {e}")
    
    # Step 6: Test with simple content
    logger.info("\n🧪 STEP 6: Test Simple Search Terms")
    
    simple_terms = ["VitalWatch", "medical", "device", "monitor", "FDA"]
    
    for term in simple_terms:
        try:
            embedding = await gemini_service.get_embedding(term)
            
            # Try direct search
            results = pinecone_service.index.query(
                vector=embedding,
                top_k=3,
                include_metadata=True,
                namespace=expected_namespace
            )
            
            logger.info(f"  '{term}': {len(results.matches)} direct results")
            
            # Try service method
            service_results = await pinecone_service.search_vectors(
                query_vector=embedding,
                device_id=device_id,
                top_k=3
            )
            
            logger.info(f"  '{term}': {len(service_results)} service results")
            
        except Exception as e:
            logger.error(f"❌ Failed to search for '{term}': {e}")

async def main():
    await detailed_debug()

if __name__ == "__main__":
    asyncio.run(main())
