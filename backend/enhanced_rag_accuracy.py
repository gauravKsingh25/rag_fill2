#!/usr/bin/env python3
"""
Enhanced RAG Accuracy System - Comprehensive Document Analysis

This module implements enhanced RAG accuracy with comprehensive document retrieval,
multi-query analysis, and detailed fact-based responses that consider ALL relevant documents.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
import json
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class EnhancedRAGConfig:
    """Enhanced configuration for maximum RAG accuracy"""
    
    # Optimized retrieval settings for faster response
    INITIAL_RETRIEVAL_COUNT: int = 15      # Reduced for faster response
    MULTI_QUERY_COUNT: int = 3             # Reduced for speed
    FINAL_CONTEXT_COUNT: int = 10          # Reduced for speed
    
    # Adjusted confidence thresholds for better coverage
    MIN_CONFIDENCE_CRITICAL: float = 0.80   # Critical information threshold (lowered)
    MIN_CONFIDENCE_HIGH: float = 0.70       # High confidence threshold (lowered)
    MIN_CONFIDENCE_ACCEPTABLE: float = 0.55 # Minimum acceptable threshold (lowered)
    
    # Multi-stage retrieval settings
    ENABLE_QUERY_EXPANSION: bool = True     # Expand queries for better coverage
    ENABLE_SEMANTIC_CLUSTERING: bool = True # Group similar content
    ENABLE_CROSS_REFERENCE: bool = True    # Cross-reference information
    
    # Response generation settings
    TEMPERATURE_FACTUAL: float = 0.02      # Even lower for maximum facts accuracy
    TEMPERATURE_SYNTHESIS: float = 0.03    # Very low for information synthesis
    MAX_RESPONSE_TOKENS: int = 2500        # Allow longer, more comprehensive responses
    
    # Quality assurance settings
    REQUIRE_MULTIPLE_SOURCES: bool = True  # Verify facts across sources
    ENABLE_FACT_CROSS_CHECK: bool = True   # Cross-check conflicting information
    CITATION_REQUIREMENT: bool = True      # Always provide source citations

# Global enhanced configuration
ENHANCED_CONFIG = EnhancedRAGConfig()

class ComprehensiveDocumentRetriever:
    """Enhanced document retrieval with multi-query and comprehensive analysis"""
    
    def __init__(self, gemini_service, pinecone_service):
        self.gemini_service = gemini_service
        self.pinecone_service = pinecone_service
    
    async def generate_query_variations(self, original_query: str) -> List[str]:
        """Generate multiple query variations for comprehensive retrieval"""
        try:
            if not self.gemini_service.available:
                # Fallback query variations
                return self._generate_fallback_variations(original_query)
            
            prompt = f"""Generate {ENHANCED_CONFIG.MULTI_QUERY_COUNT} comprehensive query variations to ensure maximum document retrieval coverage. Create variations that approach the topic from different angles, use different terminology, and consider various ways information might be expressed.

Original Query: "{original_query}"

VARIATION REQUIREMENTS:
1. Each variation should use different keywords and terminology
2. Include technical terms, synonyms, and related concepts
3. Consider different question formats (what, how, where, when, which, describe, explain, etc.)
4. Think about how information might be stored in different document types
5. Include both specific and general approaches to the topic
6. Consider abbreviations, full forms, and alternative names
7. Include variations that might capture peripheral but relevant information
8. Make sure each variation could potentially find different relevant documents

EXAMPLES of good variations for "What is the model number?":
- "model number", "product model", "device model", "model designation", "model identifier"
- "What model is this device?", "Which model?", "Device model information", "Model specifications"
- "model", "product number", "part number", "catalog number", "reference number"

Generate exactly {ENHANCED_CONFIG.MULTI_QUERY_COUNT} variations as a JSON list of strings:

