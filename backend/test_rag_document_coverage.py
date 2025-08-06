#!/usr/bin/env python3
"""
Comprehensive RAG Document Coverage Test

This script tests that the RAG system is:
1. Processing ALL documents correctly
2. Creating comprehensive chunks from each document
3. Storing all chunks with enhanced metadata
4. Retrieving information from MULTIPLE documents collectively
5. Finding the BEST relevant information across all documents
6. Using comprehensive search strategies for template filling
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
import tempfile

# Add the backend directory to Python path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.services.document_processor import document_processor
from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGDocumentCoverageTest:
    """Test RAG system for comprehensive document coverage"""
    
    def __init__(self):
        self.test_device_id = "test_comprehensive_coverage"
        self.test_documents = []
        self.processed_docs = []
    
    def create_test_documents(self):
        """Create multiple test documents with overlapping and unique information"""
        
        # Document 1: Device Basic Information
        doc1_content = """
        DEVICE MASTER FILE - BASIC INFORMATION
        
        Generic Name: Advanced Multi-Parameter Patient Monitor
        Brand Name: VitalWatch Pro
        Model Numbers: VW-2024-Pro, VW-2024-Standard, VW-2024-Compact
        Serial Number Range: VW240001-VW249999
        
        Manufacturer Information:
        Company: VitalTech Medical Systems Inc.
        Address: 456 Healthcare Boulevard, MedCenter City, MC 67890
        Phone: +1-555-MEDICAL (635-4225)
        Email: info@vitaltech-medical.com
        Website: www.vitaltech-medical.com
        
        Regulatory Information:
        FDA 510(k) Number: K987654321
        FDA Classification: Class II Medical Device
        Product Code: DQA (Patient Monitor)
        
        Document Information:
        Document Number: DMF-VW-2024-001
        Version: 2.1
        Date: March 15, 2024
        Prepared by: Dr. Sarah Johnson, Regulatory Affairs
        """.encode('utf-8')
        
        # Document 2: Technical Specifications
        doc2_content = """
        TECHNICAL SPECIFICATIONS DOCUMENT
        VitalWatch Pro Patient Monitor Series
        
        Model: VW-2024-Pro (Primary Model)
        
        Technical Specifications:
        - Display: 15.6" high-resolution color touchscreen
        - Parameters: ECG, SpO2, NIBP, Temperature, Respiration
        - ECG Channels: 12-lead capability with arrhythmia detection
        - SpO2 Accuracy: ±2% (70-100% range)
        - NIBP Range: 30-270 mmHg (systolic), 10-215 mmHg (diastolic)
        - Temperature Range: 25°C to 45°C (±0.1°C accuracy)
        
        Power Specifications:
        - AC Input: 100-240V, 50/60Hz
        - Battery: Lithium-ion, 4 hours continuous operation
        - Power Consumption: 150W maximum
        
        Environmental Conditions:
        - Operating Temperature: 0°C to 40°C
        - Storage Temperature: -20°C to 60°C
        - Humidity: 15% to 85% RH (non-condensing)
        - Altitude: Up to 3000m
        
        Connectivity:
        - Ethernet: 10/100/1000 Mbps
        - Wi-Fi: 802.11 a/b/g/n/ac
        - USB: 2x USB 3.0 ports
        - Serial: RS-232 interface
        """.encode('utf-8')
        
        # Document 3: Safety and Compliance
        doc3_content = """
        SAFETY AND COMPLIANCE DOCUMENTATION
        VitalWatch Pro Patient Monitor
        
        Safety Classifications:
        - Type of Protection: Class I equipment
        - Applied Parts: Type CF (cardiac floating)
        - IPX Rating: IPX1 (drip-proof)
        
        Standards Compliance:
        - IEC 60601-1:2012 (Medical electrical equipment)
        - IEC 60601-1-2:2014 (EMC requirements)
        - IEC 60601-2-49:2011 (Patient monitoring equipment)
        - ISO 13485:2016 (Quality management systems)
        - ISO 14971:2019 (Risk management)
        
        Risk Management:
        Risk Control Measures implemented include:
        - Electrical safety isolation
        - Alarm system redundancy
        - Software safety architecture
        - User training requirements
        - Preventive maintenance protocols
        
        Clinical Evaluation:
        Clinical studies conducted at:
        - St. Mary's Medical Center (200 patients)
        - University Hospital Network (350 patients)
        - Regional Medical Institute (150 patients)
        
        Intended Use:
        The VitalWatch Pro is intended for continuous monitoring of vital signs
        in adult, pediatric, and neonatal patients in hospital environments
        including ICU, general wards, and emergency departments.
        
        Contraindications:
        - Not suitable for MRI environments
        - Not for use during defibrillation
        """.encode('utf-8')
        
        # Document 4: Manufacturing and Quality
        doc4_content = """
        MANUFACTURING AND QUALITY INFORMATION
        VitalTech Medical Systems Inc.
        
        Manufacturing Facility:
        Primary Site: 456 Healthcare Boulevard, MedCenter City, MC 67890
        Secondary Site: 789 Innovation Park, TechValley, TV 12345
        
        Quality System:
        - ISO 13485:2016 Certified (Certificate: QS-VT-2024-001)
        - FDA Registered Facility (Registration: 12345678)
        - Health Canada License: MDL-001234
        - CE Notified Body: TÜV SÜD (NB 0123)
        
        Manufacturing Process:
        - Surface Mount Technology (SMT) assembly
        - Automated Optical Inspection (AOI)
        - In-Circuit Testing (ICT)
        - Functional testing protocols
        - Final quality assurance inspection
        
        Supplier Information:
        Key Component Suppliers:
        - Display Module: TechDisplay Corp (TDC-15.6-HD)
        - Main Processor: Advanced Semiconductors (AS-ARM-2024)
        - Sensors: BioSensor Technologies (BST-Multi-V2)
        - Power Supply: PowerTech Solutions (PTS-150W-Medical)
        
        Quality Control:
        - Incoming inspection: 100% for critical components
        - Process control: Statistical process control (SPC)
        - Final testing: 100% functional testing
        - Documentation: Complete traceability records
        """.encode('utf-8')
        
        self.test_documents = [
            ("device_basic_info.txt", doc1_content),
            ("technical_specifications.txt", doc2_content),
            ("safety_compliance.txt", doc3_content),
            ("manufacturing_quality.txt", doc4_content)
        ]
        
        logger.info(f"📄 Created {len(self.test_documents)} test documents")
        return self.test_documents
    
    async def test_document_processing_coverage(self):
        """Test that all documents are processed with comprehensive chunking"""
        logger.info("🔍 Testing document processing coverage...")
        
        total_chunks = 0
        processing_results = []
        
        for filename, content in self.test_documents:
            logger.info(f"📄 Processing {filename}...")
            
            result = await document_processor.process_uploaded_file(
                file_content=content,
                filename=filename,
                device_id=self.test_device_id
            )
            
            processing_results.append(result)
            total_chunks += result["chunks_created"]
            self.processed_docs.append(result["document_id"])
            
            logger.info(f"✅ {filename}: {result['chunks_created']} chunks created")
        
        logger.info(f"📊 Total chunks across all documents: {total_chunks}")
        
        # Validate comprehensive processing
        assert len(processing_results) == len(self.test_documents)
        assert total_chunks > 15  # Should have substantial chunks
        assert all(result["status"] == "success" for result in processing_results)
        
        return {
            "documents_processed": len(processing_results),
            "total_chunks": total_chunks,
            "processing_results": processing_results
        }
    
    async def test_comprehensive_search_across_documents(self):
        """Test that search finds information across ALL documents"""
        logger.info("🔍 Testing comprehensive search across all documents...")
        
        # Initialize Pinecone service
        await pinecone_service.initialize_pinecone()
        
        # Test queries that should find information from different documents
        test_queries = [
            {
                "query": "VitalWatch Pro model numbers",
                "expected_docs": ["device_basic_info.txt"],  # Should find VW-2024-Pro, etc.
                "field": "Model Numbers"
            },
            {
                "query": "technical specifications display screen",
                "expected_docs": ["technical_specifications.txt"],  # Should find 15.6" touchscreen
                "field": "Display"
            },
            {
                "query": "FDA 510k number regulatory",
                "expected_docs": ["device_basic_info.txt"],  # Should find K987654321
                "field": "FDA 510(k) Number"
            },
            {
                "query": "manufacturing facility address location",
                "expected_docs": ["device_basic_info.txt", "manufacturing_quality.txt"],  # Both have address info
                "field": "Address"
            },
            {
                "query": "risk control measures safety",
                "expected_docs": ["safety_compliance.txt"],  # Should find risk management info
                "field": "Risk Control Measures"
            }
        ]
        
        search_results = {}
        
        for test_case in test_queries:
            query = test_case["query"]
            logger.info(f"🔍 Testing query: {query}")
            
            # Generate embedding for query
            query_embedding = await gemini_service.get_embedding(query)
            
            # Search with enhanced parameters
            results = await pinecone_service.search_vectors(
                query_vector=query_embedding,
                device_id=self.test_device_id,
                top_k=10,  # Get more results to ensure comprehensive coverage
                include_low_quality=False
            )
            
            logger.info(f"📊 Found {len(results)} results for '{query}'")
            
            # Analyze results
            found_sources = set()
            relevant_content = []
            
            for result in results:
                metadata = result.metadata
                filename = metadata.get("filename", "unknown")
                found_sources.add(filename)
                relevant_content.append({
                    "content": result.content[:100] + "...",
                    "score": result.score,
                    "filename": filename,
                    "importance": metadata.get("importance_score", 0)
                })
            
            search_results[query] = {
                "results_count": len(results),
                "sources_found": list(found_sources),
                "expected_sources": test_case["expected_docs"],
                "relevant_content": relevant_content
            }
            
            # Log findings
            logger.info(f"📊 Sources found: {list(found_sources)}")
            logger.info(f"📊 Expected sources: {test_case['expected_docs']}")
            
            # Check if we found information from expected sources
            found_expected = any(expected in found_sources for expected in test_case["expected_docs"])
            if found_expected:
                logger.info(f"✅ Found information from expected sources")
            else:
                logger.warning(f"⚠️ Did not find information from expected sources")
        
        return search_results
    
    async def test_multi_document_field_extraction(self):
        """Test field extraction using information from multiple documents"""
        logger.info("🎯 Testing multi-document field extraction...")
        
        # Test fields that require information synthesis from multiple documents
        test_fields = [
            {
                "field_name": "Generic Name",
                "expected_value": "Advanced Multi-Parameter Patient Monitor",
                "source_docs": ["device_basic_info.txt"]
            },
            {
                "field_name": "Model Number",
                "expected_values": ["VW-2024-Pro", "VW-2024-Standard", "VW-2024-Compact"],
                "source_docs": ["device_basic_info.txt", "technical_specifications.txt"]
            },
            {
                "field_name": "Manufacturer",
                "expected_value": "VitalTech Medical Systems Inc.",
                "source_docs": ["device_basic_info.txt", "manufacturing_quality.txt"]
            },
            {
                "field_name": "FDA 510(k) Number",
                "expected_value": "K987654321",
                "source_docs": ["device_basic_info.txt"]
            },
            {
                "field_name": "Risk Control Measures",
                "expected_content": ["Electrical safety", "Alarm system", "Software safety"],
                "source_docs": ["safety_compliance.txt"]
            }
        ]
        
        extraction_results = {}
        
        for field_info in test_fields:
            field_name = field_info["field_name"]
            logger.info(f"🎯 Extracting field: {field_name}")
            
            # Generate comprehensive questions for the field
            questions = await gemini_service.generate_field_questions(
                field_name=field_name,
                field_context=f"Information about {field_name} for medical device"
            )
            
            logger.info(f"📝 Generated questions: {questions}")
            
            # Create comprehensive query vectors
            all_query_vectors = []
            for question in questions:
                embedding = await gemini_service.get_embedding(question)
                all_query_vectors.append(embedding)
            
            # Add direct field embedding
            field_embedding = await gemini_service.get_embedding(field_name)
            all_query_vectors.append(field_embedding)
            
            # Use comprehensive search
            comprehensive_results = await pinecone_service.comprehensive_search(
                query_vectors=all_query_vectors,
                device_id=self.test_device_id,
                top_k_per_query=8,
                final_top_k=15
            )
            
            logger.info(f"📊 Comprehensive search found {len(comprehensive_results)} results")
            
            # Extract context documents
            context_docs = []
            sources_found = set()
            
            for result in comprehensive_results:
                if len(result.content) > 50:
                    context_docs.append(result.content)
                    filename = result.metadata.get("filename", "unknown")
                    sources_found.add(filename)
            
            logger.info(f"📊 Context from sources: {list(sources_found)}")
            
            # Attempt field extraction
            if context_docs:
                extracted_value = await gemini_service.fill_template_field_enhanced(
                    field_name=field_name,
                    field_context=f"Extract {field_name} information",
                    context_docs=context_docs,
                    questions=questions,
                    device_id=self.test_device_id
                )
                
                logger.info(f"✅ Extracted value: '{extracted_value}'")
                
                extraction_results[field_name] = {
                    "extracted_value": extracted_value,
                    "sources_found": list(sources_found),
                    "expected_sources": field_info["source_docs"],
                    "context_count": len(context_docs),
                    "success": extracted_value is not None
                }
            else:
                logger.warning(f"❌ No context found for {field_name}")
                extraction_results[field_name] = {
                    "extracted_value": None,
                    "sources_found": [],
                    "expected_sources": field_info["source_docs"],
                    "context_count": 0,
                    "success": False
                }
        
        return extraction_results
    
    async def test_document_coverage_completeness(self):
        """Test that information from ALL documents is accessible"""
        logger.info("📊 Testing document coverage completeness...")
        
        # Create queries that should find unique information from each document
        coverage_tests = [
            {
                "doc": "device_basic_info.txt",
                "unique_queries": [
                    "VitalWatch Pro brand name",
                    "Dr Sarah Johnson regulatory affairs",
                    "DMF-VW-2024-001 document number"
                ]
            },
            {
                "doc": "technical_specifications.txt",
                "unique_queries": [
                    "15.6 inch touchscreen display",
                    "12-lead ECG capability",
                    "lithium-ion 4 hours battery"
                ]
            },
            {
                "doc": "safety_compliance.txt",
                "unique_queries": [
                    "IEC 60601-1 medical electrical",
                    "St Mary's Medical Center clinical study",
                    "CF cardiac floating applied parts"
                ]
            },
            {
                "doc": "manufacturing_quality.txt",
                "unique_queries": [
                    "TechDisplay Corp display module",
                    "TÜV SÜD notified body",
                    "Statistical process control SPC"
                ]
            }
        ]
        
        coverage_results = {}
        
        for doc_test in coverage_tests:
            doc_name = doc_test["doc"]
            queries = doc_test["unique_queries"]
            
            logger.info(f"📄 Testing coverage for {doc_name}")
            
            doc_found_count = 0
            
            for query in queries:
                # Search for specific information
                query_embedding = await gemini_service.get_embedding(query)
                results = await pinecone_service.search_vectors(
                    query_vector=query_embedding,
                    device_id=self.test_device_id,
                    top_k=5
                )
                
                # Check if we found information from the expected document
                found_in_doc = False
                for result in results:
                    if result.metadata.get("filename") == doc_name:
                        found_in_doc = True
                        break
                
                if found_in_doc:
                    doc_found_count += 1
                    logger.info(f"✅ Found '{query}' in {doc_name}")
                else:
                    logger.warning(f"❌ Did not find '{query}' in {doc_name}")
            
            coverage_percentage = (doc_found_count / len(queries)) * 100
            coverage_results[doc_name] = {
                "queries_found": doc_found_count,
                "total_queries": len(queries),
                "coverage_percentage": coverage_percentage
            }
            
            logger.info(f"📊 {doc_name} coverage: {coverage_percentage:.1f}% ({doc_found_count}/{len(queries)})")
        
        return coverage_results
    
    async def run_comprehensive_coverage_test(self):
        """Run all comprehensive coverage tests"""
        logger.info("🚀 Starting Comprehensive RAG Document Coverage Test")
        logger.info("="*80)
        
        test_results = {}
        
        try:
            # Create test documents
            self.create_test_documents()
            
            # Test 1: Document Processing Coverage
            logger.info("\n🧪 TEST 1: Document Processing Coverage")
            test_results["processing"] = await self.test_document_processing_coverage()
            
            # Test 2: Comprehensive Search Across Documents
            logger.info("\n🧪 TEST 2: Comprehensive Search Across Documents")
            test_results["search"] = await self.test_comprehensive_search_across_documents()
            
            # Test 3: Multi-Document Field Extraction
            logger.info("\n🧪 TEST 3: Multi-Document Field Extraction")
            test_results["extraction"] = await self.test_multi_document_field_extraction()
            
            # Test 4: Document Coverage Completeness
            logger.info("\n🧪 TEST 4: Document Coverage Completeness")
            test_results["coverage"] = await self.test_document_coverage_completeness()
            
            # Generate comprehensive report
            await self.generate_coverage_report(test_results)
            
            return test_results
            
        except Exception as e:
            logger.error(f"❌ Comprehensive coverage test failed: {e}")
            raise
    
    async def generate_coverage_report(self, test_results):
        """Generate comprehensive coverage report"""
        logger.info("\n" + "="*80)
        logger.info("📋 COMPREHENSIVE RAG DOCUMENT COVERAGE REPORT")
        logger.info("="*80)
        
        # Processing Results
        processing = test_results.get("processing", {})
        logger.info(f"📄 Documents Processed: {processing.get('documents_processed', 0)}")
        logger.info(f"📦 Total Chunks Created: {processing.get('total_chunks', 0)}")
        
        # Search Results
        search = test_results.get("search", {})
        search_success_count = 0
        total_searches = len(search)
        
        for query, results in search.items():
            found_sources = set(results["sources_found"])
            expected_sources = set(results["expected_sources"])
            if found_sources.intersection(expected_sources):
                search_success_count += 1
        
        search_success_rate = (search_success_count / total_searches * 100) if total_searches > 0 else 0
        logger.info(f"🔍 Search Success Rate: {search_success_rate:.1f}% ({search_success_count}/{total_searches})")
        
        # Extraction Results
        extraction = test_results.get("extraction", {})
        extraction_success_count = sum(1 for result in extraction.values() if result["success"])
        total_extractions = len(extraction)
        extraction_success_rate = (extraction_success_count / total_extractions * 100) if total_extractions > 0 else 0
        logger.info(f"🎯 Field Extraction Success Rate: {extraction_success_rate:.1f}% ({extraction_success_count}/{total_extractions})")
        
        # Coverage Results
        coverage = test_results.get("coverage", {})
        avg_coverage = sum(result["coverage_percentage"] for result in coverage.values()) / len(coverage) if coverage else 0
        logger.info(f"📊 Average Document Coverage: {avg_coverage:.1f}%")
        
        # Individual document coverage
        for doc, result in coverage.items():
            logger.info(f"   📄 {doc}: {result['coverage_percentage']:.1f}%")
        
        # Overall Assessment
        logger.info("\n🎯 COMPREHENSIVE ASSESSMENT:")
        
        if avg_coverage >= 80 and extraction_success_rate >= 70 and search_success_rate >= 70:
            logger.info("🎉 EXCELLENT: RAG system demonstrates comprehensive document coverage!")
            logger.info("✅ All documents are being processed and information is retrievable")
            logger.info("✅ Multi-document search and extraction working effectively")
        elif avg_coverage >= 60 and extraction_success_rate >= 50:
            logger.info("⚠️ GOOD: RAG system shows good coverage with room for improvement")
            logger.info("📈 Consider optimizing search parameters and chunking strategy")
        else:
            logger.info("❌ NEEDS IMPROVEMENT: RAG system may be missing document content")
            logger.info("🔧 Review document processing and search optimization")
        
        # Key Metrics Summary
        logger.info("\n📊 KEY METRICS:")
        logger.info(f"   📄 Documents Processed: {processing.get('documents_processed', 0)}/4")
        logger.info(f"   📦 Chunks Created: {processing.get('total_chunks', 0)}")
        logger.info(f"   🔍 Search Success: {search_success_rate:.1f}%")
        logger.info(f"   🎯 Extraction Success: {extraction_success_rate:.1f}%")
        logger.info(f"   📊 Document Coverage: {avg_coverage:.1f}%")
        
        return {
            "overall_score": (avg_coverage + extraction_success_rate + search_success_rate) / 3,
            "document_coverage": avg_coverage,
            "extraction_success": extraction_success_rate,
            "search_success": search_success_rate
        }

async def main():
    """Main test execution"""
    try:
        tester = RAGDocumentCoverageTest()
        results = await tester.run_comprehensive_coverage_test()
        return True
    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return False

if __name__ == "__main__":
    # Run the comprehensive coverage test
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
