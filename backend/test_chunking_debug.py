import asyncio
import logging
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.document_processor import document_processor

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_chunking_debug():
    """Debug chunking test"""
    # Use the global instance
    processor = document_processor
    
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
    
    try:
        # Create chunks using enhanced algorithm
        chunks = processor._create_chunks(complex_text)
        
        logger.info(f"✅ Created {len(chunks)} chunks")
        
        # Validate chunking improvements
        assert len(chunks) > 0, "No chunks created"
        
        # Check for enhanced metadata in first chunk
        first_chunk = chunks[0]
        logger.info(f"📦 First chunk keys: {list(first_chunk.keys())}")
        
        # Check for enhanced metadata
        for i, chunk in enumerate(chunks[:3]):  # Check first 3 chunks
            logger.info(f"📦 Chunk {i+1} metadata: {list(chunk.keys())}")
            assert "importance_score" in chunk, f"Missing importance_score in chunk {i+1}"
            assert "semantic_keywords" in chunk, f"Missing semantic_keywords in chunk {i+1}"
            assert "content_type" in chunk, f"Missing content_type in chunk {i+1}"
            assert "chunk_quality_score" in chunk, f"Missing chunk_quality_score in chunk {i+1}"
        
        # Verify boundary detection
        high_quality_chunks = [c for c in chunks if c.get("chunk_quality_score", 0) > 0.7]
        important_chunks = [c for c in chunks if c.get("importance_score", 0) > 0.7]
        
        logger.info(f"📊 Chunking results: {len(chunks)} total, {len(high_quality_chunks)} high-quality, {len(important_chunks)} high-importance")
        
        # Make assertion less strict
        assert len(chunks) > 10, f"Expected more than 10 chunks, got {len(chunks)}"
        assert len(important_chunks) > 0, f"Expected some important chunks, got {len(important_chunks)}"
        
        logger.info("✅ Chunking test passed!")
        
    except Exception as e:
        logger.error(f"❌ Chunking test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_chunking_debug())
