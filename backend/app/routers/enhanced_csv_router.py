"""
Enhanced CSV Processing FastAPI Endpoints
Implements the hybrid approach for high-accuracy CSV filling
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
import os
import json
import logging
from typing import Dict, Any
from io import StringIO, BytesIO

from app.services.enhanced_csv_processor import EnhancedCSVProcessor
from app.routers.file_history import add_file_to_history

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/enhanced-csv", tags=["Enhanced CSV Processing"])

# Global processor instance
processor = EnhancedCSVProcessor()

@router.on_event("startup")
async def startup_event():
    """Initialize the processor on startup"""
    await processor.initialize()

@router.post("/upload-knowledge-base")
async def upload_knowledge_base(
    file: UploadFile = File(...),
    device_id: str = "default",
    namespace: str = "default"
) -> Dict[str, Any]:
    """
    Upload a CSV file to serve as knowledge base for filling blank templates
    
    This endpoint:
    1. Parses the CSV and builds schema
    2. Creates exact-match indexes for unique columns
    3. Generates per-cell and row-level embeddings
    4. Stores everything for fast retrieval
    """
    
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Read and parse CSV
        content = await file.read()
        csv_text = content.decode('utf-8')
        df = pd.read_csv(StringIO(csv_text))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        logger.info(f"📊 Processing knowledge base CSV: {len(df)} rows, {len(df.columns)} columns")
        
        # Index the knowledge base
        index_metadata = await processor.index_csv_knowledge_base(
            df=df,
            device_id=device_id,
            namespace=namespace
        )
        
        return {
            "status": "success",
            "message": f"Knowledge base indexed successfully",
            "filename": file.filename,
            "device_id": device_id,
            "namespace": namespace,
            "rows_processed": len(df),
            "columns": list(df.columns),
            "schema": index_metadata["schema"],
            "total_vectors": index_metadata["total_vectors"],
            "exact_match_entries": len(index_metadata["exact_match_index"])
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to process knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process knowledge base: {str(e)}")

@router.post("/fill-blank-template")
async def fill_blank_template(
    file: UploadFile = File(...),
    device_id: str = "default",
    namespace: str = "default",
    confidence_threshold: float = None
) -> Dict[str, Any]:
    """
    Fill a blank CSV template using the uploaded knowledge base
    
    This endpoint:
    1. Processes the blank CSV template
    2. For each empty cell, tries multiple filling strategies
    3. Returns filled CSV with full provenance tracking
    4. Adds result to file history (not favorites)
    """
    
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Read and parse blank CSV
        content = await file.read()
        csv_text = content.decode('utf-8')
        blank_df = pd.read_csv(StringIO(csv_text))
        
        if blank_df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        logger.info(f"🎯 Processing blank template: {len(blank_df)} rows, {len(blank_df.columns)} columns")
        
        # Fill the blank CSV
        filled_df, fill_metadata = await processor.fill_blank_csv(
            blank_df=blank_df,
            device_id=device_id,
            namespace=namespace
        )
        
        # Convert filled DataFrame to CSV string
        filled_csv = filled_df.to_csv(index=False)
        
        # Prepare response with detailed metrics
        response = {
            "status": "success",
            "message": "CSV template filled successfully",
            "filename": file.filename,
            "device_id": device_id,
            "namespace": namespace,
            "fill_stats": fill_metadata["fill_stats"],
            "fill_rate": fill_metadata["fill_rate"],
            "filled_csv": filled_csv,
            "provenance_summary": {
                "total_cells_processed": len(fill_metadata["provenance"]),
                "methods_used": fill_metadata["fill_stats"]["methods_used"],
                "average_confidence": sum(fill_metadata["fill_stats"]["confidence_distribution"]) / len(fill_metadata["fill_stats"]["confidence_distribution"]) if fill_metadata["fill_stats"]["confidence_distribution"] else 0
            }
        }
        
        # Optionally include full provenance (can be large)
        if len(fill_metadata["provenance"]) <= 100:  # Only include for smaller files
            response["provenance"] = fill_metadata["provenance"]
        
        # Add to file history (not favorites)
        try:
            filled_filename = f"enhanced_filled_{file.filename}"
            await add_file_to_history(
                filename=filled_filename,
                file_path=None,
                file_obj=None,
                content_type='text/csv',
                file_type="processed_csv",
                gcs_folder="enhanced_filled_csv"
            )
            logger.info(f"✅ Added enhanced filled CSV to file history: {filled_filename}")
        except Exception as e:
            logger.warning(f"Could not add enhanced filled CSV to file history: {e}")
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Failed to fill CSV template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fill CSV template: {str(e)}")

@router.post("/fill-and-download")
async def fill_and_download(
    file: UploadFile = File(...),
    device_id: str = "default",
    namespace: str = "default"
):
    """
    Fill blank CSV and return as downloadable file
    """
    
    try:
        # Fill the CSV using the same logic
        content = await file.read()
        csv_text = content.decode('utf-8')
        blank_df = pd.read_csv(StringIO(csv_text))
        
        filled_df, fill_metadata = await processor.fill_blank_csv(
            blank_df=blank_df,
            device_id=device_id,
            namespace=namespace
        )
        
        # Create temporary file for download
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            filled_df.to_csv(temp_file, index=False)
            temp_file_path = temp_file.name
        
        # Prepare filename
        original_name = file.filename.replace('.csv', '')
        filled_filename = f"{original_name}_filled.csv"
        
        # Add to file history before returning the file
        try:
            await add_file_to_history(
                filename=filled_filename,
                file_path=temp_file_path,
                content_type='text/csv',
                file_type="filled",
                gcs_folder="filled_csv"
            )
        except Exception as e:
            logger.warning(f"Could not add filled CSV to file history: {e}")
        
        return FileResponse(
            path=temp_file_path,
            filename=filled_filename,
            media_type='text/csv',
            background=BackgroundTasks([lambda: os.unlink(temp_file_path)])
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to fill and download CSV: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@router.get("/device/{device_id}/stats")
async def get_device_stats(device_id: str) -> Dict[str, Any]:
    """
    Get statistics about the knowledge base for a device
    """
    
    try:
        # Check if device has vectors stored
        if processor.pinecone_service.index:
            # Query Pinecone for device stats
            stats = processor.pinecone_service.index.describe_index_stats()
            namespace_key = f"device_{device_id}"
            
            if stats.namespaces and namespace_key in stats.namespaces:
                namespace_stats = stats.namespaces[namespace_key]
                return {
                    "device_id": device_id,
                    "storage_type": "pinecone",
                    "total_vectors": namespace_stats.vector_count,
                    "status": "indexed"
                }
        
        # Check local storage
        local_file = processor.pinecone_service._get_local_storage_file(device_id)
        if local_file.exists():
            vectors = processor.pinecone_service._load_local_vectors(device_id)
            
            # Count by type
            cell_vectors = sum(1 for v in vectors if v.get('metadata', {}).get('type') == 'cell')
            row_vectors = sum(1 for v in vectors if v.get('metadata', {}).get('type') == 'row')
            
            return {
                "device_id": device_id,
                "storage_type": "local",
                "total_vectors": len(vectors),
                "cell_vectors": cell_vectors,
                "row_vectors": row_vectors,
                "status": "indexed"
            }
        
        return {
            "device_id": device_id,
            "storage_type": "none",
            "total_vectors": 0,
            "status": "not_indexed"
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get device stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get device stats: {str(e)}")

@router.post("/test-workflow")
async def test_workflow() -> Dict[str, Any]:
    """
    Test the complete workflow with sample data
    """
    
    try:
        # Create sample knowledge base
        knowledge_base_data = {
            'device_name': ['ECG Monitor Pro', 'Temperature Sensor', 'Pulse Oximeter Pro', 'Blood Pressure Monitor'],
            'model_number': ['ECG-2000', 'TEMP-100', 'PULSE-300', 'BP-400'],
            'category': ['Cardiology', 'General', 'Respiratory', 'Cardiology'],
            'description': [
                'Professional ECG monitoring system',
                'Digital temperature measurement device', 
                'Advanced pulse oximetry monitor',
                'Automated blood pressure measurement'
            ],
            'price': [2500, 150, 800, 600],
            'manufacturer': ['MedTech Inc', 'TempCorp', 'PulseDevice Ltd', 'CardioSystems']
        }
        knowledge_df = pd.DataFrame(knowledge_base_data)
        
        # Index the knowledge base
        device_id = "test_workflow"
        index_result = await processor.index_csv_knowledge_base(
            df=knowledge_df,
            device_id=device_id,
            namespace="test"
        )
        
        # Create blank template
        blank_data = {
            'device_name': ['ECG Monitor Pro', '', 'Pulse Oximeter Pro', ''],
            'model_number': ['', 'TEMP-100', '', 'BP-400'],
            'category': ['', '', 'Respiratory', ''],
            'description': ['', '', '', 'Automated blood pressure measurement'],
            'price': ['', '', 800, ''],
            'manufacturer': ['', 'TempCorp', '', '']
        }
        blank_df = pd.DataFrame(blank_data)
        
        # Fill the blank template
        filled_df, fill_metadata = await processor.fill_blank_csv(
            blank_df=blank_df,
            device_id=device_id,
            namespace="test"
        )
        
        return {
            "status": "success",
            "message": "Test workflow completed successfully",
            "knowledge_base": {
                "rows": len(knowledge_df),
                "columns": list(knowledge_df.columns),
                "vectors_created": index_result["total_vectors"]
            },
            "blank_template": {
                "rows": len(blank_df),
                "total_blanks": fill_metadata["fill_stats"]["total_blanks"]
            },
            "fill_results": {
                "filled_count": fill_metadata["fill_stats"]["filled_count"],
                "fill_rate": fill_metadata["fill_rate"],
                "methods_used": fill_metadata["fill_stats"]["methods_used"]
            },
            "filled_csv": filled_df.to_csv(index=False),
            "sample_provenance": dict(list(fill_metadata["provenance"].items())[:3])  # Show first 3 items
        }
        
    except Exception as e:
        logger.error(f"❌ Test workflow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test workflow failed: {str(e)}")

@router.delete("/device/{device_id}/clear")
async def clear_device_data(device_id: str) -> Dict[str, Any]:
    """
    Clear all indexed data for a device
    """
    
    try:
        # Clear from Pinecone if available
        if processor.pinecone_service.index:
            try:
                processor.pinecone_service.index.delete(delete_all=True, namespace=f"device_{device_id}")
                logger.info(f"Cleared Pinecone data for device {device_id}")
            except Exception as e:
                logger.warning(f"Failed to clear Pinecone data: {e}")
        
        # Clear local storage
        local_file = processor.pinecone_service._get_local_storage_file(device_id)
        if local_file.exists():
            local_file.unlink()
            logger.info(f"Cleared local storage for device {device_id}")
        
        return {
            "status": "success",
            "message": f"All data cleared for device {device_id}",
            "device_id": device_id
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to clear device data: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear device data: {str(e)}")
