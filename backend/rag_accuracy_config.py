"""
RAG Accuracy Configuration and Testing Module

This module provides configuration settings and testing utilities
for ensuring 100% accurate, fact-based responses from the RAG system.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RAGAccuracyConfig:
    """Configuration for RAG accuracy settings - ENHANCED for document filling"""
    
    # Confidence thresholds - ENHANCED
    MIN_CONFIDENCE_HIGH: float = 0.75     # High confidence threshold (lowered for more inclusive results)
    MIN_CONFIDENCE_GOOD: float = 0.65     # Good confidence threshold (lowered)
    MIN_CONFIDENCE_MODERATE: float = 0.5  # Minimum acceptable confidence (lowered for comprehensive coverage)
    
    # Retrieval settings - ENHANCED for comprehensive document coverage
    MAX_CHUNKS_INITIAL: int = 20          # Initial retrieval count (increased)
    MAX_CHUNKS_FINAL: int = 15            # Final chunks for response (increased)
    MAX_CHUNKS_PER_QUERY: int = 10        # Per query chunk limit (increased)
    
    # Temperature settings for accuracy - OPTIMIZED for document filling
    TEMPERATURE_FACT_VERIFICATION: float = 0.01  # Extremely low for facts
    TEMPERATURE_RESPONSE_GENERATION: float = 0.05 # Very low for document filling
    TEMPERATURE_FIELD_EXTRACTION: float = 0.01   # Extremely low for field extraction
    
    # Prompt engineering settings - ENHANCED for document filling
    REQUIRE_CITATIONS: bool = False       # Disabled for cleaner field filling
    STRICT_FACT_MODE: bool = True         # Only use explicit document facts
    NO_INFERENCE_MODE: bool = True        # Prohibit AI inferences
    COMPREHENSIVE_SEARCH_MODE: bool = True # Enable multi-query comprehensive search
    
    # Response quality settings - OPTIMIZED for document filling
    MAX_RESPONSE_TOKENS: int = 200        # Reduced for concise field values
    ENABLE_CONFIDENCE_INDICATORS: bool = False  # Disabled for cleaner field values
    
    # Document processing settings - NEW
    ENHANCED_CHUNKING: bool = True        # Enable enhanced chunking with metadata
    QUALITY_FILTERING: bool = True        # Enable chunk quality filtering
    IMPORTANCE_SCORING: bool = True       # Enable importance-based scoring
    SEMANTIC_ENHANCEMENT: bool = True     # Enable semantic keyword extraction

# Global accuracy configuration
ACCURACY_CONFIG = RAGAccuracyConfig()

class AccuracyPrompts:
    """Standardized prompts for maximum accuracy - ENHANCED for document filling"""
    
    DOCUMENT_FILLING_PROMPT = """You are an expert document analysis system specialized in extracting precise information for template field filling. Your ONLY task is to find the exact value for the specified field from the provided document chunks.

CRITICAL INSTRUCTIONS FOR DOCUMENT FILLING:
1. 🎯 ONLY extract information that is EXPLICITLY stated in the document chunks
2. 📝 Return ONLY the specific field value - no labels, prefixes, or explanations
3. 🚫 Do NOT add any additional text, formatting, or commentary
4. ✅ Extract the precise data that would go in the template field
5. ❌ If the information is not found, return exactly "NOT_FOUND"
6. 🔍 Look through ALL provided chunks thoroughly before concluding
7. 📊 Use the most specific and detailed information if multiple sources exist

EXTRACTION EXAMPLES:
- Field: "Generic Name" → Extract: "Pulse Oximeter" (NOT "Generic Name: Pulse Oximeter")
- Field: "Model Number" → Extract: "OPO-101" (NOT "Model: OPO-101")  
- Field: "Manufacturer" → Extract: "ACME Corp" (NOT "Manufactured by ACME Corp")
- Field: "Date" → Extract: "03/15/2024" (NOT "Date: 03/15/2024")

EXTRACTED VALUE:"""

    COMPREHENSIVE_FIELD_PROMPT = """You are performing comprehensive document analysis to extract specific field information. Analyze ALL provided document chunks systematically.

