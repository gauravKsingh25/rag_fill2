from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import uuid
import logging
import re

from app.models import ChatRequest, ChatResponse, ChatMessage, FactVerificationRequest, FactVerificationResponse
from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from app.database import conversation_repo
from app.routers.devices import get_device

# Import enhanced RAG accuracy system
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from enhanced_rag_accuracy import EnhancedRAGSystem, ENHANCED_CONFIG, initialize_enhanced_rag
    from rag_accuracy_config import ACCURACY_CONFIG, AccuracyMetrics
    ENHANCED_RAG_AVAILABLE = True
except ImportError:
    # Fallback values if enhanced config not found
    class FallbackConfig:
        MIN_CONFIDENCE_HIGH = 0.8
        MIN_CONFIDENCE_GOOD = 0.7
        MIN_CONFIDENCE_MODERATE = 0.6
    
    ACCURACY_CONFIG = FallbackConfig()
    ENHANCED_RAG_AVAILABLE = False
    
    class AccuracyMetrics:
        @staticmethod
        def get_confidence_level(score):
            return "HIGH" if score >= 0.8 else "GOOD" if score >= 0.7 else "MODERATE"

# Global enhanced RAG system
enhanced_rag_system = None

router = APIRouter()
logger = logging.getLogger(__name__)

def format_user_friendly_response(response_text: str, sources: List[Dict[str, Any]]) -> str:
    """Format the RAG response to be more user-friendly"""
    
    # Clean up technical formatting
    formatted = response_text
    
    # Remove excessive technical metadata
    formatted = re.sub(r'📊 COMPREHENSIVE ANALYSIS SUMMARY:.*$', '', formatted, flags=re.MULTILINE | re.DOTALL)
    formatted = re.sub(r'📊 ANALYSIS SUMMARY:.*$', '', formatted, flags=re.MULTILINE | re.DOTALL)
    
    # Clean up confidence indicators to be more natural
    formatted = formatted.replace('🎯 HIGH CONFIDENCE:', '✅ **Based on reliable sources:**')
    formatted = formatted.replace('✅ GOOD CONFIDENCE:', '✅ **From available documents:**')
    formatted = formatted.replace('⚠️ MODERATE CONFIDENCE:', '⚠️ **Based on limited information:**')
    
    # Make document references cleaner
    formatted = re.sub(r'\[Document (\d+)\]', r'*(Document \1)*', formatted)
    
    # Remove excessive newlines and clean up formatting
    formatted = re.sub(r'\n{3,}', '\n\n', formatted)
    formatted = re.sub(r'\*{2,}', '**', formatted)
    
    # Add a simple source summary if sources exist
    if sources and len(sources) > 0:
        source_summary = f"\n\n**📋 Source Summary:**\nBased on {len(sources)} document(s)"
        if len(sources) <= 3:
            doc_names = [s.get('filename', 'Unknown') for s in sources[:3]]
            source_summary += f": {', '.join(set(doc_names))}"
        formatted += source_summary
    
    return formatted.strip()

