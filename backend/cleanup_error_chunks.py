"""
Cleanup script to remove bad chunks with error messages
"""
import asyncio
import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def cleanup_error_chunks():
    """Remove chunks that contain error messages instead of real content"""
    try:
        logger.info("🧹 Starting cleanup of error chunks...")
        
        from app.services.pinecone_service import pinecone_service
        from app.database import document_repo, connect_to_mongo
        
        # Connect to databases
        await connect_to_mongo()
        await pinecone_service.initialize_pinecone()
        
        # Get all documents for device DA
        documents = await document_repo.get_documents_by_device("DA")
        logger.info(f"📊 Found {len(documents)} documents for device DA")
        
        cleaned_count = 0
        for doc in documents:
            doc_id = doc["document_id"]
            logger.info(f"🔍 Checking document {doc_id} ({doc.get('filename', 'unknown')})")
            
            # Check if this document has error message chunks
            if doc.get("chunk_count", 0) == 1:
                # Likely candidate for error chunk - let's check the content
                try:
                    # Query the chunk content
                    query_result = await pinecone_service.query_vectors(
                        query_vector=[0.0] * 1024,  # Dummy vector
                        device_id="DA",
                        top_k=1,
                        filter={"document_id": doc_id}
                    )
                    
                    if query_result and query_result.matches:
                        chunk_content = query_result.matches[0].metadata.get("content", "")
                        
                        # Check if it's an error message
                        if "[DOCUMENT_PROCESSED]" in chunk_content and "timed out" in chunk_content:
                            logger.warning(f"❌ Found error chunk in document {doc_id}")
                            logger.info(f"🗑️ Deleting document {doc_id} with error chunk")
                            
                            # Delete the entire document
                            from app.services.document_processor import document_processor
                            success = await document_processor.delete_document(doc_id, "DA")
                            
                            if success:
                                cleaned_count += 1
                                logger.info(f"✅ Successfully deleted document {doc_id}")
                            else:
                                logger.error(f"❌ Failed to delete document {doc_id}")
                
                except Exception as e:
                    logger.warning(f"⚠️ Could not check document {doc_id}: {e}")
        
        logger.info(f"✅ Cleanup completed - removed {cleaned_count} documents with error chunks")
        
        if cleaned_count > 0:
            logger.info("🔄 Now try uploading your PDF again - it should work with 5-minute timeout!")
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")

if __name__ == "__main__":
    asyncio.run(cleanup_error_chunks())
