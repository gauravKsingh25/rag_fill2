"""
Hybrid RAG Strategy Implementation
==================================

This module implements a hybrid approach that combines:
1. Precise RAG retrieval for specific/exact information
2. Generalized LLM responses for descriptive/explanatory content
3. Best mix strategy that adapts based on query type and content needed

Author: Enhanced RAG System
Version: 1.0
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Types of queries that determine response strategy"""
    EXACT_FACT = "exact_fact"           # Needs precise extraction
    DESCRIPTIVE = "descriptive"         # Needs explanation/description  
    MIXED = "mixed"                     # Needs both exact + descriptive
    CODE_SPECIFIC = "code_specific"     # Codes, numbers, IDs
    GENERAL_KNOWLEDGE = "general_knowledge"  # General explanations

class ContentType(Enum):
    """Types of content that fields expect"""
    PRECISE_VALUE = "precise_value"     # Names, numbers, codes, dates
    SHORT_DESCRIPTION = "short_description"  # Brief explanations
    LONG_DESCRIPTION = "long_description"    # Detailed descriptions
    TECHNICAL_SPEC = "technical_spec"   # Technical specifications
    REGULATORY_TEXT = "regulatory_text"  # Regulatory/compliance text

@dataclass
class HybridStrategy:
    """Configuration for hybrid response strategy"""
    rag_weight: float          # 0.0 to 1.0 - how much to rely on RAG
    llm_weight: float          # 0.0 to 1.0 - how much to rely on general LLM
    min_confidence: float      # Minimum confidence for RAG results
    temperature: float         # Temperature for LLM generation
    max_tokens: int           # Max tokens for response
    use_fallback: bool        # Whether to use LLM fallback if RAG fails