Query Variations:"""

            response = await self.gemini_service.generate_response(
                prompt=prompt,
                context=None,
                temperature=0.3,
                max_tokens=500
            )
            
            try:
                variations = json.loads(response)
                if isinstance(variations, list) and len(variations) >= 3:
                    return [original_query] + variations[:ENHANCED_CONFIG.MULTI_QUERY_COUNT-1]
                else:
                    return self._generate_fallback_variations(original_query)
            except json.JSONDecodeError:
                return self._generate_fallback_variations(original_query)
                
        except Exception as e:
            logger.error(f"❌ Failed to generate query variations: {e}")
            return self._generate_fallback_variations(original_query)
    
    def _generate_fallback_variations(self, original_query: str) -> List[str]:
        """Generate fallback query variations when AI is not available"""
        base_query = original_query.lower()
        variations = [original_query]
        
        # Add keyword-based variations
        if "what" in base_query:
            variations.append(original_query.replace("what", "which"))
            variations.append(f"Find information about {original_query.replace('what is', '').replace('what are', '')}")
            variations.append(f"Details on {original_query.replace('what is', '').replace('what are', '')}")
        
        # Add specific vs general variations
        if "device" in base_query:
            variations.append(original_query.replace("device", "product"))
            variations.append(original_query.replace("device", "equipment"))
            variations.append(original_query.replace("device", "system"))
        
        # Add question type variations
        if "?" in original_query:
            variations.append(f"Information about {original_query.replace('?', '')}")
            variations.append(f"Details on {original_query.replace('?', '')}")
            variations.append(f"Describe {original_query.replace('?', '')}")
        
        # Add technical variations
        variations.append(f"Technical specifications for {original_query}")
        variations.append(f"Documentation about {original_query}")
        
        # Remove duplicates and return requested count
        seen = set()
        unique_variations = []
        for var in variations:
            if var.lower() not in seen:
                seen.add(var.lower())
                unique_variations.append(var)
        
        return unique_variations[:ENHANCED_CONFIG.MULTI_QUERY_COUNT]
    
    async def comprehensive_retrieval(
        self, 
        query: str, 
        device_id: str
    ) -> Tuple[List[Any], Dict[str, Any]]:
        """Perform comprehensive document retrieval with multi-query approach"""
        try:
            # Step 1: Generate query variations
            query_variations = await self.generate_query_variations(query)
            logger.info(f"🔍 Generated {len(query_variations)} query variations for comprehensive retrieval")
            
            # Step 2: Retrieve documents for each query variation
            all_results = []
            query_stats = {}
            
            for i, query_var in enumerate(query_variations):
                logger.info(f"🔍 Processing query variation {i+1}: {query_var}")
                
                # Generate embedding for this query variation
                query_embedding = await self.gemini_service.get_embedding(query_var)
                
                # Retrieve more documents than usual
                search_results = await self.pinecone_service.search_vectors(
                    query_vector=query_embedding,
                    device_id=device_id,
                    top_k=ENHANCED_CONFIG.INITIAL_RETRIEVAL_COUNT
                )
                
                query_stats[f"query_{i+1}"] = {
                    "query": query_var,
                    "results_count": len(search_results),
                    "avg_score": sum(r.score for r in search_results) / len(search_results) if search_results else 0
                }
                
                all_results.extend(search_results)
            
            # Step 3: Remove duplicates and merge results
            unique_results = self._deduplicate_results(all_results)
            
            # Step 4: Apply comprehensive filtering
            filtered_results = self._apply_comprehensive_filtering(unique_results, query)
            
            # Step 5: Sort by relevance and confidence
            final_results = sorted(
                filtered_results, 
                key=lambda x: x.score, 
                reverse=True
            )[:ENHANCED_CONFIG.FINAL_CONTEXT_COUNT]
            
            # Step 6: Prepare statistics
            retrieval_stats = {
                "original_query": query,
                "query_variations": len(query_variations),
                "total_retrieved": len(all_results),
                "unique_results": len(unique_results),
                "final_context_count": len(final_results),
                "query_details": query_stats,
                "confidence_breakdown": self._analyze_confidence_distribution(final_results)
            }
            
            logger.info(f"✅ Comprehensive retrieval complete: {len(final_results)} high-quality documents selected")
            
            return final_results, retrieval_stats
            
        except Exception as e:
            logger.error(f"❌ Comprehensive retrieval failed: {e}")
            # Fallback to standard retrieval
            return await self._fallback_retrieval(query, device_id)
    
    def _deduplicate_results(self, results: List[Any]) -> List[Any]:
        """Remove duplicate documents based on content similarity"""
        unique_results = []
        seen_content = set()
        
        for result in results:
            # Create a hash of the content for deduplication
            content_hash = hash(result.content[:200])  # Use first 200 chars for deduplication
            
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_results.append(result)
        
        return unique_results
    
    def _apply_comprehensive_filtering(self, results: List[Any], original_query: str) -> List[Any]:
        """Apply comprehensive filtering to ensure high-quality results"""
        filtered_results = []
        
        for result in results:
            # Filter 1: More lenient minimum confidence threshold for comprehensive coverage
            if result.score < ENHANCED_CONFIG.MIN_CONFIDENCE_ACCEPTABLE:
                continue
            
            # Filter 2: Basic content quality check (less strict)
            if not self._is_content_high_quality(result.content):
                continue
            
            # Filter 3: Relaxed relevance check to capture more potentially useful information
            if not self._is_relevant_to_query(result.content, original_query):
                continue
            
            filtered_results.append(result)
        
        return filtered_results
    
    def _is_content_high_quality(self, content: str) -> bool:
        """Check if content meets quality standards - more permissive for comprehensive coverage"""
        # More lenient quality checks to capture more potentially useful information
        content = content.strip()
        
        if len(content) < 10:  # Too short (reduced from 20)
            return False
        
        if len(content.split()) < 2:  # Too few words (reduced from 5)
            return False
        
        # More lenient check for garbled text
        special_char_ratio = sum(1 for c in content if not c.isalnum() and not c.isspace() and c not in '.,;:-()[]{}|/') / len(content)
        if special_char_ratio > 0.5:  # More than 50% non-standard special characters
            return False
        
        # Accept structured content and table data as potentially useful
        if '[STRUCTURED_CONTENT]' in content or '[TABLE DATA]' in content:
            return True
        
        return True
    
    def _is_relevant_to_query(self, content: str, query: str) -> bool:
        """Check if content is relevant to the query - more lenient approach"""
        # Simple keyword-based relevance check with more leniency
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        # Remove common stop words for better matching
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should"}
        query_words = query_words - stop_words
        content_words = content_words - stop_words
        
        # Check for keyword overlap - more lenient threshold
        overlap = len(query_words.intersection(content_words))
        overlap_ratio = overlap / len(query_words) if query_words else 0
        
        # Accept if there's any reasonable keyword overlap or if content is substantial
        return overlap_ratio > 0.05 or len(content.split()) > 50  # 5% overlap or substantial content
    
    def _analyze_confidence_distribution(self, results: List[Any]) -> Dict[str, int]:
        """Analyze confidence score distribution"""
        distribution = {
            "critical": 0,
            "high": 0,
            "acceptable": 0,
            "low": 0
        }
        
        for result in results:
            if result.score >= ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL:
                distribution["critical"] += 1
            elif result.score >= ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH:
                distribution["high"] += 1
            elif result.score >= ENHANCED_CONFIG.MIN_CONFIDENCE_ACCEPTABLE:
                distribution["acceptable"] += 1
            else:
                distribution["low"] += 1
        
        return distribution
    
    async def _fallback_retrieval(self, query: str, device_id: str) -> Tuple[List[Any], Dict[str, Any]]:
        """Fallback retrieval method when comprehensive retrieval fails"""
        try:
            query_embedding = await self.gemini_service.get_embedding(query)
            search_results = await self.pinecone_service.search_vectors(
                query_vector=query_embedding,
                device_id=device_id,
                top_k=ENHANCED_CONFIG.INITIAL_RETRIEVAL_COUNT
            )
            
            stats = {
                "fallback_mode": True,
                "results_count": len(search_results),
                "method": "standard_retrieval"
            }
            
            return search_results, stats
            
        except Exception as e:
            logger.error(f"❌ Fallback retrieval failed: {e}")
            return [], {"error": str(e)}

class ComprehensiveResponseGenerator:
    """Enhanced response generation with comprehensive analysis"""
    
    def __init__(self, gemini_service):
        self.gemini_service = gemini_service
    
    async def generate_comprehensive_response(
        self,
        query: str,
        documents: List[Any],
        retrieval_stats: Dict[str, Any],
        device_id: str
    ) -> str:
        """Generate comprehensive, detailed response using all relevant documents"""
        try:
            if not self.gemini_service.available:
                return self._generate_fallback_response(query, documents, device_id)
            
            # Prepare comprehensive context
            context_sections = self._organize_documents_by_relevance(documents)
            
            # Create enhanced prompt for comprehensive analysis
            prompt = self._create_comprehensive_prompt(
                query=query,
                context_sections=context_sections,
                retrieval_stats=retrieval_stats,
                device_id=device_id
            )
            
            # Generate response with enhanced settings
            response = await self.gemini_service.generate_response(
                prompt=prompt,
                context=None,  # Context already in prompt
                temperature=ENHANCED_CONFIG.TEMPERATURE_FACTUAL,
                max_tokens=ENHANCED_CONFIG.MAX_RESPONSE_TOKENS
            )
            
            # Post-process response for quality
            enhanced_response = self._enhance_response_quality(response, documents)
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"❌ Comprehensive response generation failed: {e}")
            return self._generate_fallback_response(query, documents, device_id)
    
    def _organize_documents_by_relevance(self, documents: List[Any]) -> Dict[str, List[str]]:
        """Organize documents by relevance tiers"""
        sections = {
            "critical_confidence": [],
            "high_confidence": [],
            "acceptable_confidence": []
        }
        
        for i, doc in enumerate(documents):
            content_with_id = f"[Document {i+1}] {doc.content}"
            
            if doc.score >= ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL:
                sections["critical_confidence"].append(content_with_id)
            elif doc.score >= ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH:
                sections["high_confidence"].append(content_with_id)
            else:
                sections["acceptable_confidence"].append(content_with_id)
        
        return sections
    
    def _create_comprehensive_prompt(
        self,
        query: str,
        context_sections: Dict[str, List[str]],
        retrieval_stats: Dict[str, Any],
        device_id: str
    ) -> str:
        """Create comprehensive prompt for detailed analysis"""
        
        # Build context sections
        critical_docs = "\n\n".join(context_sections["critical_confidence"])
        high_conf_docs = "\n\n".join(context_sections["high_confidence"])
        acceptable_docs = "\n\n".join(context_sections["acceptable_confidence"])
        
        prompt = f"""You are an expert document analysis system. Your task is to provide a comprehensive, detailed, and accurate response based on ALL available document evidence. You MUST analyze every single document provided and extract all relevant information.

