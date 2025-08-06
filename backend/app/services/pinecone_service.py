import os
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from app.models import VectorSearchResult
import logging
import json
import pickle
from pathlib import Path
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class PineconeService:
    def __init__(self):
        self.pc = None  # Pinecone client
        self.index = None
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "rag-system-index")
        self.local_storage_path = Path("./local_vector_storage")
        self.local_storage_path.mkdir(exist_ok=True)
        
    def _get_local_storage_file(self, device_id: str) -> Path:
        """Get local storage file path for a device"""
        return self.local_storage_path / f"device_{device_id}_vectors.json"
        
    def _load_local_vectors(self, device_id: str) -> List[Dict[str, Any]]:
        """Load vectors from local storage"""
        storage_file = self._get_local_storage_file(device_id)
        if storage_file.exists():
            try:
                with open(storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load local vectors: {e}")
        return []
        
    def _save_local_vectors(self, device_id: str, vectors: List[Dict[str, Any]]) -> bool:
        """Save vectors to local storage"""
        try:
            storage_file = self._get_local_storage_file(device_id)
            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(vectors, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save local vectors: {e}")
            return False
            
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            a_np = np.array(a)
            b_np = np.array(b)
            return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))
        except:
            return 0.0
        
    async def initialize_pinecone(self):
        """Initialize Pinecone connection"""
        try:
            api_key = os.getenv("PINECONE_API_KEY")
            
            if not api_key or api_key == "dummy_key_for_testing":
                logger.warning("❌ Pinecone API key not provided or is dummy key")
                logger.info("📝 Pinecone service will be disabled (using local storage for vectors)")
                return
            
            # Initialize Pinecone with the new API
            self.pc = Pinecone(api_key=api_key)
            
            # Check if index exists first
            existing_indexes = [index.name for index in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.warning(f"❌ Pinecone index '{self.index_name}' does not exist")
                logger.info("📝 Please create the index manually or check your pod limits")
                logger.info("📝 Pinecone service will be disabled (using local storage for vectors)")
                return
            
            # Try to connect to existing index
            self.index = self.pc.Index(self.index_name)
            
            # Test the connection with a simple describe operation
            stats = self.index.describe_index_stats()
            print("✅ Pinecone connected successfully")
            logger.info("✅ Pinecone initialized successfully")
            
        except Exception as e:
            error_msg = str(e)
            if "max pods allowed" in error_msg.lower() or "pod" in error_msg.lower():
                logger.warning("❌ Pinecone pod limit reached")
                logger.info("📝 Please check your Pinecone console to manage pod limits")
                logger.info("📝 Pinecone service will be disabled (using local storage for vectors)")
            elif "index not found" in error_msg.lower():
                logger.warning("❌ Pinecone index not found")
                logger.info("📝 Please create the index manually in your Pinecone console")
                logger.info("📝 Pinecone service will be disabled (using local storage for vectors)")
            else:
                logger.error(f"❌ Failed to initialize Pinecone: {e}")
                logger.info("📝 Pinecone service will be disabled (using local storage for vectors)")
            
            # Set index to None to enable fallback mode
            self.index = None
    
    async def upsert_vectors(
        self, 
        vectors: List[Dict[str, Any]], 
        device_id: str
    ) -> bool:
        """Upsert vectors to Pinecone with device isolation or local storage fallback"""
        try:
            if self.index:
                # Use Pinecone if available
                # Add device_id to metadata for isolation
                for vector in vectors:
                    if 'metadata' not in vector:
                        vector['metadata'] = {}
                    vector['metadata']['device_id'] = device_id
                
                self.index.upsert(vectors=vectors, namespace=f"device_{device_id}")
                logger.info(f"✅ Upserted {len(vectors)} vectors to Pinecone for device {device_id}")
                return True
            else:
                # Fallback to local storage
                existing_vectors = self._load_local_vectors(device_id)
                
                # Add new vectors (simple append for now - could be improved with deduplication)
                for vector in vectors:
                    if 'metadata' not in vector:
                        vector['metadata'] = {}
                    vector['metadata']['device_id'] = device_id
                    # Convert numpy arrays to lists for JSON serialization
                    if 'values' in vector and hasattr(vector['values'], 'tolist'):
                        vector['values'] = vector['values'].tolist()
                    existing_vectors.append(vector)
                
                if self._save_local_vectors(device_id, existing_vectors):
                    logger.info(f"✅ Stored {len(vectors)} vectors locally for device {device_id}")
                    return True
                else:
                    logger.error(f"❌ Failed to store vectors locally for device {device_id}")
                    return False
            
        except Exception as e:
            logger.error(f"❌ Failed to upsert vectors: {e}")
            return False
    
    async def search_vectors(
        self, 
        query_vector: List[float], 
        device_id: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_low_quality: bool = False
    ) -> List[VectorSearchResult]:
        """Enhanced vector search with quality filtering and comprehensive retrieval"""
        try:
            # ENHANCED: Increase top_k for better coverage, then filter by quality
            enhanced_top_k = min(top_k * 3, 50)  # Get more results initially
            
            if self.index:
                # Use Pinecone if available
                # Ensure device isolation in filter
                device_filter = {"device_id": device_id}
                if filter_metadata:
                    device_filter.update(filter_metadata)
                
                # ENHANCED: Add quality filtering unless explicitly disabled
                if not include_low_quality:
                    if "chunk_quality_score" not in device_filter:
                        device_filter["chunk_quality_score"] = {"$gte": 0.3}  # Minimum quality threshold
                
                results = self.index.query(
                    vector=query_vector,
                    top_k=enhanced_top_k,
                    include_metadata=True,
                    namespace=f"device_{device_id}",
                    filter=device_filter
                )
                
                search_results = []
                for match in results.matches:
                    search_results.append(VectorSearchResult(
                        content=match.metadata.get('content', ''),
                        metadata=match.metadata,
                        score=match.score
                    ))
                
                # ENHANCED: Post-process results for better quality and diversity
                enhanced_results = self._enhance_search_results(search_results, top_k)
                return enhanced_results
                
            else:
                # Fallback to local storage with enhanced similarity search
                vectors = self._load_local_vectors(device_id)
                
                if not vectors:
                    return []
                
                # Calculate similarities
                similarities = []
                for i, vector in enumerate(vectors):
                    if 'values' in vector:
                        similarity = self._cosine_similarity(query_vector, vector['values'])
                        
                        # ENHANCED: Apply quality filtering
                        metadata = vector.get('metadata', {})
                        quality_score = metadata.get('chunk_quality_score', 0.5)
                        
                        if include_low_quality or quality_score >= 0.3:
                            similarities.append((i, similarity, vector))
                
                # Sort by similarity and take enhanced top_k
                similarities.sort(key=lambda x: x[1], reverse=True)
                top_results = similarities[:enhanced_top_k]
                
                search_results = []
                for _, score, vector in top_results:
                    metadata = vector.get('metadata', {})
                    
                    # Apply additional filter if provided
                    if filter_metadata:
                        skip = False
                        for key, value in filter_metadata.items():
                            if metadata.get(key) != value:
                                skip = True
                                break
                        if skip:
                            continue
                    
                    search_results.append(VectorSearchResult(
                        content=metadata.get('content', ''),
                        metadata=metadata,
                        score=score
                    ))
                
                # ENHANCED: Post-process results
                enhanced_results = self._enhance_search_results(search_results, top_k)
                
                logger.info(f"✅ Found {len(enhanced_results)} quality results from local storage for device {device_id}")
                return enhanced_results
            
        except Exception as e:
            logger.error(f"❌ Failed to search vectors: {e}")
            return []
    
    def _enhance_search_results(self, search_results: List[VectorSearchResult], target_count: int) -> List[VectorSearchResult]:
        """Enhance search results with quality filtering and diversity"""
        try:
            if not search_results:
                return search_results
            
            # Sort by composite score (similarity + quality)
            enhanced_results = []
            for result in search_results:
                metadata = result.metadata
                
                # Calculate composite score
                similarity_score = result.score
                quality_score = metadata.get('chunk_quality_score', 0.5)
                importance_score = metadata.get('importance_score', 0.5)
                
                # Weighted composite score
                composite_score = (
                    similarity_score * 0.6 +           # 60% similarity
                    quality_score * 0.25 +             # 25% quality
                    importance_score * 0.15             # 15% importance
                )
                
                enhanced_results.append({
                    'result': result,
                    'composite_score': composite_score,
                    'has_form_fields': metadata.get('has_form_fields', False),
                    'content_type': metadata.get('content_type', 'text')
                })
            
            # Sort by composite score
            enhanced_results.sort(key=lambda x: x['composite_score'], reverse=True)
            
            # Apply diversity filtering to avoid too much similar content
            diverse_results = []
            seen_content_hashes = set()
            
            for item in enhanced_results:
                result = item['result']
                content = result.content
                
                # Create a simple hash for content similarity
                content_hash = hash(content[:100].lower().strip())
                
                # Add if we haven't seen similar content OR if it's high importance
                if (content_hash not in seen_content_hashes or 
                    item['composite_score'] > 0.8 or 
                    item['has_form_fields']):
                    
                    diverse_results.append(result)
                    seen_content_hashes.add(content_hash)
                    
                    if len(diverse_results) >= target_count:
                        break
            
            # If we don't have enough diverse results, fill with the next best
            if len(diverse_results) < target_count:
                for item in enhanced_results:
                    if item['result'] not in diverse_results:
                        diverse_results.append(item['result'])
                        if len(diverse_results) >= target_count:
                            break
            
            logger.info(f"📊 Enhanced search: {len(search_results)} → {len(diverse_results)} diverse, high-quality results")
            return diverse_results[:target_count]
            
        except Exception as e:
            logger.error(f"❌ Failed to enhance search results: {e}")
            return search_results[:target_count]
    
    async def comprehensive_search(
        self, 
        query_vectors: List[List[float]], 
        device_id: str,
        top_k_per_query: int = 8,
        final_top_k: int = 15
    ) -> List[VectorSearchResult]:
        """Comprehensive search using multiple query vectors for maximum coverage"""
        try:
            all_results = []
            
            # Search with each query vector
            for i, query_vector in enumerate(query_vectors):
                results = await self.search_vectors(
                    query_vector=query_vector,
                    device_id=device_id,
                    top_k=top_k_per_query,
                    include_low_quality=False
                )
                
                # Tag results with query info
                for result in results:
                    result.metadata['query_index'] = i
                    all_results.append(result)
            
            # Deduplicate and enhance
            unique_results = {}
            for result in all_results:
                content_key = result.content[:100]  # Use first 100 chars as key
                
                if content_key not in unique_results or result.score > unique_results[content_key].score:
                    unique_results[content_key] = result
            
            # Convert back to list and enhance
            final_results = list(unique_results.values())
            enhanced_final = self._enhance_search_results(final_results, final_top_k)
            
            logger.info(f"📊 Comprehensive search: {len(query_vectors)} queries → {len(all_results)} results → {len(enhanced_final)} final")
            return enhanced_final
            
        except Exception as e:
            logger.error(f"❌ Failed in comprehensive search: {e}")
            return []
    
    async def delete_vectors(
        self, 
        vector_ids: List[str], 
        device_id: str
    ) -> bool:
        """Delete vectors by IDs with device isolation"""
        try:
            if self.index:
                # Use Pinecone if available
                self.index.delete(ids=vector_ids, namespace=f"device_{device_id}")
                logger.info(f"✅ Deleted {len(vector_ids)} vectors from Pinecone for device {device_id}")
                return True
            else:
                # Fallback to local storage deletion
                vectors = self._load_local_vectors(device_id)
                
                if not vectors:
                    logger.info(f"📝 No vectors found in local storage for device {device_id}")
                    return True  # Consider success if no vectors exist
                
                # Filter out vectors with matching IDs
                initial_count = len(vectors)
                filtered_vectors = [
                    vector for vector in vectors 
                    if vector.get('id') not in vector_ids
                ]
                
                deleted_count = initial_count - len(filtered_vectors)
                
                if deleted_count > 0:
                    # Save the filtered vectors back to local storage
                    if self._save_local_vectors(device_id, filtered_vectors):
                        logger.info(f"✅ Deleted {deleted_count} vectors from local storage for device {device_id}")
                        return True
                    else:
                        logger.error(f"❌ Failed to save filtered vectors to local storage for device {device_id}")
                        return False
                else:
                    logger.info(f"📝 No matching vectors found to delete for device {device_id}")
                    return True  # Consider success if no matching vectors found
            
        except Exception as e:
            logger.error(f"❌ Failed to delete vectors: {e}")
            return False
    
    async def delete_document_vectors(self, document_id: str, device_id: str) -> bool:
        """Delete all vectors for a specific document"""
        try:
            if self.index:
                # Use Pinecone metadata filtering to delete all vectors for this document
                self.index.delete(
                    filter={"document_id": document_id},
                    namespace=f"device_{device_id}"
                )
                logger.info(f"✅ Deleted all vectors for document {document_id} from Pinecone for device {device_id}")
                return True
            else:
                # Fallback to local storage deletion
                vectors = self._load_local_vectors(device_id)
                
                if not vectors:
                    logger.info(f"📝 No vectors found in local storage for device {device_id}")
                    return True
                
                # Filter out vectors with matching document_id
                initial_count = len(vectors)
                filtered_vectors = [
                    vector for vector in vectors 
                    if vector.get('metadata', {}).get('document_id') != document_id
                ]
                
                deleted_count = initial_count - len(filtered_vectors)
                
                if deleted_count > 0:
                    # Save the filtered vectors back to local storage
                    if self._save_local_vectors(device_id, filtered_vectors):
                        logger.info(f"✅ Deleted {deleted_count} vectors for document {document_id} from local storage for device {device_id}")
                        return True
                    else:
                        logger.error(f"❌ Failed to save filtered vectors to local storage for device {device_id}")
                        return False
                else:
                    logger.info(f"📝 No vectors found for document {document_id} in device {device_id}")
                    return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document vectors: {e}")
            return False
    
    async def cleanup_orphaned_vectors(self, device_id: str, valid_document_ids: List[str]) -> int:
        """Remove vectors that don't correspond to existing documents"""
        try:
            if self.index:
                # For Pinecone, we'd need to query and filter, which is complex
                # This feature would require fetching all vectors and checking metadata
                logger.info("🔧 Orphaned vector cleanup for Pinecone not implemented (requires manual intervention)")
                return 0
            else:
                # For local storage, we can easily clean up
                vectors = self._load_local_vectors(device_id)
                
                if not vectors:
                    return 0
                
                initial_count = len(vectors)
                
                # Keep only vectors that have document_ids in the valid list
                valid_vectors = [
                    vector for vector in vectors 
                    if vector.get('metadata', {}).get('document_id') in valid_document_ids
                ]
                
                orphaned_count = initial_count - len(valid_vectors)
                
                if orphaned_count > 0:
                    if self._save_local_vectors(device_id, valid_vectors):
                        logger.info(f"🧹 Cleaned up {orphaned_count} orphaned vectors for device {device_id}")
                        return orphaned_count
                    else:
                        logger.error(f"❌ Failed to save cleaned vectors for device {device_id}")
                        return 0
                else:
                    logger.info(f"✅ No orphaned vectors found for device {device_id}")
                    return 0
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup orphaned vectors: {e}")
            return 0
    
    async def get_index_stats(self, device_id: str) -> Dict[str, Any]:
        """Get index statistics for a specific device"""
        try:
            if self.index:
                # Use Pinecone if available
                stats = self.index.describe_index_stats()
                device_namespace = f"device_{device_id}"
                
                if device_namespace in stats.namespaces:
                    return {
                        "total_vectors": stats.namespaces[device_namespace].vector_count,
                        "device_id": device_id,
                        "namespace": device_namespace,
                        "storage_type": "pinecone"
                    }
                else:
                    return {
                        "total_vectors": 0,
                        "device_id": device_id,
                        "namespace": device_namespace,
                        "storage_type": "pinecone"
                    }
            else:
                # Use local storage
                vectors = self._load_local_vectors(device_id)
                return {
                    "total_vectors": len(vectors),
                    "device_id": device_id,
                    "namespace": f"device_{device_id}",
                    "storage_type": "local"
                }
                
        except Exception as e:
            logger.error(f"❌ Failed to get index stats: {e}")
            return {
                "total_vectors": 0,
                "device_id": device_id,
                "error": str(e),
                "storage_type": "unknown"
            }

# Global instance
pinecone_service = PineconeService()
