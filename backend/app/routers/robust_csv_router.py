"""
Robust CSV Processing FastAPI Endpoints
Handles timeouts and column matching issues
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

from app.services.robust_csv_processor import RobustCSVProcessor
from app.routers.file_history import add_file_to_history

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/robust-csv", tags=["Robust CSV Processing"])

# Global processor instance
processor = RobustCSVProcessor()

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
    Upload a CSV file to serve as knowledge base with robust error handling
    """
    
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Read and parse CSV
        content = await file.read()
        df = pd.read_csv(BytesIO(content))
        
        if df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        logger.info(f"📊 Processing CSV: {len(df)} rows, {len(df.columns)} columns")
        logger.info(f"📋 Columns: {list(df.columns)}")
        
        # Process with robust handling
        result = await processor.index_csv_knowledge_base(df, device_id, namespace)
        
        return {
            "message": "Knowledge base uploaded successfully",
            "device_id": device_id,
            "namespace": namespace,
            "filename": file.filename,
            **result
        }
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty or invalid")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Knowledge base upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/fill-blank-template")
async def fill_blank_template(
    file: UploadFile = File(...),
    device_id: str = "default",
    namespace: str = "default"
) -> Dict[str, Any]:
    """
    Fill blank CSV template using knowledge base with robust error handling
    """
    
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")
        
        # Read and parse CSV
        content = await file.read()
        blank_df = pd.read_csv(BytesIO(content))
        
        if blank_df.empty:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        logger.info(f"🎯 Processing blank template: {len(blank_df)} rows, {len(blank_df.columns)} columns")
        logger.info(f"📋 Template columns: {list(blank_df.columns)}")
        
        # Count blank cells
        blank_count = blank_df.isna().sum().sum() + (blank_df == '').sum().sum()
        logger.info(f"📊 Found {blank_count} blank cells to fill")
        
        # Fill with robust handling
        filled_df, result = await processor.fill_blank_csv(blank_df, device_id, namespace)
        
        # Convert filled DataFrame to CSV string
        csv_output = StringIO()
        filled_df.to_csv(csv_output, index=False)
        csv_string = csv_output.getvalue()
        
        response = {
            "message": "Template filled successfully",
            "device_id": device_id,
            "namespace": namespace,
            "filename": file.filename,
            "filled_csv": csv_string,
            "original_blanks": int(blank_count),
            **result
        }
        
        # Add to file history (not favorites)
        try:
            filled_filename = f"robust_filled_{file.filename}"
            await add_file_to_history(
                filename=filled_filename,
                file_path=None,
                file_obj=None,
                content_type='text/csv',
                file_type="processed_csv",
                gcs_folder="robust_filled_csv"
            )
            logger.info(f"✅ Added robust filled CSV to file history: {filled_filename}")
        except Exception as e:
            logger.warning(f"Could not add robust filled CSV to file history: {e}")
        
        return response
        
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty or invalid")
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"CSV parsing error: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Template filling failed: {e}")
        raise HTTPException(status_code=500, detail=f"Filling failed: {str(e)}")

@router.get("/device/{device_id}/stats")
async def get_device_stats(device_id: str) -> Dict[str, Any]:
    """Get statistics for a device's knowledge base"""
    
    try:
        if device_id in processor.local_data_store:
            data = processor.local_data_store[device_id]
            df = data['dataframe']
            
            return {
                "device_id": device_id,
                "status": "active",
                "storage_type": "local_fallback",
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "columns": list(df.columns),
                "indexed_at": data['timestamp'],
                "namespace": data.get('namespace', 'default')
            }
        else:
            return {
                "device_id": device_id,
                "status": "not_found",
                "message": "No knowledge base found for this device"
            }
            
    except Exception as e:
        logger.error(f"❌ Failed to get device stats: {e}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@router.post("/test-workflow")
async def test_workflow() -> Dict[str, Any]:
    """Test the complete robust CSV workflow with sample data"""
    
    try:
        # Create sample knowledge base
        knowledge_data = {
            'Device Name': ['ECG Monitor Pro', 'Temperature Sensor', 'Pulse Oximeter Pro'],
            'Model Number': ['ECG-2000', 'TEMP-100', 'PULSE-300'],
            'Version': ['v2.1', 'v1.5', 'v3.0'],
            'Manufacturer': ['MedTech Inc', 'TempCorp', 'PulseDevice Ltd'],
            'Date Released': ['2023-01-15', '2022-11-20', '2023-03-10'],
            'Price': [2500, 150, 800]
        }
        knowledge_df = pd.DataFrame(knowledge_data)
        
        # Create blank template (note: different column casing to test robustness)
        blank_data = {
            'device name': ['ECG Monitor Pro', '', 'New Device'],
            'model number': ['', 'TEMP-100', ''],
            'version': ['', '', 'v4.0'],
            'manufacturer': ['', 'TempCorp', ''],
            'date released': ['', '', ''],
            'price': ['', '', '']
        }
        blank_df = pd.DataFrame(blank_data)
        
        # Replace empty strings with NaN
        blank_df = blank_df.replace('', pd.NA)
        
        device_id = "test_robust_workflow"
        
        # Step 1: Index knowledge base
        logger.info("🚀 Testing knowledge base indexing...")
        index_result = await processor.index_csv_knowledge_base(knowledge_df, device_id, "test")
        
        # Step 2: Fill blank template
        logger.info("🎯 Testing template filling...")
        filled_df, fill_result = await processor.fill_blank_csv(blank_df, device_id, "test")
        
        # Convert to CSV string
        csv_output = StringIO()
        filled_df.to_csv(csv_output, index=False)
        filled_csv = csv_output.getvalue()
        
        return {
            "message": "Robust workflow test completed",
            "test_device_id": device_id,
            "knowledge_base_result": index_result,
            "fill_results": fill_result,
            "original_template": blank_df.to_dict(),
            "filled_template": filled_df.to_dict(),
            "filled_csv": filled_csv
        }
        
    except Exception as e:
        logger.error(f"❌ Workflow test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

@router.delete("/device/{device_id}")
async def clear_device_data(device_id: str) -> Dict[str, Any]:
    """Clear all data for a specific device"""
    
    try:
        # Clear local storage
        if device_id in processor.local_data_store:
            del processor.local_data_store[device_id]
        
        # Clear column mapping cache for this device
        keys_to_remove = [k for k in processor.column_mapping_cache.keys() if device_id in k]
        for key in keys_to_remove:
            del processor.column_mapping_cache[key]
        
        # Clear embedding cache (optional - affects all devices)
        # processor.embedding_cache.clear()
        
        return {
            "message": f"Device data cleared successfully",
            "device_id": device_id
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to clear device data: {e}")
        raise HTTPException(status_code=500, detail=f"Clear failed: {str(e)}")

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check for the robust CSV service"""
    
    return {
        "status": "healthy",
        "service": "robust_csv_processor",
        "gemini_available": processor.gemini_service.available,
        "pinecone_available": processor.pinecone_service.index is not None,
        "local_devices": list(processor.local_data_store.keys()),
        "cache_stats": {
            "embeddings_cached": len(processor.embedding_cache),
            "column_mappings_cached": len(processor.column_mapping_cache)
        }
    }