class HybridRAGProcessor:
    """
    Hybrid RAG Processor that intelligently combines RAG retrieval with LLM generation
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Strategy configurations for different scenarios
        self.strategies = {
            # For exact information that must be precise
            QueryType.EXACT_FACT: HybridStrategy(
                rag_weight=0.95,       # Heavily favor RAG
                llm_weight=0.05,       # Minimal LLM generation
                min_confidence=0.80,   # High confidence required
                temperature=0.01,      # Very low temperature
                max_tokens=100,        # Short, precise answers
                use_fallback=False     # Don't fallback to general LLM
            ),
            
            # For codes, numbers, IDs that must be exact
            QueryType.CODE_SPECIFIC: HybridStrategy(
                rag_weight=1.0,        # Only use RAG
                llm_weight=0.0,        # No LLM generation
                min_confidence=0.85,   # Very high confidence required
                temperature=0.001,     # Extremely low temperature
                max_tokens=50,         # Very short answers
                use_fallback=False     # Never fallback for codes
            ),
            
            # For descriptions, explanations, use cases
            QueryType.DESCRIPTIVE: HybridStrategy(
                rag_weight=0.30,       # Some RAG for context
                llm_weight=0.70,       # Mostly LLM generation
                min_confidence=0.60,   # Lower confidence ok
                temperature=0.40,      # Higher temperature for creativity
                max_tokens=500,        # Longer descriptive answers
                use_fallback=True      # Use LLM if RAG insufficient
            ),
            
            # For mixed content (facts + descriptions)
            QueryType.MIXED: HybridStrategy(
                rag_weight=0.60,       # Balanced approach
                llm_weight=0.40,       # Significant LLM contribution
                min_confidence=0.70,   # Moderate confidence
                temperature=0.15,      # Moderate temperature
                max_tokens=300,        # Medium length
                use_fallback=True      # Use fallback when needed
            ),
            
            # For general knowledge explanations
            QueryType.GENERAL_KNOWLEDGE: HybridStrategy(
                rag_weight=0.20,       # Light RAG for context
                llm_weight=0.80,       # Heavy LLM generation
                min_confidence=0.50,   # Low confidence ok
                temperature=0.50,      # Higher temperature
                max_tokens=600,        # Longer explanations
                use_fallback=True      # Always use LLM fallback
            )
        }
    
    def classify_query_type(self, query: str, field_name: str = "", field_context: str = "") -> QueryType:
        """
        Classify the type of query/field to determine optimal strategy
        """
        try:
            query_lower = query.lower()
            field_lower = field_name.lower()
            context_lower = field_context.lower()
            
            # Combine all text for analysis
            all_text = f"{query_lower} {field_lower} {context_lower}"
            
            # Code/Number patterns - these MUST be exact
            code_patterns = [
                r'\b(code|number|id|serial|model|part|doc|ref|std)\b',
                r'\b(no\.?|#|num)\b',
                r'\b\w{2,}-\d+\b',  # Format like ABC-123
                r'\b[A-Z]{2,}\d+\b',  # Format like ABC123
                r'\bversion\b',
                r'\bdate\b(?!.*(?:description|explanation))',  # Date but not "date description"
            ]
            
            # Exact fact patterns - need precise extraction
            exact_fact_patterns = [
                r'\b(name|title|manufacturer|company|address)\b',
                r'\b(who|what|when|where)\s+(is|are|was)\b',
                r'\bspecific\b',
                r'\bexact\b',
                r'\bprecise\b',
            ]
            
            # Descriptive patterns - need explanation
            descriptive_patterns = [
                r'\b(description|explain|describe|how|why)\b',
                r'\b(purpose|function|mechanism|principle)\b',
                r'\b(use case|application|indication)\b',
                r'\b(summary|overview|background)\b',
                r'\b(risk|safety|warning|precaution)\b',
                r'\b(feature|characteristic|property)\b',
                r'\b(clinical|performance|evaluation)\b',
                r'\b(instruction|procedure|method)\b',
            ]
            
            # General knowledge patterns
            general_patterns = [
                r'\b(what does|how does|why does)\b',
                r'\b(generally|typically|usually)\b',
                r'\b(define|definition)\b',
                r'\b(concept|theory|principle)\b',
            ]
            
            # Check for code/number patterns (highest priority)
            for pattern in code_patterns:
                if re.search(pattern, all_text):
                    self.logger.info(f"🔢 Classified as CODE_SPECIFIC: {pattern}")
                    return QueryType.CODE_SPECIFIC
            
            # Check for exact fact patterns
            exact_score = sum(1 for pattern in exact_fact_patterns if re.search(pattern, all_text))
            
            # Check for descriptive patterns
            desc_score = sum(1 for pattern in descriptive_patterns if re.search(pattern, all_text))
            
            # Check for general knowledge patterns
            general_score = sum(1 for pattern in general_patterns if re.search(pattern, all_text))
            
            # Decision logic
            if exact_score > 0 and desc_score > 0:
                self.logger.info(f"🔄 Classified as MIXED (exact: {exact_score}, desc: {desc_score})")
                return QueryType.MIXED
            elif exact_score > desc_score and exact_score > general_score:
                self.logger.info(f"🎯 Classified as EXACT_FACT (score: {exact_score})")
                return QueryType.EXACT_FACT
            elif desc_score > 0:
                self.logger.info(f"📝 Classified as DESCRIPTIVE (score: {desc_score})")
                return QueryType.DESCRIPTIVE
            elif general_score > 0:
                self.logger.info(f"🧠 Classified as GENERAL_KNOWLEDGE (score: {general_score})")
                return QueryType.GENERAL_KNOWLEDGE
            else:
                # Default to mixed approach for ambiguous cases
                self.logger.info(f"❓ Defaulting to MIXED for ambiguous query")
                return QueryType.MIXED
                
        except Exception as e:
            self.logger.error(f"❌ Failed to classify query type: {e}")
            return QueryType.MIXED
    
    def classify_content_type(self, field_name: str, field_context: str) -> ContentType:
        """
        Classify the type of content expected for a field
        """
        try:
            field_lower = field_name.lower()
            context_lower = field_context.lower()
            combined = f"{field_lower} {context_lower}"
            
            # Precise value indicators
            if any(term in combined for term in [
                'name', 'number', 'id', 'code', 'date', 'version', 'model',
                'serial', 'manufacturer', 'company', 'address', 'phone', 'email'
            ]):
                return ContentType.PRECISE_VALUE
            
            # Long description indicators
            elif any(term in combined for term in [
                'description', 'summary', 'overview', 'background', 'purpose',
                'explanation', 'details', 'information', 'clinical evidence',
                'risk management', 'evaluation', 'assessment', 'analysis'
            ]):
                if any(term in combined for term in ['detailed', 'comprehensive', 'full']):
                    return ContentType.LONG_DESCRIPTION
                else:
                    return ContentType.SHORT_DESCRIPTION
            
            # Technical specification indicators
            elif any(term in combined for term in [
                'specification', 'technical', 'performance', 'parameter',
                'characteristic', 'property', 'feature', 'standard'
            ]):
                return ContentType.TECHNICAL_SPEC
            
            # Regulatory text indicators
            elif any(term in combined for term in [
                'regulatory', 'compliance', 'requirement', 'standard',
                'approval', 'certification', 'validation', 'verification'
            ]):
                return ContentType.REGULATORY_TEXT
            
            else:
                return ContentType.SHORT_DESCRIPTION
                
        except Exception as e:
            self.logger.error(f"❌ Failed to classify content type: {e}")
            return ContentType.SHORT_DESCRIPTION
    
    async def get_hybrid_response(
        self,
        query: str,
        field_name: str = "",
        field_context: str = "",
        rag_results: List[Dict[str, Any]] = None,
        gemini_service = None,
        device_id: str = ""
    ) -> Dict[str, Any]:
        """
        Generate hybrid response combining RAG retrieval with LLM generation
        """
        try:
            # Classify query and content types
            query_type = self.classify_query_type(query, field_name, field_context)
            content_type = self.classify_content_type(field_name, field_context)
            strategy = self.strategies[query_type]
            
            self.logger.info(f"🎯 Query Type: {query_type.value}")
            self.logger.info(f"📋 Content Type: {content_type.value}")
            self.logger.info(f"⚖️ Strategy: RAG={strategy.rag_weight}, LLM={strategy.llm_weight}")
            
            # Process RAG results
            rag_response = ""
            rag_confidence = 0.0
            high_conf_results = []
            
            if rag_results:
                # Filter by confidence
                high_conf_results = [
                    r for r in rag_results 
                    if r.get('score', 0) >= strategy.min_confidence
                ]
                
                if high_conf_results:
                    rag_confidence = sum(r.get('score', 0) for r in high_conf_results) / len(high_conf_results)
                    rag_context = "\n\n".join(r.get('content', '') for r in high_conf_results[:5])
                    
                    # Generate RAG-based response
                    if strategy.rag_weight > 0:
                        rag_response = await self._generate_rag_response(
                            query, field_name, field_context, rag_context, 
                            query_type, strategy, gemini_service
                        )
            
            # Generate LLM response if needed
            llm_response = ""
            if strategy.llm_weight > 0 and (
                strategy.use_fallback or 
                rag_confidence < strategy.min_confidence or
                not rag_response
            ):
                llm_response = await self._generate_llm_response(
                    query, field_name, field_context, query_type, 
                    content_type, strategy, gemini_service, device_id
                )
            
            # Combine responses based on strategy
            final_response = await self._combine_responses(
                rag_response, llm_response, strategy, query_type, content_type
            )
            
            return {
                "response": final_response,
                "strategy_used": {
                    "query_type": query_type.value,
                    "content_type": content_type.value,
                    "rag_weight": strategy.rag_weight,
                    "llm_weight": strategy.llm_weight,
                    "rag_confidence": rag_confidence,
                    "rag_results_count": len(high_conf_results),
                    "approach": self._get_approach_description(strategy, rag_confidence)
                },
                "sources": high_conf_results[:3] if high_conf_results else []
            }
            
        except Exception as e:
            self.logger.error(f"❌ Failed to get hybrid response: {e}")
            return {
                "response": "I encountered an error processing your request.",
                "strategy_used": {"error": str(e)},
                "sources": []
            }
    
    async def _generate_rag_response(
        self, query: str, field_name: str, field_context: str, 
        rag_context: str, query_type: QueryType, strategy: HybridStrategy,
        gemini_service
    ) -> str:
        """Generate response primarily based on RAG context"""
        try:
            if query_type == QueryType.CODE_SPECIFIC:
                # For codes/numbers, use very precise extraction
                prompt = f"""Extract the exact value for "{field_name}" from the provided context. Return ONLY the specific value without any additional text or explanation.