ANALYSIS TASK: "{query}"

COMPREHENSIVE DOCUMENT EVIDENCE (ANALYZE ALL OF THESE):

=== CRITICAL CONFIDENCE DOCUMENTS (Score ≥ 0.80) ===
{critical_docs if critical_docs else "No critical confidence documents found."}

=== HIGH CONFIDENCE DOCUMENTS (Score ≥ 0.70) ===
{high_conf_docs if high_conf_docs else "No high confidence documents found."}

=== ACCEPTABLE CONFIDENCE DOCUMENTS (Score ≥ 0.55) ===
{acceptable_docs if acceptable_docs else "No acceptable confidence documents found."}

RETRIEVAL STATISTICS:
- Total documents to analyze: {retrieval_stats.get('final_context_count', 0)}
- Query variations used: {retrieval_stats.get('query_variations', 1)}
- Device: {device_id}

MANDATORY COMPREHENSIVE ANALYSIS INSTRUCTIONS:

1. **EXAMINE EVERY DOCUMENT**: You must analyze ALL provided documents thoroughly - do not skip any document
2. **EXTRACT ALL RELEVANT INFORMATION**: Find every piece of information that relates to the query, even tangentially
3. **COMPREHENSIVE COVERAGE**: Address every aspect of the query found in ANY document
4. **SYNTHESIZE ACROSS SOURCES**: Combine information from multiple documents to provide complete answers
5. **DETAILED CITATIONS**: Reference specific documents when presenting each fact: [Document X]
6. **NO INFORMATION LEFT BEHIND**: If a document contains relevant information, include it in your response
7. **ORGANIZE SYSTEMATICALLY**: Structure your response to cover all discovered information logically
8. **CROSS-REFERENCE**: When multiple documents mention the same information, note this for validation
9. **IDENTIFY GAPS**: If information is missing, explicitly state what additional information would be helpful
10. **PRIORITIZE COMPLETENESS**: Better to be comprehensive than concise - include all relevant details

