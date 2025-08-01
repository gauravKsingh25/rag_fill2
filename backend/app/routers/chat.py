from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import uuid
import logging

from app.models import ChatRequest, ChatResponse, ChatMessage
from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from app.database import conversation_repo
from app.routers.devices import get_device

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=ChatResponse)
async def chat_with_device(request: ChatRequest):
    """Chat with a specific device's knowledge base"""
    try:
        # Verify device exists
        await get_device(request.device_id)
        
        # Generate embedding for user query
        query_embedding = await gemini_service.get_embedding(request.message)
        
        # Search for relevant context in device's knowledge base
        search_results = await pinecone_service.search_vectors(
            query_vector=query_embedding,
            device_id=request.device_id,
            top_k=5
        )
        
        # Extract context from search results
        context_docs = []
        sources = []
        
        for result in search_results:
            context_docs.append(result.content)
            sources.append({
                "filename": result.metadata.get("filename", "Unknown"),
                "chunk_id": result.metadata.get("chunk_id", 0),
                "score": result.score,
                "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content
            })
        
        # Generate response using Gemini with context
        if context_docs:
            response_text = await gemini_service.generate_response(
                prompt=request.message,
                context=context_docs,
                temperature=0.7
            )
        else:
            response_text = await gemini_service.generate_response(
                prompt=f"I don't have any relevant information in my knowledge base to answer your question: '{request.message}'. Please upload relevant documents for this device ({request.device_id}) first.",
                temperature=0.5
            )
        
        # Create session ID if not in conversation history
        session_id = str(uuid.uuid4())
        
        # Store conversation (optional - can be enabled/disabled)
        try:
            await conversation_repo.add_message(session_id, {
                "role": "user",
                "content": request.message
            })
            await conversation_repo.add_message(session_id, {
                "role": "assistant", 
                "content": response_text
            })
        except Exception as e:
            logger.warning(f"⚠️ Failed to store conversation: {e}")
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            device_id=request.device_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to process chat request: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process chat request: {e}")

@router.get("/history/{session_id}")
async def get_conversation_history(session_id: str):
    """Get conversation history by session ID"""
    try:
        conversation = await conversation_repo.get_conversation(session_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "session_id": session_id,
            "device_id": conversation["device_id"],
            "messages": conversation["messages"],
            "created_at": conversation["created_at"],
            "updated_at": conversation["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get conversation history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get conversation history: {e}")

@router.post("/search")
async def search_device_knowledge(device_id: str, query: str, top_k: int = 5):
    """Search device knowledge base directly"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Generate embedding for search query
        query_embedding = await gemini_service.get_embedding(query)
        
        # Search vectors
        search_results = await pinecone_service.search_vectors(
            query_vector=query_embedding,
            device_id=device_id,
            top_k=top_k
        )
        
        # Format results
        results = []
        for result in search_results:
            results.append({
                "content": result.content,
                "filename": result.metadata.get("filename", "Unknown"),
                "chunk_id": result.metadata.get("chunk_id", 0),
                "score": result.score,
                "document_id": result.metadata.get("document_id", "Unknown")
            })
        
        return {
            "device_id": device_id,
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to search device knowledge: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search device knowledge: {e}")