Context: {rag_context}

Field: {field_name}
Query: {query}

Extract only the precise value:"""
            
            elif query_type == QueryType.EXACT_FACT:
                # For exact facts, extract precisely
                prompt = f"""Based on the provided context, extract the exact information for "{field_name}".

Context: {rag_context}

Field: {field_name}
Query: {query}

Provide only the specific factual information requested:"""
            
            else:
                # For mixed/descriptive, use context but allow some generation
                prompt = f"""Based on the provided context, answer the query about "{field_name}". Use the context as your primary source but provide a complete, helpful response.

Context: {rag_context}

Field: {field_name}
Query: {query}
Context: {field_context}

Provide a helpful response based primarily on the context:"""
            
            if gemini_service and gemini_service.available:
                response = await gemini_service.generate_response(
                    prompt=prompt,
                    temperature=strategy.temperature,
                    max_tokens=strategy.max_tokens
                )
                return response.strip()
            else:
                return "RAG extraction not available"
                
        except Exception as e:
            self.logger.error(f"❌ Failed to generate RAG response: {e}")
            return ""
    
    async def _generate_llm_response(
        self, query: str, field_name: str, field_context: str,
        query_type: QueryType, content_type: ContentType, 
        strategy: HybridStrategy, gemini_service, device_id: str
    ) -> str:
        """Generate response using general LLM knowledge"""
        try:
            if query_type == QueryType.CODE_SPECIFIC:
                # Never use LLM for codes
                return ""
            
            # Customize prompt based on content type
            if content_type == ContentType.LONG_DESCRIPTION:
                prompt = f"""Provide a comprehensive description for the field "{field_name}" in the context of medical device documentation.