@router.post("/", response_model=ChatResponse)
async def chat_with_device(request: ChatRequest):
    """Chat with a specific device's knowledge base with enhanced comprehensive accuracy"""
    try:
        # Verify device exists
        await get_device(request.device_id)
        
        # Initialize enhanced RAG system if available and not already initialized
        global enhanced_rag_system
        if ENHANCED_RAG_AVAILABLE and enhanced_rag_system is None:
            enhanced_rag_system = await initialize_enhanced_rag(gemini_service, pinecone_service)
        
        # Use simplified approach for faster responses instead of enhanced RAG
        # if ENHANCED_RAG_AVAILABLE and enhanced_rag_system is not None:
        if False:  # Temporarily disable enhanced RAG for speed
            logger.info(f"🚀 Using enhanced RAG system for comprehensive analysis")
            
            # Process query with comprehensive document analysis
            comprehensive_result = await enhanced_rag_system.process_query_comprehensively(
                query=request.message,
                device_id=request.device_id
            )
            
            response_text = comprehensive_result["response"]
            sources = comprehensive_result["sources"]
            
            # Add comprehensive analysis metadata to response
            if comprehensive_result.get("quality_metrics"):
                quality_info = comprehensive_result["quality_metrics"]
                logger.info(f"📊 Analysis Quality: {quality_info.get('analysis_quality', 'UNKNOWN')}")
                logger.info(f"📈 Documents Analyzed: {quality_info.get('total_documents_analyzed', 0)}")
                logger.info(f"🎯 Average Confidence: {quality_info.get('average_confidence', 0):.3f}")
            
        else:
            # Fallback to enhanced standard approach
            logger.info(f"📝 Using enhanced standard RAG approach")
            
            # Generate embedding for user query
            query_embedding = await gemini_service.get_embedding(request.message)
            
            # Enhanced retrieval: Get more chunks for better coverage but not too many
            search_results = await pinecone_service.search_vectors(
                query_vector=query_embedding,
                device_id=request.device_id,
                top_k=15  # Reduced for faster response
            )
            
            # Apply enhanced filtering with more lenient confidence thresholds for better coverage
            MIN_CONFIDENCE_SCORE = 0.65 if ENHANCED_RAG_AVAILABLE else ACCURACY_CONFIG.MIN_CONFIDENCE_GOOD
            filtered_results = [result for result in search_results if result.score >= MIN_CONFIDENCE_SCORE]
            
            # If no high-confidence results, apply more lenient threshold
            if not filtered_results and search_results:
                MIN_CONFIDENCE_SCORE = 0.55 if ENHANCED_RAG_AVAILABLE else ACCURACY_CONFIG.MIN_CONFIDENCE_MODERATE
                filtered_results = [result for result in search_results if result.score >= MIN_CONFIDENCE_SCORE]
            
            # If still no results, use even more lenient threshold but prioritize content quality
            if not filtered_results and search_results:
                MIN_CONFIDENCE_SCORE = 0.45
                filtered_results = [result for result in search_results if result.score >= MIN_CONFIDENCE_SCORE]
            
            # Take fewer results for faster processing
            filtered_results = filtered_results[:10]  # Reduced from 20 to 10
            
            # Extract context from search results with enhanced metadata
            context_docs = []
            sources = []
            
            for i, result in enumerate(filtered_results):
                # Use clean content without document numbering for better AI processing
                context_docs.append(result.content)
                
                sources.append({
                    "document_number": i + 1,
                    "filename": result.metadata.get("filename", "Unknown"),
                    "chunk_id": result.metadata.get("chunk_id", 0),
                    "score": result.score,
                    "confidence_level": AccuracyMetrics.get_confidence_level(result.score),
                    "document_id": result.metadata.get("document_id", "Unknown"),
                    "content_preview": result.content[:200] + "..." if len(result.content) > 200 else result.content
                })
            
            # Generate comprehensive response using enhanced settings
            if context_docs:
                logger.info(f"✅ Found {len(context_docs)} documents for comprehensive analysis")
                
                # Create enhanced prompt that properly uses context for general questions
                enhanced_prompt = f"""You are a helpful AI assistant analyzing medical device documentation. Answer the user's question using the information provided below.

User Question: "{request.message}"

Available Information:
{chr(10).join(context_docs)}

Instructions:
- If asked to summarize: Provide a comprehensive overview covering key aspects from all documents
- If asked specific questions: Give precise answers using the document information
- If asked about features: List and explain the main capabilities and specifications
- Write naturally and conversationally as if explaining to a colleague
- Include relevant details that help answer the question completely
- If information is missing, clearly state what's not available
- Be direct and helpful

Answer:"""
                
                response_text = await gemini_service.generate_response(
                    prompt=enhanced_prompt,
                    context=None,  # Context is already in the prompt
                    temperature=0.2,  # Higher for more natural responses
                    max_tokens=2000   # Allow longer responses for summaries
                )
                
                # Add simple analysis summary
                avg_confidence = sum(r["score"] for r in sources) / len(sources) if sources else 0
                high_conf_count = sum(1 for r in sources if r["score"] >= 0.8)
                
                # Format response for better user experience
                response_text = format_user_friendly_response(response_text, sources)
                
            else:
                logger.warning(f"❌ No relevant documents found for comprehensive analysis: {request.message}")
                response_text = f"""❌ NO RELEVANT INFORMATION FOUND

I performed a comprehensive search of all available documents for device {request.device_id} but could not find relevant information to answer your question: "{request.message}"

This could mean:
1. The information is not available in the uploaded documents
2. The documents don't contain content related to your query
3. You may need to upload more relevant documents
4. Try rephrasing your question with different keywords

To get better results:
- Upload documents that specifically contain information about your question
- Use specific terms that might appear in technical documents
- Try breaking complex questions into simpler parts

Please upload relevant documents and try again."""
        
        # Create session ID for conversation tracking
        session_id = str(uuid.uuid4())
        
        # Store conversation with enhanced metadata
        try:
            await conversation_repo.add_message(session_id, {
                "role": "user",
                "content": request.message,
                "timestamp": logger.info.__name__,
                "enhanced_rag": ENHANCED_RAG_AVAILABLE,
                "comprehensive_analysis": True
            })
            await conversation_repo.add_message(session_id, {
                "role": "assistant", 
                "content": response_text,
                "sources_count": len(sources),
                "enhanced_rag": ENHANCED_RAG_AVAILABLE
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
async def search_device_knowledge(device_id: str, query: str, top_k: int = 15, min_score: float = 0.65):
    """Search device knowledge base with comprehensive filtering and enhanced accuracy"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Use enhanced RAG system if available for search
        if ENHANCED_RAG_AVAILABLE and enhanced_rag_system is not None:
            logger.info(f"🔍 Using enhanced comprehensive search")
            
            # Use comprehensive retrieval for search
            documents, retrieval_stats = await enhanced_rag_system.retriever.comprehensive_retrieval(
                query=query,
                device_id=device_id
            )
            
            # Format enhanced results
            results = []
            for i, result in enumerate(documents[:top_k]):
                results.append({
                    "document_number": i + 1,
                    "content": result.content,
                    "filename": result.metadata.get("filename", "Unknown"),
                    "chunk_id": result.metadata.get("chunk_id", 0),
                    "confidence_score": result.score,
                    "confidence_level": AccuracyMetrics.get_confidence_level(result.score),
                    "document_id": result.metadata.get("document_id", "Unknown"),
                    "relevance_tier": "PRIMARY" if result.score >= 0.85 else "SECONDARY" if result.score >= 0.75 else "SUPPORTING"
                })
            
            # Enhanced search quality metrics
            avg_confidence = sum(r["confidence_score"] for r in results) / len(results) if results else 0
            high_confidence_count = sum(1 for r in results if r["confidence_score"] >= 0.8)
            critical_confidence_count = sum(1 for r in results if r["confidence_score"] >= 0.85)
            
            return {
                "device_id": device_id,
                "query": query,
                "results_count": len(results),
                "retrieval_method": "comprehensive",
                "query_variations_used": retrieval_stats.get("query_variations", 1),
                "total_candidates_analyzed": retrieval_stats.get("total_retrieved", len(results)),
                "avg_confidence": round(avg_confidence, 3),
                "high_confidence_results": high_confidence_count,
                "critical_confidence_results": critical_confidence_count,
                "search_quality": "EXCELLENT" if avg_confidence >= 0.8 else "VERY_GOOD" if avg_confidence >= 0.75 else "GOOD" if avg_confidence >= 0.7 else "MODERATE",
                "recommendation": "High-quality comprehensive results" if avg_confidence >= 0.8 else "Good results with comprehensive analysis" if avg_confidence >= 0.7 else "Moderate results - consider uploading more relevant documents",
                "results": results
            }
        
        else:
            # Enhanced standard search approach
            logger.info(f"🔍 Using enhanced standard search")
            
            # Generate embedding for search query
            query_embedding = await gemini_service.get_embedding(query)
            
            # Search vectors with higher retrieval count for comprehensive coverage
            search_results = await pinecone_service.search_vectors(
                query_vector=query_embedding,
                device_id=device_id,
                top_k=top_k * 2  # Get more results to filter comprehensively
            )
            
            # Apply enhanced filtering with better confidence thresholds
            filtered_results = [result for result in search_results if result.score >= min_score]
            
            # Sort by score and take requested count
            filtered_results = sorted(filtered_results, key=lambda x: x.score, reverse=True)[:top_k]
            
            # Format results with enhanced metadata
            results = []
            for i, result in enumerate(filtered_results):
                results.append({
                    "document_number": i + 1,
                    "content": result.content,
                    "filename": result.metadata.get("filename", "Unknown"),
                    "chunk_id": result.metadata.get("chunk_id", 0),
                    "confidence_score": result.score,
                    "confidence_level": AccuracyMetrics.get_confidence_level(result.score),
                    "document_id": result.metadata.get("document_id", "Unknown"),
                    "relevance_tier": "PRIMARY" if result.score >= 0.8 else "SECONDARY" if result.score >= 0.7 else "SUPPORTING"
                })
            
            # Calculate enhanced search quality metrics
            avg_confidence = sum(r["confidence_score"] for r in results) / len(results) if results else 0
            high_confidence_count = sum(1 for r in results if r["confidence_score"] >= 0.8)
            
            return {
                "device_id": device_id,
                "query": query,
                "results_count": len(results),
                "retrieval_method": "enhanced_standard",
                "total_candidates": len(search_results),
                "avg_confidence": round(avg_confidence, 3),
                "high_confidence_results": high_confidence_count,
                "search_quality": "EXCELLENT" if avg_confidence >= 0.8 else "GOOD" if avg_confidence >= 0.7 else "MODERATE",
                "recommendation": "High-quality results available" if avg_confidence >= 0.8 else "Good results found" if avg_confidence >= 0.7 else "Consider uploading more relevant documents for better results",
                "results": results
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to search device knowledge: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search device knowledge: {e}")

@router.post("/verify-fact", response_model=FactVerificationResponse)
async def verify_fact_with_documents(request: FactVerificationRequest):
    """Verify a specific fact or claim against the device's knowledge base"""
    try:
        # Verify device exists
        await get_device(request.device_id)
        
        # Generate embedding for the claim
        claim_embedding = await gemini_service.get_embedding(request.claim)
        
        # Search for supporting or contradicting evidence
        search_results = await pinecone_service.search_vectors(
            query_vector=claim_embedding,
            device_id=request.device_id,
            top_k=10
        )
        
        # Filter high-confidence results only
        high_confidence_results = [result for result in search_results if result.score >= 0.75]
        
        if not high_confidence_results:
            return FactVerificationResponse(
                device_id=request.device_id,
                claim=request.claim,
                verification_status="INSUFFICIENT_DATA",
                verification_result="No high-confidence documents found to verify this claim.",
                evidence_count=0,
                avg_confidence=0.0,
                evidence=[]
            )
        
        # Create verification prompt
        evidence_chunks = [f"EVIDENCE {i+1}:\n{result.content}" for i, result in enumerate(high_confidence_results)]
        verification_prompt = f"""FACT VERIFICATION TASK

CLAIM TO VERIFY: "{request.claim}"

AVAILABLE EVIDENCE:
{chr(10).join(evidence_chunks)}

VERIFICATION INSTRUCTIONS:
1. Determine if the claim is SUPPORTED, CONTRADICTED, or PARTIALLY_SUPPORTED by the evidence
2. Quote EXACT text from evidence that supports or contradicts the claim
3. If no relevant evidence exists, state "NO_EVIDENCE_FOUND"
4. Do NOT make inferences - only use explicit statements in the evidence
5. Be precise about which evidence chunk supports your conclusion

VERIFICATION RESULT:
Status: [SUPPORTED/CONTRADICTED/PARTIALLY_SUPPORTED/NO_EVIDENCE_FOUND]
Evidence: [Exact quotes with chunk numbers]
Explanation: [Brief factual explanation]"""
        
        verification_result = await gemini_service.generate_response(
            prompt=verification_prompt,
            context=None,  # Context already in prompt
            temperature=0.05  # Extremely low for accuracy
        )
        
        # Parse verification status
        status = "UNKNOWN"
        if "SUPPORTED" in verification_result:
            status = "SUPPORTED" if "CONTRADICTED" not in verification_result else "PARTIALLY_SUPPORTED"
        elif "CONTRADICTED" in verification_result:
            status = "CONTRADICTED"
        elif "NO_EVIDENCE_FOUND" in verification_result:
            status = "NO_EVIDENCE_FOUND"
        
        # Format evidence
        evidence = []
        for result in high_confidence_results:
            evidence.append({
                "filename": result.metadata.get("filename", "Unknown"),
                "content": result.content,
                "confidence_score": result.score,
                "document_id": result.metadata.get("document_id", "Unknown")
            })
        
        return FactVerificationResponse(
            device_id=request.device_id,
            claim=request.claim,
            verification_status=status,
            verification_result=verification_result,
            evidence_count=len(evidence),
            avg_confidence=sum(e["confidence_score"] for e in evidence) / len(evidence) if evidence else 0,
            evidence=evidence[:5]  # Top 5 evidence pieces
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to verify fact: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify fact: {e}")