COMPREHENSIVE ANALYSIS PROTOCOL:
1. 🔍 Scan through EVERY document chunk provided
2. 🎯 Look for direct mentions of the field or closely related information
3. 📊 Cross-reference information across multiple chunks
4. ✅ Prioritize exact matches over approximate matches
5. 🔄 If multiple chunks contain the same field, use the most detailed/recent version
6. 📝 Extract ONLY the field value without any additional formatting
7. ❌ Return "NOT_FOUND" only if the information is completely absent

FIELD EXTRACTION RULES:
- Be extremely precise - extract only what belongs in the field
- Remove field labels and prefixes from the extracted value
- Maintain original formatting of numbers, dates, and technical codes
- Use the most authoritative source if conflicts exist

VALUE EXTRACTED:"""

    STRICT_FACT_PROMPT = """You are a highly accurate document analysis system. Your task is to provide ONLY factual information that can be directly found in the provided document chunks.

CRITICAL INSTRUCTIONS:
1. ONLY use information that is EXPLICITLY stated in the document chunks
2. Do NOT make assumptions, generalizations, or add external knowledge
3. If the exact information is not in the documents, state: "This information is not available in the provided documents."
4. Quote relevant parts of the documents when possible using quotation marks
5. Be specific about which document chunk contains the information
6. If multiple chunks contain related information, cite all relevant chunks
7. Do NOT use phrases like "generally", "typically", "usually" - stick to facts only
8. If the question asks for something not covered in the documents, explicitly state what IS available instead

RESPONSE FORMAT:
- Start with the direct answer if available
- Cite specific document chunks: [From Chunk X: "exact quote"]
- If no relevant information: "This specific information is not available in the provided documents. However, the documents contain information about: [list what IS available]"

FACTUAL RESPONSE:"""

    FACT_VERIFICATION_PROMPT = """FACT VERIFICATION TASK

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

    NO_DOCUMENTS_PROMPT = """I don't have access to any relevant documents in my knowledge base to answer your question. Please upload documents related to your query first.

To get accurate answers, I need:
1. Documents uploaded to the device
2. Relevant content that addresses your specific question

Please upload relevant documents and try again."""

class AccuracyMetrics:
    """Metrics for measuring RAG accuracy"""
    
    @staticmethod
    def calculate_confidence_score(search_results: List[Any]) -> Dict[str, float]:
        """Calculate confidence metrics for search results"""
        if not search_results:
            return {
                "avg_confidence": 0.0,
                "max_confidence": 0.0,
                "min_confidence": 0.0,
                "high_confidence_count": 0,
                "total_results": 0
            }
        
        scores = [result.score for result in search_results]
        
        return {
            "avg_confidence": sum(scores) / len(scores),
            "max_confidence": max(scores),
            "min_confidence": min(scores),
            "high_confidence_count": sum(1 for score in scores if score >= ACCURACY_CONFIG.MIN_CONFIDENCE_HIGH),
            "total_results": len(scores)
        }
    
    @staticmethod
    def get_confidence_level(score: float) -> str:
        """Get confidence level description"""
        if score >= ACCURACY_CONFIG.MIN_CONFIDENCE_HIGH:
            return "HIGH"
        elif score >= ACCURACY_CONFIG.MIN_CONFIDENCE_GOOD:
            return "GOOD"
        elif score >= ACCURACY_CONFIG.MIN_CONFIDENCE_MODERATE:
            return "MODERATE"
        else:
            return "LOW"
    
    @staticmethod
    def get_search_quality(avg_confidence: float) -> str:
        """Determine overall search quality"""
        if avg_confidence >= 0.8:
            return "EXCELLENT"
        elif avg_confidence >= 0.7:
            return "GOOD"
        elif avg_confidence >= 0.6:
            return "MODERATE"
        else:
            return "POOR"

