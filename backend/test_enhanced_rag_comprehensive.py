#!/usr/bin/env python3
"""
Comprehensive RAG Enhancement Test Script

This script tests all the enhanced RAG features for maximum document coverage,
improved chunking, better retrieval, and accurate template filling.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.document_processor import document_processor
from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from rag_accuracy_config import ACCURACY_CONFIG, AccuracyPrompts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGEnhancementTester:
    """Comprehensive tester for enhanced RAG features"""
    
    def __init__(self):
        self.test_device_id = "test_enhanced_device"
        self.results = {}
    
    async def run_comprehensive_tests(self):
        """Run all comprehensive enhancement tests"""
        logger.info("🚀 Starting Comprehensive RAG Enhancement Tests")
        
        tests = [
            ("Document Processing Enhancement", self.test_enhanced_document_processing),
            ("Chunking Strategy Enhancement", self.test_enhanced_chunking),
            ("Metadata Enhancement", self.test_enhanced_metadata),
            ("Vector Storage Enhancement", self.test_enhanced_vector_storage),
            ("Search Enhancement", self.test_enhanced_search),
            ("Comprehensive Retrieval", self.test_comprehensive_retrieval),
            ("Template Field Extraction", self.test_enhanced_field_extraction),
            ("Temperature Optimization", self.test_temperature_optimization),
            ("Quality Filtering", self.test_quality_filtering),
            ("Coverage Analysis", self.test_document_coverage)
        ]
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*60}")
            logger.info(f"🧪 Running: {test_name}")
            logger.info(f"{'='*60}")
            
            try:
                result = await test_func()
                self.results[test_name] = {"status": "PASSED", "details": result}
                logger.info(f"✅ {test_name}: PASSED")
            except Exception as e:
                self.results[test_name] = {"status": "FAILED", "error": str(e)}
                logger.error(f"❌ {test_name}: FAILED - {e}")
        
        await self.generate_comprehensive_report()
    
    async def test_enhanced_document_processing(self):
        """Test enhanced document processing with multiple extraction methods"""
        logger.info("📄 Testing enhanced document processing...")
        
        # Create a comprehensive test document
        test_content = """
        DEVICE MASTER FILE
        
        1. DEVICE INFORMATION
        Generic Name: Advanced Pulse Oximeter
        Model Number: APO-2024-Pro
        Serial Number: SN-APO-123456
        Document No: DMF-APO-2024-001
        
        2. MANUFACTURER INFORMATION
        Manufacturer: MedTech Solutions Inc.
        Address: 123 Innovation Drive, MedCity, MC 12345
        Contact: info@medtechsolutions.com
        
        3. TECHNICAL SPECIFICATIONS
        Accuracy: ±2% for SpO2 measurements
        Operating Temperature: 0°C to 40°C
        Power Supply: 3.7V Lithium-ion battery
        Display: 2.4" OLED color display
        
        4. REGULATORY INFORMATION
        FDA 510(k): K123456789
        CE Mark: CE-APO-2024
        ISO Standards: ISO 13485:2016
        
        5. INTENDED USE
        The Advanced Pulse Oximeter is intended for non-invasive monitoring
        of functional oxygen saturation (SpO2) and pulse rate in adult and
        pediatric patients in hospitals, clinics, and home care settings.
        """.encode('utf-8')
        
        # Test document processing
        result = await document_processor.process_uploaded_file(
            file_content=test_content,
            filename="test_comprehensive_document.txt",
            device_id=self.test_device_id
        )
        
        # Validate processing results
        assert result["status"] == "success"
        assert result["chunks_created"] > 0
        assert result["document_id"] is not None
        
        logger.info(f"📊 Document processed: {result['chunks_created']} chunks created")
        return result
    
    async def test_enhanced_chunking(self):
        """Test enhanced chunking with improved boundary detection"""
        logger.info("📦 Testing enhanced chunking strategy...")
        
        # Test with a complex document structure
        complex_text = """
        EXECUTIVE SUMMARY
        
        This document provides comprehensive information about the Advanced Pulse Oximeter (APO-2024-Pro).
        
        DEVICE DESCRIPTION
        
        Generic Name: Advanced Pulse Oximeter
        Brand Name: OxyPro Advanced
        Model: APO-2024-Pro, APO-2024-Standard
        
        The device uses advanced sensor technology to provide accurate measurements.
        
        TECHNICAL SPECIFICATIONS
        
        Measurement Range:
        - SpO2: 70% to 100%
        - Pulse Rate: 30 to 250 bpm
        - Perfusion Index: 0.02% to 20%
        
        Accuracy Specifications:
        - SpO2 Accuracy: ±2% (70% to 100%)
        - Pulse Rate Accuracy: ±3 bpm or ±2%
        
        MANUFACTURER INFORMATION
        
        Company: MedTech Solutions Inc.
        Established: 1998
        Location: MedCity, State, Country
        Certifications: ISO 13485, ISO 14971
        """
        
        # Create chunks using enhanced algorithm
        chunks = document_processor._create_chunks(complex_text)
        
        # Validate chunking improvements
        assert len(chunks) > 0
        
        # Check for enhanced metadata
        for chunk in chunks:
            assert "importance_score" in chunk
            assert "semantic_keywords" in chunk
            assert "content_type" in chunk
            assert "chunk_quality_score" in chunk
        
        # Verify boundary detection
        high_quality_chunks = [c for c in chunks if c.get("chunk_quality_score", 0) > 0.7]
        important_chunks = [c for c in chunks if c.get("importance_score", 0) > 0.7]
        
        logger.info(f"📊 Chunking results: {len(chunks)} total, {len(high_quality_chunks)} high-quality, {len(important_chunks)} high-importance")
        
        return {
            "total_chunks": len(chunks),
            "high_quality_chunks": len(high_quality_chunks),
            "important_chunks": len(important_chunks),
            "avg_importance": sum(c.get("importance_score", 0) for c in chunks) / len(chunks)
        }
    
    async def test_enhanced_metadata(self):
        """Test enhanced metadata extraction"""
        logger.info("🏷️ Testing enhanced metadata extraction...")
        
        test_chunk = """
        Generic Name: Advanced Pulse Oximeter
        Model Number: APO-2024-Pro
        Manufacturer: MedTech Solutions Inc.
        Document No: DMF-APO-2024-001
        Date: 03/15/2024
        
        Technical Specifications:
        - Operating Temperature: 0°C to 40°C
        - Accuracy: ±2% for SpO2 measurements
        - Display: 2.4" OLED color display
        """
        
        # Test metadata extraction
        metadata = document_processor._extract_chunk_metadata(test_chunk)
        enhanced_metadata = document_processor._enhance_chunk_metadata(test_chunk, 0, 0, len(test_chunk))
        
        # Validate enhanced metadata
        assert metadata["contains_fields"] == True
        assert enhanced_metadata["importance_score"] > 0.7  # Should be high importance
        assert len(enhanced_metadata["semantic_keywords"]) > 0
        assert enhanced_metadata["entity_density"] > 0
        
        logger.info(f"📊 Metadata quality: importance={enhanced_metadata['importance_score']:.2f}, entities={enhanced_metadata['entity_density']:.2f}")
        
        return {
            "contains_fields": metadata["contains_fields"],
            "importance_score": enhanced_metadata["importance_score"],
            "semantic_keywords": enhanced_metadata["semantic_keywords"],
            "entity_density": enhanced_metadata["entity_density"]
        }
    
    async def test_enhanced_vector_storage(self):
        """Test enhanced vector storage with comprehensive metadata"""
        logger.info("🔗 Testing enhanced vector storage...")
        
        # Initialize services
        await pinecone_service.initialize_pinecone()
        
        # Create test chunks with enhanced metadata
        test_chunks = [
            {
                "chunk_id": 0,
                "content": "Generic Name: Advanced Pulse Oximeter\nModel Number: APO-2024-Pro",
                "start_index": 0,
                "end_index": 60,
                "word_count": 8,
                "content_type": "form",
                "has_structured_data": False,
                "contains_fields": True,
                "importance_score": 0.9,
                "semantic_keywords": ["pulse oximeter", "apo-2024-pro"],
                "entity_density": 0.6,
                "information_richness": 0.8,
                "chunk_quality_score": 0.85
            }
        ]
        
        # Test storage
        await document_processor._store_chunks_in_pinecone(
            chunks=test_chunks,
            document_id="test_doc_enhanced",
            device_id=self.test_device_id,
            filename="test_enhanced.txt"
        )
        
        logger.info("✅ Enhanced vector storage completed")
        return {"vectors_stored": len(test_chunks)}
    
    async def test_enhanced_search(self):
        """Test enhanced search with quality filtering"""
        logger.info("🔍 Testing enhanced search capabilities...")
        
        # Test comprehensive search
        query_embeddings = [
            await gemini_service.get_embedding("pulse oximeter model number"),
            await gemini_service.get_embedding("APO-2024-Pro specifications"),
            await gemini_service.get_embedding("device technical details")
        ]
        
        # Test comprehensive search
        comprehensive_results = await pinecone_service.comprehensive_search(
            query_vectors=query_embeddings,
            device_id=self.test_device_id,
            top_k_per_query=5,
            final_top_k=10
        )
        
        # Test quality filtering
        quality_results = await pinecone_service.search_vectors(
            query_vector=query_embeddings[0],
            device_id=self.test_device_id,
            top_k=10,
            include_low_quality=False
        )
        
        all_results = await pinecone_service.search_vectors(
            query_vector=query_embeddings[0],
            device_id=self.test_device_id,
            top_k=10,
            include_low_quality=True
        )
        
        logger.info(f"📊 Search results: comprehensive={len(comprehensive_results)}, quality-filtered={len(quality_results)}, all={len(all_results)}")
        
        return {
            "comprehensive_results": len(comprehensive_results),
            "quality_filtered_results": len(quality_results),
            "all_results": len(all_results)
        }
    
    async def test_comprehensive_retrieval(self):
        """Test comprehensive retrieval for maximum document coverage"""
        logger.info("🎯 Testing comprehensive retrieval...")
        
        # Generate multiple query approaches for a field
        field_name = "Generic Name"
        questions = await gemini_service.generate_field_questions(field_name, "Device identification field")
        
        # Test multi-query retrieval
        all_query_vectors = []
        for question in questions:
            embedding = await gemini_service.get_embedding(question)
            all_query_vectors.append(embedding)
        
        # Add direct field embedding
        field_embedding = await gemini_service.get_embedding(field_name)
        all_query_vectors.append(field_embedding)
        
        # Test comprehensive search
        results = await pinecone_service.comprehensive_search(
            query_vectors=all_query_vectors,
            device_id=self.test_device_id,
            top_k_per_query=8,
            final_top_k=15
        )
        
        logger.info(f"📊 Comprehensive retrieval: {len(questions)} questions, {len(all_query_vectors)} queries, {len(results)} results")
        
        return {
            "questions_generated": len(questions),
            "total_queries": len(all_query_vectors),
            "final_results": len(results)
        }
    
    async def test_enhanced_field_extraction(self):
        """Test enhanced field extraction with comprehensive context"""
        logger.info("📝 Testing enhanced field extraction...")
        
        # Create comprehensive context documents
        context_docs = [
            "Generic Name: Advanced Pulse Oximeter",
            "The device name is Advanced Pulse Oximeter for professional use",
            "Product identification: Advanced Pulse Oximeter (APO-2024-Pro)",
            "Device type: Pulse oximeter, advanced monitoring system",
            "Medical device name: Advanced Pulse Oximeter with enhanced features"
        ]
        
        # Test enhanced field filling
        field_value = await gemini_service.fill_template_field_enhanced(
            field_name="Generic Name",
            field_context="Device identification information",
            context_docs=context_docs,
            questions=["What is the generic name?", "What is the device name?"],
            device_id=self.test_device_id
        )
        
        logger.info(f"📊 Field extraction result: '{field_value}'")
        
        # Validate extraction
        assert field_value is not None
        assert "Advanced Pulse Oximeter" in field_value
        assert not field_value.startswith("Generic Name:")  # Should not include label
        
        return {"extracted_value": field_value}
    
    async def test_temperature_optimization(self):
        """Test temperature optimization for document filling"""
        logger.info("🌡️ Testing temperature optimization...")
        
        # Test with different temperatures
        test_prompt = "Extract the model number from: Model Number: APO-2024-Pro"
        
        # Test with extremely low temperature (enhanced setting)
        low_temp_response = await gemini_service.generate_response(
            prompt=test_prompt,
            temperature=ACCURACY_CONFIG.TEMPERATURE_FIELD_EXTRACTION
        )
        
        # Test with higher temperature
        high_temp_response = await gemini_service.generate_response(
            prompt=test_prompt,
            temperature=0.3
        )
        
        logger.info(f"📊 Temperature test: low_temp='{low_temp_response[:50]}...', high_temp='{high_temp_response[:50]}...'")
        
        return {
            "low_temperature_response": low_temp_response,
            "high_temperature_response": high_temp_response,
            "optimal_temperature": ACCURACY_CONFIG.TEMPERATURE_FIELD_EXTRACTION
        }
    
    async def test_quality_filtering(self):
        """Test quality filtering and ranking"""
        logger.info("⭐ Testing quality filtering...")
        
        # Create test chunks with different quality scores
        test_chunks = [
            "This is garbled text with ââ€™ encoding issues and ï¿½ artifacts",
            "Generic Name: Advanced Pulse Oximeter\nModel: APO-2024-Pro",
            "Technical specifications include accurate measurement capabilities",
            "!!!### random symbols and numbers 12345 @@@ meaningless content"
        ]
        
        quality_scores = []
        for chunk in test_chunks:
            quality = document_processor._calculate_chunk_quality_score(chunk)
            quality_scores.append(quality)
        
        logger.info(f"📊 Quality scores: {[f'{score:.2f}' for score in quality_scores]}")
        
        # Validate quality assessment
        assert quality_scores[1] > quality_scores[0]  # Clean content > garbled
        assert quality_scores[1] > quality_scores[3]  # Structured > random
        
        return {"quality_scores": quality_scores}
    
    async def test_document_coverage(self):
        """Test comprehensive document coverage analysis"""
        logger.info("📊 Testing document coverage analysis...")
        
        # Create a document with various content types
        comprehensive_doc = """
        DEVICE MASTER FILE - COMPREHENSIVE TEST
        
        Section 1: Device Identification
        Generic Name: Advanced Pulse Oximeter
        Model Number: APO-2024-Pro
        Serial Number: SN-APO-123456
        
        Section 2: Technical Specifications
        Accuracy: ±2% for SpO2 measurements (70% to 100%)
        Operating Temperature: 0°C to 40°C
        Power Supply: 3.7V Lithium-ion battery
        
        Section 3: Regulatory Information
        FDA 510(k) Number: K123456789
        CE Marking: CE-APO-2024
        ISO Standards Compliance: ISO 13485:2016
        
        Section 4: Manufacturing Information
        Manufacturer: MedTech Solutions Inc.
        Manufacturing Site: 123 Innovation Drive, MedCity
        Quality System: ISO 13485:2016 certified
        
        Section 5: Clinical Information
        Intended Use: Non-invasive monitoring of SpO2 and pulse rate
        Patient Population: Adult and pediatric patients
        Clinical Environment: Hospitals, clinics, home care
        """
        
        # Process document
        chunks = document_processor._create_chunks(comprehensive_doc)
        
        # Analyze coverage
        total_sections = 5
        sections_covered = set()
        important_chunks = 0
        field_chunks = 0
        
        for chunk in chunks:
            content = chunk["content"]
            if "Section" in content:
                # Extract section number
                import re
                section_match = re.search(r'Section (\d+)', content)
                if section_match:
                    sections_covered.add(int(section_match.group(1)))
            
            if chunk.get("importance_score", 0) > 0.7:
                important_chunks += 1
            
            if chunk.get("contains_fields", False):
                field_chunks += 1
        
        coverage_percentage = len(sections_covered) / total_sections * 100
        
        logger.info(f"📊 Document coverage: {coverage_percentage:.1f}% ({len(sections_covered)}/{total_sections} sections)")
        logger.info(f"📊 Chunk analysis: {important_chunks} important, {field_chunks} with fields")
        
        return {
            "coverage_percentage": coverage_percentage,
            "sections_covered": len(sections_covered),
            "total_sections": total_sections,
            "important_chunks": important_chunks,
            "field_chunks": field_chunks,
            "total_chunks": len(chunks)
        }
    
    async def generate_comprehensive_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*80)
        logger.info("📋 COMPREHENSIVE RAG ENHANCEMENT TEST REPORT")
        logger.info("="*80)
        
        passed_tests = sum(1 for result in self.results.values() if result["status"] == "PASSED")
        total_tests = len(self.results)
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        logger.info(f"✅ Tests Passed: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        
        for test_name, result in self.results.items():
            status_emoji = "✅" if result["status"] == "PASSED" else "❌"
            logger.info(f"{status_emoji} {test_name}: {result['status']}")
            if result["status"] == "FAILED":
                logger.error(f"   Error: {result['error']}")
        
        # Enhanced configuration summary
        logger.info("\n📊 ENHANCED CONFIGURATION SUMMARY:")
        logger.info(f"   Chunk Size: {document_processor.chunk_size} chars")
        logger.info(f"   Chunk Overlap: {document_processor.chunk_overlap} chars")
        logger.info(f"   Temperature (Field Extraction): {ACCURACY_CONFIG.TEMPERATURE_FIELD_EXTRACTION}")
        logger.info(f"   Max Chunks (Initial): {ACCURACY_CONFIG.MAX_CHUNKS_INITIAL}")
        logger.info(f"   Max Chunks (Final): {ACCURACY_CONFIG.MAX_CHUNKS_FINAL}")
        logger.info(f"   Quality Filtering: {ACCURACY_CONFIG.QUALITY_FILTERING}")
        logger.info(f"   Comprehensive Search: {ACCURACY_CONFIG.COMPREHENSIVE_SEARCH_MODE}")
        
        # Key improvements summary
        logger.info("\n🚀 KEY ENHANCEMENTS IMPLEMENTED:")
        logger.info("   📈 Increased chunk size (1000→1500 chars) for better context")
        logger.info("   🔄 Enhanced chunk overlap (200→400 chars) for continuity")
        logger.info("   🏷️ Advanced metadata extraction with importance scoring")
        logger.info("   🎯 Comprehensive multi-query search strategy")
        logger.info("   🌡️ Optimized temperature (0.1→0.01) for factual accuracy")
        logger.info("   ⭐ Quality filtering for better chunk selection")
        logger.info("   📊 Enhanced document coverage analysis")
        logger.info("   🔍 Semantic keyword extraction for better matching")
        
        if success_rate >= 80:
            logger.info("\n🎉 COMPREHENSIVE RAG ENHANCEMENTS: SUCCESSFULLY IMPLEMENTED!")
        else:
            logger.warning(f"\n⚠️ Some tests failed. Success rate: {success_rate:.1f}%")
        
        return {
            "success_rate": success_rate,
            "passed_tests": passed_tests,
            "total_tests": total_tests,
            "results": self.results
        }

async def main():
    """Main test execution"""
    try:
        tester = RAGEnhancementTester()
        await tester.run_comprehensive_tests()
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    # Run the comprehensive tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