RESPONSE REQUIREMENTS:
- Provide an extremely detailed, thorough answer
- Use information from as many documents as possible
- Include specific document references for every fact
- Synthesize information comprehensively across all sources
- Note any contradictions or variations between documents
- Organize information clearly but comprehensively
- If insufficient information exists, explain exactly what IS available and what is missing

COMPREHENSIVE ANALYSIS AND RESPONSE:"""

        return prompt
    
    def _enhance_response_quality(self, response: str, documents: List[Any]) -> str:
        """Enhance response quality with additional context and validation"""
        try:
            # Add document count and confidence summary
            doc_count = len(documents)
            high_conf_count = sum(1 for d in documents if d.score >= ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH)
            
            quality_summary = f"""

📊 ANALYSIS SUMMARY:
• Documents analyzed: {doc_count}
• High-confidence sources: {high_conf_count}
• Response based on comprehensive document review

"""
            
            # Add confidence indicator if documents are available
            if documents:
                avg_confidence = sum(d.score for d in documents) / len(documents)
                if avg_confidence >= 0.8:
                    confidence_indicator = "🎯 HIGH CONFIDENCE: Response based on strong document evidence"
                elif avg_confidence >= 0.7:
                    confidence_indicator = "✅ GOOD CONFIDENCE: Response based on reliable document evidence"
                else:
                    confidence_indicator = "⚠️ MODERATE CONFIDENCE: Response based on available document evidence"
                
                enhanced_response = f"{response}\n\n{confidence_indicator}{quality_summary}"
            else:
                enhanced_response = f"{response}{quality_summary}"
            
            return enhanced_response
            
        except Exception as e:
            logger.error(f"❌ Response enhancement failed: {e}")
            return response
    
    def _generate_fallback_response(self, query: str, documents: List[Any], device_id: str) -> str:
        """Generate fallback response when AI is not available"""
        if not documents:
            return f"""❌ NO RELEVANT DOCUMENTS FOUND

