import os
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
import json
from pathlib import Path
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def serialize_document(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document for JSON serialization"""
    if doc is None:
        return None
    
    # Convert ObjectId to string
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    
    # Convert datetime objects to ISO format strings
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
    
    return doc

class MongoDB:
    def __init__(self):
        self.client = None
        self.database = None

mongodb = MongoDB()

# Local storage paths
LOCAL_STORAGE_PATH = Path("./local_storage")
LOCAL_STORAGE_PATH.mkdir(exist_ok=True)

async def connect_to_mongo():
    """Create database connection"""
    try:
        mongodb_url = os.getenv("MONGODB_URL")
        
        # If no MongoDB URL is set, skip MongoDB entirely
        if not mongodb_url:
            logger.info("📝 No MONGODB_URL found, using local storage only")
            mongodb.client = None
            mongodb.database = None
            return
        
        # For local MongoDB
        if mongodb_url.startswith("mongodb://localhost") or mongodb_url.startswith("mongodb://127.0.0.1"):
            mongodb.client = AsyncIOMotorClient(mongodb_url)
            await mongodb.client.admin.command('ping', maxTimeMS=3000)
            mongodb.database = mongodb.client[os.getenv("MONGODB_DATABASE", "rag_system")]
            logger.info("✅ Connected to local MongoDB")
            return
        
        # For Atlas - if it fails, just continue with local storage
        logger.info("🔄 Attempting MongoDB Atlas connection...")
        mongodb.client = AsyncIOMotorClient(
            mongodb_url,
            tls=True,
            tlsAllowInvalidCertificates=True,
            serverSelectionTimeoutMS=5000,  # Short timeout
            connectTimeoutMS=5000,
            socketTimeoutMS=5000
        )
        await mongodb.client.admin.command('ping', maxTimeMS=3000)
        mongodb.database = mongodb.client[os.getenv("MONGODB_DATABASE", "rag_system")]
        logger.info("✅ Connected to MongoDB Atlas")
        
    except Exception as e:
        logger.warning(f"❌ MongoDB connection failed: {str(e)[:100]}...")
        logger.info("📝 Continuing with local storage (this is perfectly fine!)")
        mongodb.client = None
        mongodb.database = None

async def close_mongo_connection():
    """Close database connection"""
    if mongodb.client:
        mongodb.client.close()
        logger.info("✅ MongoDB connection closed")

def get_database():
    """Get database instance"""
    return mongodb.database

class DocumentRepository:
    """Repository for document metadata operations"""
    
    def __init__(self):
        self.collection_name = "documents"
        self.local_file = LOCAL_STORAGE_PATH / "documents.json"
    
    def _load_local_documents(self) -> List[Dict[str, Any]]:
        """Load documents from local storage"""
        if self.local_file.exists():
            try:
                with open(self.local_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load local documents: {e}")
        return []
    
    def _save_local_documents(self, documents: List[Dict[str, Any]]) -> bool:
        """Save documents to local storage"""
        try:
            with open(self.local_file, 'w', encoding='utf-8') as f:
                json.dump(documents, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save local documents: {e}")
            return False
    
    async def create_document(self, document_data: Dict[str, Any]) -> str:
        """Create a new document record"""
        try:
            document_data["created_at"] = datetime.utcnow()
            
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                result = await collection.insert_one(document_data)
                return str(result.inserted_id)
            else:
                documents = self._load_local_documents()
                document_id = f"doc_{len(documents) + 1}_{int(datetime.utcnow().timestamp())}"
                document_data["_id"] = document_id
                documents.append(document_data)
                
                if self._save_local_documents(documents):
                    logger.info(f"✅ Saved document to local storage: {document_id}")
                    return document_id
                else:
                    raise Exception("Failed to save to local storage")
                    
        except Exception as e:
            logger.error(f"❌ Failed to create document: {e}")
            raise
    
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        try:
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                document = await collection.find_one({"document_id": document_id})
                return serialize_document(document) if document else None
            else:
                documents = self._load_local_documents()
                for doc in documents:
                    if doc.get("document_id") == document_id or doc.get("_id") == document_id:
                        return doc
                return None
        except Exception as e:
            logger.error(f"❌ Failed to get document {document_id}: {e}")
            return None
    
    async def get_documents_by_device(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all documents for a specific device"""
        try:
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                cursor = collection.find({"device_id": device_id})
                documents = await cursor.to_list(length=None)
                # Serialize all documents
                return [serialize_document(doc) for doc in documents]
            else:
                documents = self._load_local_documents()
                device_documents = [doc for doc in documents if doc.get("device_id") == device_id]
                return device_documents
        except Exception as e:
            logger.error(f"❌ Failed to get documents for device {device_id}: {e}")
            return []
    
    async def update_document(self, document_id: str, update_data: Dict[str, Any]) -> bool:
        """Update document metadata"""
        try:
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                update_data["updated_at"] = datetime.utcnow()
                result = await collection.update_one(
                    {"document_id": document_id},
                    {"$set": update_data}
                )
                return result.modified_count > 0
            else:
                documents = self._load_local_documents()
                for i, doc in enumerate(documents):
                    if doc.get("document_id") == document_id or doc.get("_id") == document_id:
                        update_data["updated_at"] = datetime.utcnow().isoformat()
                        documents[i].update(update_data)
                        return self._save_local_documents(documents)
                return False
        except Exception as e:
            logger.error(f"❌ Failed to update document {document_id}: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """Delete document record"""
        try:
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                result = await collection.delete_one({"document_id": document_id})
                return result.deleted_count > 0
            else:
                documents = self._load_local_documents()
                original_count = len(documents)
                documents = [doc for doc in documents 
                           if doc.get("document_id") != document_id and doc.get("_id") != document_id]
                if len(documents) < original_count:
                    return self._save_local_documents(documents)
                return False
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id}: {e}")
            return False

class ConversationRepository:
    """Repository for conversation history operations"""
    
    def __init__(self):
        self.collection_name = "conversations"
        self.local_file = LOCAL_STORAGE_PATH / "conversations.json"
    
    def _load_local_conversations(self) -> List[Dict[str, Any]]:
        """Load conversations from local storage"""
        if self.local_file.exists():
            try:
                with open(self.local_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load local conversations: {e}")
        return []
    
    def _save_local_conversations(self, conversations: List[Dict[str, Any]]) -> bool:
        """Save conversations to local storage"""
        try:
            with open(self.local_file, 'w', encoding='utf-8') as f:
                json.dump(conversations, f, indent=2, default=str)
            return True
        except Exception as e:
            logger.error(f"Failed to save local conversations: {e}")
            return False
    
    async def create_conversation(self, device_id: str, session_id: str) -> str:
        """Create a new conversation"""
        try:
            conversation_data = {
                "device_id": device_id,
                "session_id": session_id,
                "messages": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                result = await collection.insert_one(conversation_data)
                return str(result.inserted_id)
            else:
                conversations = self._load_local_conversations()
                conversation_id = f"conv_{len(conversations) + 1}_{int(datetime.utcnow().timestamp())}"
                conversation_data["_id"] = conversation_id
                conversation_data["created_at"] = conversation_data["created_at"].isoformat()
                conversation_data["updated_at"] = conversation_data["updated_at"].isoformat()
                conversations.append(conversation_data)
                
                if self._save_local_conversations(conversations):
                    return conversation_id
                else:
                    raise Exception("Failed to save conversation to local storage")
        except Exception as e:
            logger.error(f"❌ Failed to create conversation: {e}")
            raise
    
    async def add_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add message to conversation"""
        try:
            message["timestamp"] = datetime.utcnow()
            
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                result = await collection.update_one(
                    {"session_id": session_id},
                    {
                        "$push": {"messages": message},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                return result.modified_count > 0
            else:
                conversations = self._load_local_conversations()
                for conv in conversations:
                    if conv.get("session_id") == session_id:
                        message["timestamp"] = message["timestamp"].isoformat()
                        conv["messages"].append(message)
                        conv["updated_at"] = datetime.utcnow().isoformat()
                        return self._save_local_conversations(conversations)
                return False
        except Exception as e:
            logger.error(f"❌ Failed to add message to conversation {session_id}: {e}")
            return False
    
    async def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by session ID"""
        try:
            if mongodb.database is not None:
                collection = mongodb.database[self.collection_name]
                conversation = await collection.find_one({"session_id": session_id})
                return serialize_document(conversation) if conversation else None
            else:
                conversations = self._load_local_conversations()
                for conv in conversations:
                    if conv.get("session_id") == session_id:
                        return conv
                return None
        except Exception as e:
            logger.error(f"❌ Failed to get conversation {session_id}: {e}")
            return None

# Global repository instances
document_repo = DocumentRepository()
conversation_repo = ConversationRepository()