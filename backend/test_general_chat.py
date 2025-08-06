#!/usr/bin/env python3
"""
Test general chat functionality to ensure RAG understands various question types
including document summaries, general questions, and conversational queries.
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.gemini_service import GeminiService
from app.services.pinecone_service import PineconeService
from app.services.document_processor import DocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_general_chat_capabilities():
    """Test various types of general questions to ensure RAG handles them well"""
    
    print("🧪 TESTING GENERAL CHAT CAPABILITIES")
    print("=" * 60)
    
    # Initialize services
    gemini_service = GeminiService()
    pinecone_service = PineconeService()
    document_processor = DocumentProcessor()
    
    # Test device ID
    test_device_id = "test_general_chat"
    
    # Sample document content to upload for testing
    sample_documents = [
        {
            "filename": "device_overview.txt",
            "content": """
Advanced Pulse Oximeter APO-2024-Pro
====================================

DEVICE DESCRIPTION
The Advanced Pulse Oximeter (APO-2024-Pro) is a state-of-the-art medical device designed for accurate measurement of blood oxygen saturation (SpO2) and pulse rate in clinical and home settings.

MANUFACTURER INFORMATION
Company: MedTech Solutions Inc.
Location: Boston, Massachusetts, USA
Established: 1998
Certifications: ISO 13485, ISO 14971, FDA 510(k) cleared

TECHNICAL SPECIFICATIONS
- SpO2 Range: 70% to 100%
- SpO2 Accuracy: ±2% (70-100%)
- Pulse Rate Range: 30 to 250 bpm
- Pulse Rate Accuracy: ±3 bpm or ±2%
- Power: 2 AA batteries
- Display: OLED color display
- Weight: 65 grams
- Dimensions: 62mm x 37mm x 32mm

INTENDED USE
The device is intended for non-invasive measurement of functional oxygen saturation of arterial hemoglobin and pulse rate in adults, children, and neonates in hospitals, clinics, and home care environments.

SAFETY FEATURES
- Automatic power-off after 8 seconds
- Low battery indicator
- Motion artifact detection
- Weak signal detection
- Perfusion index display

REGULATORY STATUS
- FDA 510(k) Cleared (K201234567)
- CE Marked (EU MDR compliant)
- Health Canada Licensed (MDL 12345)
- Meets IEC 80601-2-61 standards
"""
        },
        {
            "filename": "clinical_studies.txt", 
            "content": """
Clinical Studies for APO-2024-Pro Pulse Oximeter
===============================================

VALIDATION STUDY OVERVIEW
A comprehensive clinical validation study was conducted at Massachusetts General Hospital from January 2023 to March 2023 to validate the accuracy of the APO-2024-Pro pulse oximeter.

STUDY DESIGN
- Study Type: Prospective, controlled validation study
- Participants: 120 healthy volunteers (age 18-65)
- Reference Standard: ABG analysis with CO-oximetry
- Test Conditions: Motion, low perfusion, ambient light

ACCURACY RESULTS
SpO2 Accuracy:
- Overall Arms: 1.8% (within ±2% specification)
- Motion Conditions: 2.1% Arms
- Low Perfusion: 2.0% Arms
- Ambient Light: 1.9% Arms

Pulse Rate Accuracy:
- Overall: ±2.1 bpm (within ±3 bpm specification)
- Motion Conditions: ±2.8 bpm
- Low Perfusion: ±2.3 bpm

STATISTICAL ANALYSIS
- Sample Size: n=120 subjects
- Data Points: 3,600 SpO2 measurements
- Statistical Method: Bland-Altman analysis
- Confidence Interval: 95%

CONCLUSION
The APO-2024-Pro demonstrated excellent accuracy and reliability across all tested conditions, meeting all FDA requirements for pulse oximeter accuracy.