I could not find any relevant documents for device {device_id} to answer: "{query}"

Please ensure:
1. Relevant documents are uploaded for this device
2. Documents contain information related to your query
3. Try rephrasing your question with different keywords

Upload more relevant documents and try again."""
        
        # Create simple response from document content
        response_parts = [
            f"Based on {len(documents)} documents found for device {device_id}:",
            ""
        ]
        
        for i, doc in enumerate(documents[:5]):  # Show top 5 documents
            response_parts.append(f"Document {i+1} (Confidence: {doc.score:.2f}):")
            response_parts.append(doc.content[:300] + "..." if len(doc.content) > 300 else doc.content)
            response_parts.append("")
        
        return "\n".join(response_parts)

class EnhancedRAGSystem:
    """Complete enhanced RAG system with comprehensive accuracy"""
    
    def __init__(self, gemini_service, pinecone_service):
        self.retriever = ComprehensiveDocumentRetriever(gemini_service, pinecone_service)
        self.generator = ComprehensiveResponseGenerator(gemini_service)
        self.gemini_service = gemini_service
        self.pinecone_service = pinecone_service
    
    async def process_query_comprehensively(
        self,
        query: str,
        device_id: str
    ) -> Dict[str, Any]:
        """Process a query with comprehensive document analysis and detailed response"""
        try:
            logger.info(f"🚀 Starting comprehensive RAG analysis for query: {query}")
            
            # Step 1: Comprehensive document retrieval
            documents, retrieval_stats = await self.retriever.comprehensive_retrieval(
                query=query,
                device_id=device_id
            )
            
            # Step 2: Generate comprehensive response
            detailed_response = await self.generator.generate_comprehensive_response(
                query=query,
                documents=documents,
                retrieval_stats=retrieval_stats,
                device_id=device_id
            )
            
            # Step 3: Prepare detailed source information
            detailed_sources = self._prepare_detailed_sources(documents)
            
            # Step 4: Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(documents, retrieval_stats)
            
            result = {
                "response": detailed_response,
                "sources": detailed_sources,
                "device_id": device_id,
                "retrieval_stats": retrieval_stats,
                "quality_metrics": quality_metrics,
                "comprehensive_analysis": True
            }
            
            logger.info(f"✅ Comprehensive RAG analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Comprehensive RAG processing failed: {e}")
            return {
                "response": f"Error processing query: {e}",
                "sources": [],
                "device_id": device_id,
                "error": str(e),
                "comprehensive_analysis": False
            }
    
    def _prepare_detailed_sources(self, documents: List[Any]) -> List[Dict[str, Any]]:
        """Prepare detailed source information with enhanced metadata"""
        detailed_sources = []
        
        for i, doc in enumerate(documents):
            source_info = {
                "document_number": i + 1,
                "filename": doc.metadata.get("filename", "Unknown"),
                "chunk_id": doc.metadata.get("chunk_id", 0),
                "confidence_score": round(doc.score, 4),
                "confidence_level": self._get_confidence_level(doc.score),
                "document_id": doc.metadata.get("document_id", "Unknown"),
                "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content,
                "content_length": len(doc.content),
                "relevance_tier": self._get_relevance_tier(doc.score)
            }
            detailed_sources.append(source_info)
        
        return detailed_sources
    
    def _get_confidence_level(self, score: float) -> str:
        """Get confidence level description"""
        if score >= ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL:
            return "CRITICAL"
        elif score >= ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH:
            return "HIGH"
        elif score >= ENHANCED_CONFIG.MIN_CONFIDENCE_ACCEPTABLE:
            return "ACCEPTABLE"
        else:
            return "LOW"
    
    def _get_relevance_tier(self, score: float) -> str:
        """Get relevance tier for organization"""
        if score >= ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL:
            return "PRIMARY"
        elif score >= ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH:
            return "SECONDARY"
        else:
            return "SUPPORTING"
    
    def _calculate_quality_metrics(self, documents: List[Any], retrieval_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive quality metrics"""
        if not documents:
            return {"error": "No documents available for quality assessment"}
        
        scores = [doc.score for doc in documents]
        
        return {
            "total_documents_analyzed": len(documents),
            "average_confidence": sum(scores) / len(scores),
            "max_confidence": max(scores),
            "min_confidence": min(scores),
            "critical_confidence_count": sum(1 for s in scores if s >= ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL),
            "high_confidence_count": sum(1 for s in scores if s >= ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH),
            "acceptable_confidence_count": sum(1 for s in scores if s >= ENHANCED_CONFIG.MIN_CONFIDENCE_ACCEPTABLE),
            "query_variations_used": retrieval_stats.get("query_variations", 1),
            "retrieval_method": "comprehensive" if retrieval_stats.get("query_variations", 0) > 1 else "standard",
            "analysis_quality": self._get_analysis_quality(scores),
            "recommendation": self._get_quality_recommendation(scores)
        }
    
    def _get_analysis_quality(self, scores: List[float]) -> str:
        """Determine overall analysis quality"""
        if not scores:
            return "NO_DATA"
        
        avg_score = sum(scores) / len(scores)
        critical_count = sum(1 for s in scores if s >= ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL)
        
        if avg_score >= 0.8 and critical_count >= 3:
            return "EXCELLENT"
        elif avg_score >= 0.75 and critical_count >= 1:
            return "VERY_GOOD"
        elif avg_score >= 0.7:
            return "GOOD"
        elif avg_score >= 0.65:
            return "ACCEPTABLE"
        else:
            return "LIMITED"
    
    def _get_quality_recommendation(self, scores: List[float]) -> str:
        """Get recommendation for improving response quality"""
        if not scores:
            return "Upload relevant documents for this device"
        
        avg_score = sum(scores) / len(scores)
        
        if avg_score >= 0.8:
            return "High-quality documents available - responses should be very accurate"
        elif avg_score >= 0.7:
            return "Good document quality - responses should be reliable"
        elif avg_score >= 0.65:
            return "Moderate document quality - consider uploading more specific documents"
        else:
            return "Limited relevant documents - upload more documents related to your query"

