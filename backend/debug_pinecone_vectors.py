#!/usr/bin/env python3
"""
Debug Pinecone Vector Storage and Retrieval

This script will check:
1. How many vectors are actually stored in Pinecone
2. What metadata is being stored
3. Test simple vector retrieval
4. Check if embeddings are being generated correctly
"""

import asyncio
import logging
import os
import sys
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

async def debug_pinecone_storage():
    """Debug what's actually stored in Pinecone"""
    logger.info("🔍 Debugging Pinecone Vector Storage")
    logger.info("="*60)
    
    try:
        # Initialize Pinecone
        await pinecone_service.initialize_pinecone()
        
        # Get index stats
        index_stats = pinecone_service.index.describe_index_stats()
        logger.info(f"📊 Index Stats: {index_stats}")
        
        # Check for our test device
        device_id = "test_comprehensive_coverage"
        
        # Try to query all vectors for our device
        logger.info(f"🔍 Searching for vectors with device_id: {device_id}")
        
        # Create a test query vector to search with
        test_query = "VitalWatch Pro"
        query_embedding = await gemini_service.get_embedding(test_query)
        logger.info(f"✅ Generated embedding for test query (length: {len(query_embedding)})")
        
        # Search for vectors - try with and without filters
        logger.info("🔍 Testing search without device filter...")
        results_no_filter = pinecone_service.index.query(
            vector=query_embedding,
            top_k=10,
            include_metadata=True,
            include_values=False
        )
        logger.info(f"📊 Found {len(results_no_filter.matches)} results without device filter")
        
        if results_no_filter.matches:
            for i, match in enumerate(results_no_filter.matches[:3]):
                logger.info(f"  Result {i+1}: ID={match.id}, Score={match.score:.4f}")
                logger.info(f"    Metadata keys: {list(match.metadata.keys()) if match.metadata else 'None'}")
                if match.metadata:
                    device = match.metadata.get('device_id', 'NO_DEVICE')
                    filename = match.metadata.get('filename', 'NO_FILENAME')
                    logger.info(f"    Device: {device}, File: {filename}")
        
        logger.info(f"🔍 Testing search with device filter: {device_id}")
        results_with_filter = pinecone_service.index.query(
            vector=query_embedding,
            top_k=10,
            include_metadata=True,
            include_values=False,
            filter={"device_id": device_id}
        )
        logger.info(f"📊 Found {len(results_with_filter.matches)} results with device filter")
        
        if results_with_filter.matches:
            for i, match in enumerate(results_with_filter.matches[:3]):
                logger.info(f"  Result {i+1}: ID={match.id}, Score={match.score:.4f}")
                if match.metadata:
                    filename = match.metadata.get('filename', 'NO_FILENAME')
                    content_preview = match.metadata.get('content', '')[:100] + "..."
                    logger.info(f"    File: {filename}")
                    logger.info(f"    Content: {content_preview}")
        
        # Test the Pinecone service search method
        logger.info("🔍 Testing pinecone_service.search_vectors method...")
        service_results = await pinecone_service.search_vectors(
            query_vector=query_embedding,
            device_id=device_id,
            top_k=10
        )
        logger.info(f"📊 Pinecone service returned {len(service_results)} results")
        
        if service_results:
            for i, result in enumerate(service_results[:3]):
                logger.info(f"  Service Result {i+1}: Score={result.score:.4f}")
                logger.info(f"    Content: {result.content[:100]}...")
                logger.info(f"    Metadata: {result.metadata}")
        else:
            logger.warning("❌ Pinecone service returned no results!")
            
            # Let's check what's in the local storage
            logger.info("🔍 Checking local vector storage...")
            local_storage_path = backend_dir / "local_vector_storage"
            if local_storage_path.exists():
                logger.info(f"📁 Local storage exists: {local_storage_path}")
                files = list(local_storage_path.glob("*.json"))
                logger.info(f"📄 Found {len(files)} local vector files")
                for file in files:
                    logger.info(f"  - {file.name}")
            else:
                logger.warning("❌ Local vector storage directory not found!")
        
        # Test with different queries
        test_queries = [
            "VitalWatch",
            "medical device",
            "monitor",
            "FDA",
            "model number"
        ]
        
        logger.info("\n🧪 Testing multiple queries...")
        for query in test_queries:
            embedding = await gemini_service.get_embedding(query)
            results = await pinecone_service.search_vectors(
                query_vector=embedding,
                device_id=device_id,
                top_k=5
            )
            logger.info(f"  '{query}': {len(results)} results")
        
    except Exception as e:
        logger.error(f"❌ Error debugging Pinecone: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main debug execution"""
    await debug_pinecone_storage()

if __name__ == "__main__":
    asyncio.run(main())