ADVERSE EVENTS
No adverse events were reported during the clinical study.
"""
        }
    ]
    
    # Upload test documents
    print("📄 Uploading test documents...")
    for doc in sample_documents:
        try:
            # Process document
            chunks = document_processor._create_chunks(doc["content"])
            
            # Generate embeddings and store
            for i, chunk in enumerate(chunks):
                embedding = await gemini_service.get_embedding(chunk["content"])
                await pinecone_service.upsert_vectors(
                    vectors=[{
                        "id": f"{test_device_id}_{doc['filename']}_{i}",
                        "values": embedding,
                        "metadata": {
                            "device_id": test_device_id,
                            "filename": doc["filename"],
                            "chunk_id": i,
                            "document_id": f"test_{doc['filename']}"
                        }
                    }],
                    device_id=test_device_id
                )
            
            print(f"✅ Uploaded {doc['filename']}: {len(chunks)} chunks")
            
        except Exception as e:
            print(f"❌ Failed to upload {doc['filename']}: {e}")
    
    # Test various question types
    test_questions = [
        # Summary questions
        {
            "question": "Summarize this document",
            "expected_type": "summary",
            "description": "General document summary request"
        },
        {
            "question": "Give me a brief overview of the device",
            "expected_type": "summary", 
            "description": "Device overview request"
        },
        {
            "question": "What are the main features of this product?",
            "expected_type": "features",
            "description": "Feature summary request"
        },
        
        # Specific information requests
        {
            "question": "What is the accuracy of this device?",
            "expected_type": "specific",
            "description": "Specific technical detail"
        },
        {
            "question": "Who makes this device?",
            "expected_type": "specific",
            "description": "Manufacturer information"
        },
        {
            "question": "What is the model number?",
            "expected_type": "specific", 
            "description": "Model identification"
        },
        
        # Contextual questions
        {
            "question": "Is this device FDA approved?",
            "expected_type": "contextual",
            "description": "Regulatory status inquiry"
        },
        {
            "question": "Can this be used at home?",
            "expected_type": "contextual",
            "description": "Usage context question"
        },
        
        # Analytical questions
        {
            "question": "What were the results of clinical studies?",
            "expected_type": "analytical",
            "description": "Study results analysis"
        },
        {
            "question": "How does this compare to other devices?",
            "expected_type": "analytical",
            "description": "Comparative analysis"
        }
    ]
    
    print(f"\n🔍 Testing {len(test_questions)} different question types...")
    print("-" * 60)
    
    results = []
    
    for i, test in enumerate(test_questions, 1):
        print(f"\n📝 Test {i}: {test['description']}")
        print(f"❓ Question: {test['question']}")
        
        try:
            # Generate embedding for the question
            query_embedding = await gemini_service.get_embedding(test["question"])
            
            # Search for relevant documents
            search_results = await pinecone_service.search_vectors(
                query_vector=query_embedding,
                device_id=test_device_id,
                top_k=10
            )
            
            # Filter results
            filtered_results = [result for result in search_results if result.score >= 0.6]
            
            # Extract context
            context_docs = []
            for result in filtered_results[:5]:  # Top 5 results
                context_docs.append(result.content)
            
            if context_docs:
                # Create enhanced prompt for general questions
                enhanced_prompt = f"""You are a helpful AI assistant analyzing medical device documentation. Answer the user's question naturally and comprehensively based on the provided documents.

User Question: "{test['question']}"

Available Information:
{chr(10).join([f"Document {i+1}: {doc}" for i, doc in enumerate(context_docs)])}

Instructions:
- If asked for a summary, provide a comprehensive overview covering key aspects
- If asked about specific details, give precise information with context
- If asked analytical questions, synthesize information from multiple sources
- Write in clear, natural language as if explaining to a colleague
- Include relevant details that help answer the question completely
- If information is missing, mention what's not available

Answer:"""
                
                response = await gemini_service.generate_response(
                    prompt=enhanced_prompt,
                    context=None,  # Context already in prompt
                    temperature=0.2,  # Slightly higher for more natural responses
                    max_tokens=2000
                )
                
                print(f"✅ Response:")
                print(f"{response}")
                print(f"📊 Found {len(filtered_results)} relevant chunks")
                
                # Evaluate response quality
                response_length = len(response.split())
                has_specific_info = any(keyword in response.lower() for keyword in ["apo-2024", "medtech", "accuracy", "fda", "clinical"])
                is_comprehensive = response_length >= 30  # Reasonable length for good answers
                
                results.append({
                    "question": test["question"],
                    "question_type": test["expected_type"],
                    "response_length": response_length,
                    "has_specific_info": has_specific_info,
                    "is_comprehensive": is_comprehensive,
                    "chunks_found": len(filtered_results),
                    "success": has_specific_info and is_comprehensive
                })
                
            else:
                print(f"❌ No relevant documents found")
                results.append({
                    "question": test["question"],
                    "question_type": test["expected_type"],
                    "response_length": 0,
                    "has_specific_info": False,
                    "is_comprehensive": False,
                    "chunks_found": 0,
                    "success": False
                })
            
        except Exception as e:
            print(f"❌ Error processing question: {e}")
            results.append({
                "question": test["question"],
                "question_type": test["expected_type"],
                "error": str(e),
                "success": False
            })
    
    # Generate test summary
    print(f"\n📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r.get("success", False))
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"✅ Success Rate: {success_rate:.1f}% ({successful_tests}/{total_tests})")
    
    # Analyze by question type
    by_type = {}
    for result in results:
        q_type = result["question_type"]
        if q_type not in by_type:
            by_type[q_type] = {"total": 0, "success": 0}
        by_type[q_type]["total"] += 1
        if result.get("success", False):
            by_type[q_type]["success"] += 1
    
    print(f"\n📈 Performance by Question Type:")
    for q_type, stats in by_type.items():
        rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        print(f"  {q_type.title()}: {rate:.1f}% ({stats['success']}/{stats['total']})")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    if success_rate >= 80:
        print("✅ System handles general questions well!")
        print("✅ Good context retrieval and response generation")
    elif success_rate >= 60:
        print("⚠️ System works but could be improved:")
        print("  - Consider adjusting search thresholds")
        print("  - Enhance prompt templates for better responses")
    else:
        print("❌ System needs significant improvements:")
        print("  - Check embedding quality and search relevance")
        print("  - Improve prompt engineering for better responses")
        print("  - Verify document processing and chunking")
    
    # Cleanup - Remove test vectors
    try:
        await pinecone_service.delete_by_device(test_device_id)
        print(f"\n🧹 Cleaned up test data for device {test_device_id}")
    except Exception as e:
        print(f"⚠️ Failed to cleanup test data: {e}")
    
    return success_rate >= 70  # Return True if acceptable performance

if __name__ == "__main__":
    asyncio.run(test_general_chat_capabilities())
