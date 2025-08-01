import os
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Any, Optional
from app.models import VectorSearchResult
import logging
import json
import pickle
from pathlib import Path
import numpy as np

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
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[VectorSearchResult]:
        """Search vectors with device isolation or local storage fallback"""
        try:
            if self.index:
                # Use Pinecone if available
                # Ensure device isolation in filter
                device_filter = {"device_id": device_id}
                if filter_metadata:
                    device_filter.update(filter_metadata)
                
                results = self.index.query(
                    vector=query_vector,
                    top_k=top_k,
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
                
                return search_results
            else:
                # Fallback to local storage with simple similarity search
                vectors = self._load_local_vectors(device_id)
                
                if not vectors:
                    return []
                
                # Calculate similarities
                similarities = []
                for i, vector in enumerate(vectors):
                    if 'values' in vector:
                        similarity = self._cosine_similarity(query_vector, vector['values'])
                        similarities.append((i, similarity, vector))
                
                # Sort by similarity and take top_k
                similarities.sort(key=lambda x: x[1], reverse=True)
                top_results = similarities[:top_k]
                
                search_results = []
                for _, score, vector in top_results:
                    metadata = vector.get('metadata', {})
                    
                    # Apply filter if provided
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
                
                logger.info(f"✅ Found {len(search_results)} results from local storage for device {device_id}")
                return search_results
            
        except Exception as e:
            logger.error(f"❌ Failed to search vectors: {e}")
            return []
    
    async def delete_vectors(
        self, 
        vector_ids: List[str], 
        device_id: str
    ) -> bool:
        """Delete vectors by IDs with device isolation"""
        try:
            if not self.index:
                await self.initialize_pinecone()
            
            self.index.delete(ids=vector_ids, namespace=f"device_{device_id}")
            logger.info(f"✅ Deleted {len(vector_ids)} vectors for device {device_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete vectors: {e}")
            return False
    
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