# Global enhanced RAG system instance will be created when needed
enhanced_rag_system = None

async def initialize_enhanced_rag(gemini_service, pinecone_service):
    """Initialize the enhanced RAG system"""
    global enhanced_rag_system
    enhanced_rag_system = EnhancedRAGSystem(gemini_service, pinecone_service)
    logger.info("✅ Enhanced RAG system initialized")
    return enhanced_rag_system

if __name__ == "__main__":
    # Test configuration
    print("Enhanced RAG Accuracy Configuration:")
    print(f"Initial Retrieval Count: {ENHANCED_CONFIG.INITIAL_RETRIEVAL_COUNT}")
    print(f"Multi-Query Count: {ENHANCED_CONFIG.MULTI_QUERY_COUNT}")
    print(f"Final Context Count: {ENHANCED_CONFIG.FINAL_CONTEXT_COUNT}")
    print(f"Min Confidence (Critical): {ENHANCED_CONFIG.MIN_CONFIDENCE_CRITICAL}")
    print(f"Min Confidence (High): {ENHANCED_CONFIG.MIN_CONFIDENCE_HIGH}")
    print(f"Temperature (Factual): {ENHANCED_CONFIG.TEMPERATURE_FACTUAL}")
    print(f"Max Response Tokens: {ENHANCED_CONFIG.MAX_RESPONSE_TOKENS}")