Field: {field_name}
Context: {field_context}
Query: {query}
Device ID: {device_id}

Requirements:
- Provide a detailed, professional description (2-3 paragraphs)
- Use appropriate medical device terminology
- Include relevant technical and regulatory considerations
- Ensure content is suitable for regulatory documentation
- Write in clear, professional language

Description:"""
            
            elif content_type == ContentType.SHORT_DESCRIPTION:
                prompt = f"""Provide a concise description for the field "{field_name}" in medical device documentation.

Field: {field_name}
Context: {field_context}
Query: {query}

Requirements:
- Provide a brief, professional description (1-2 sentences)
- Use appropriate medical terminology
- Be clear and direct
- Suitable for technical documentation

Description:"""
            
            elif content_type == ContentType.TECHNICAL_SPEC:
                prompt = f"""Provide technical specification information for the field "{field_name}".

Field: {field_name}
Context: {field_context}
Query: {query}

Requirements:
- Focus on technical specifications and parameters
- Use appropriate technical terminology
- Be precise and accurate
- Include relevant performance characteristics

Specification:"""
            
            elif content_type == ContentType.REGULATORY_TEXT:
                prompt = f"""Provide appropriate regulatory text for the field "{field_name}".

Field: {field_name}
Context: {field_context}
Query: {query}

Requirements:
- Use regulatory/compliance language
- Follow medical device industry standards
- Be clear and professional
- Suitable for regulatory submissions

Regulatory text:"""
            
            else:
                prompt = f"""Provide appropriate content for the field "{field_name}".

Field: {field_name}
Context: {field_context}
Query: {query}