class ResponseValidator:
    """Validates response accuracy and quality"""
    
    @staticmethod
    def validate_response_accuracy(response: str, sources: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate response accuracy based on sources"""
        validation_result = {
            "has_citations": False,
            "source_count": len(sources),
            "confidence_indicators": False,
            "fact_based": True,  # Assume true unless we find issues
            "warnings": []
        }
        
        # Check for citations
        if "[From Chunk" in response or "document chunk" in response.lower():
            validation_result["has_citations"] = True
        
        # Check for confidence indicators
        confidence_indicators = ["🎯 HIGH CONFIDENCE", "✅ GOOD CONFIDENCE", "⚠️ MODERATE CONFIDENCE"]
        if any(indicator in response for indicator in confidence_indicators):
            validation_result["confidence_indicators"] = True
        
        # Check for prohibited phrases (generalizations)
        prohibited_phrases = ["generally", "typically", "usually", "in most cases", "often"]
        for phrase in prohibited_phrases:
            if phrase.lower() in response.lower():
                validation_result["fact_based"] = False
                validation_result["warnings"].append(f"Contains generalization: '{phrase}'")
        
        # Check if response explicitly states when information is not available
        if "not available in the provided documents" in response.lower():
            validation_result["explicit_limitations"] = True
        
        return validation_result

class AccuracyTester:
    """Test RAG accuracy with sample queries"""
    
    SAMPLE_FACT_CHECKS = [
        "What is the exact model number mentioned in the documents?",
        "Who is the manufacturer of the device?", 
        "What is the specific document number?",
        "What is the exact date mentioned?",
        "What are the technical specifications listed?"
    ]
    
    SAMPLE_VERIFICATION_CLAIMS = [
        "The device has FDA approval",
        "The model number is XYZ-123",
        "The manufacturer is ACME Corporation",
        "The document was created in 2024"
    ]
    
    @staticmethod
    async def test_accuracy_with_sample_queries(device_id: str, chat_function) -> Dict[str, Any]:
        """Test RAG accuracy with predefined queries"""
        results = {
            "total_tests": len(AccuracyTester.SAMPLE_FACT_CHECKS),
            "passed_tests": 0,
            "test_results": []
        }
        
        for query in AccuracyTester.SAMPLE_FACT_CHECKS:
            try:
                # This would call your actual chat function
                # response = await chat_function(device_id, query)
                
                # Placeholder for actual testing
                test_result = {
                    "query": query,
                    "status": "NOT_IMPLEMENTED",
                    "accuracy_score": 0.0,
                    "has_citations": False,
                    "fact_based": False
                }
                
                results["test_results"].append(test_result)
                
            except Exception as e:
                logger.error(f"Test failed for query '{query}': {e}")
                results["test_results"].append({
                    "query": query,
                    "status": "ERROR",
                    "error": str(e)
                })
        
        return results

# Environment variable checking for accuracy
def check_accuracy_environment() -> Dict[str, bool]:
    """Check if environment is configured for maximum accuracy"""
    checks = {
        "google_api_key_set": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")),
        "pinecone_configured": bool(os.getenv("PINECONE_API_KEY")),
        "mongodb_configured": bool(os.getenv("MONGODB_URL")),
        "debug_mode": os.getenv("DEBUG", "False").lower() == "true"
    }
    
    return checks

def get_accuracy_recommendations() -> List[str]:
    """Get recommendations for improving RAG accuracy"""
    env_checks = check_accuracy_environment()
    recommendations = []
    
    if not env_checks["google_api_key_set"]:
        recommendations.append("⚠️ Set GOOGLE_API_KEY for full AI capabilities")
    
    if not env_checks["pinecone_configured"]:
        recommendations.append("⚠️ Configure Pinecone for better vector search")
    
    if not env_checks["mongodb_configured"]:
        recommendations.append("💡 Consider MongoDB for conversation history")
    
    recommendations.extend([
        "📝 Upload high-quality, well-structured documents",
        "🎯 Use specific, fact-based questions for best results",
        "✅ Verify important facts using the fact-verification endpoint",
        "📊 Monitor confidence scores in responses",
        "🔍 Use search endpoint to validate information availability"
    ])
    
    return recommendations

if __name__ == "__main__":
    # Print current configuration
    print("RAG Accuracy Configuration:")
    print(f"Min Confidence (High): {ACCURACY_CONFIG.MIN_CONFIDENCE_HIGH}")
    print(f"Min Confidence (Good): {ACCURACY_CONFIG.MIN_CONFIDENCE_GOOD}")
    print(f"Strict Fact Mode: {ACCURACY_CONFIG.STRICT_FACT_MODE}")
    print(f"Temperature (Fact Check): {ACCURACY_CONFIG.TEMPERATURE_FACT_VERIFICATION}")
    
    print("\nEnvironment Checks:")
    for check, status in check_accuracy_environment().items():
        print(f"{check}: {'✅' if status else '❌'}")
    
    print("\nRecommendations:")
    for rec in get_accuracy_recommendations():
        print(f"  {rec}")