Provide clear, professional content suitable for medical device documentation:"""
            
            if gemini_service and gemini_service.available:
                response = await gemini_service.generate_response(
                    prompt=prompt,
                    temperature=strategy.temperature,
                    max_tokens=strategy.max_tokens
                )
                return response.strip()
            else:
                return self._fallback_llm_response(field_name, content_type)
                
        except Exception as e:
            self.logger.error(f"❌ Failed to generate LLM response: {e}")
            return ""
    
    async def _combine_responses(
        self, rag_response: str, llm_response: str, 
        strategy: HybridStrategy, query_type: QueryType, 
        content_type: ContentType
    ) -> str:
        """Combine RAG and LLM responses based on strategy"""
        try:
            # For code-specific queries, only use RAG
            if query_type == QueryType.CODE_SPECIFIC:
                return rag_response if rag_response else "NOT_FOUND"
            
            # For exact facts, prioritize RAG heavily
            elif query_type == QueryType.EXACT_FACT:
                if rag_response and len(rag_response.strip()) > 0:
                    return rag_response
                elif strategy.use_fallback and llm_response:
                    return llm_response
                else:
                    return "NOT_FOUND"
            
            # For descriptive content, intelligently combine
            elif query_type in [QueryType.DESCRIPTIVE, QueryType.MIXED, QueryType.GENERAL_KNOWLEDGE]:
                if rag_response and llm_response:
                    # Both available - combine intelligently
                    if len(rag_response) < 50 and len(llm_response) > 100:
                        # RAG has brief info, LLM has detailed - combine
                        return f"{rag_response.rstrip('.')}. {llm_response}"
                    elif strategy.rag_weight > strategy.llm_weight:
                        # Prefer RAG
                        return rag_response
                    else:
                        # Prefer LLM
                        return llm_response
                elif rag_response:
                    return rag_response
                elif llm_response:
                    return llm_response
                else:
                    return "NOT_FOUND"
            
            # Default fallback
            return rag_response or llm_response or "NOT_FOUND"
            
        except Exception as e:
            self.logger.error(f"❌ Failed to combine responses: {e}")
            return rag_response or llm_response or "ERROR"
    
    def _get_approach_description(self, strategy: HybridStrategy, rag_confidence: float) -> str:
        """Get human-readable description of the approach used"""
        if strategy.rag_weight >= 0.8:
            if rag_confidence >= 0.8:
                return "High-confidence RAG extraction"
            else:
                return "RAG extraction with moderate confidence"
        elif strategy.llm_weight >= 0.8:
            return "AI-generated content based on general knowledge"
        else:
            return f"Hybrid approach (RAG: {strategy.rag_weight:.1f}, LLM: {strategy.llm_weight:.1f})"
    
    def _fallback_llm_response(self, field_name: str, content_type: ContentType) -> str:
        """Provide fallback response when LLM is not available"""
        if content_type == ContentType.PRECISE_VALUE:
            return "VALUE_NEEDED"
        elif content_type == ContentType.SHORT_DESCRIPTION:
            return f"Brief description needed for {field_name}"
        elif content_type == ContentType.LONG_DESCRIPTION:
            return f"Detailed description and information needed for {field_name}"
        else:
            return f"Information needed for {field_name}"

# Global instance
hybrid_processor = HybridRAGProcessor()

# Convenience functions for easy integration
async def get_hybrid_chat_response(
    query: str, rag_results: List[Dict[str, Any]], 
    gemini_service, device_id: str = ""
) -> Dict[str, Any]:
    """Get hybrid response for chat queries"""
    return await hybrid_processor.get_hybrid_response(
        query=query,
        rag_results=rag_results,
        gemini_service=gemini_service,
        device_id=device_id
    )

async def get_hybrid_field_response(
    field_name: str, field_context: str, rag_results: List[Dict[str, Any]],
    gemini_service, device_id: str = ""
) -> Dict[str, Any]:
    """Get hybrid response for template field filling"""
    query = f"Fill the field {field_name}"
    return await hybrid_processor.get_hybrid_response(
        query=query,
        field_name=field_name,
        field_context=field_context,
        rag_results=rag_results,
        gemini_service=gemini_service,
        device_id=device_id
    )
