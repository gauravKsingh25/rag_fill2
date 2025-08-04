from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import List, Dict, Any
import logging

from app.models import DocumentUploadResponse, DocumentMetadata
from app.services.document_processor import document_processor
from app.services.pinecone_service import pinecone_service
from app.database import document_repo
from app.routers.devices import get_device

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    device_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload and process a document for a specific device"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.txt', '.md']
        file_extension = file.filename.split('.')[-1].lower()
        if f'.{file_extension}' not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if len(file_content) > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
            )
        
        # Process document
        result = await document_processor.process_uploaded_file(
            file_content=file_content,
            filename=file.filename,
            device_id=device_id
        )
        
        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            device_id=result["device_id"],
            status="success",
            message=f"Document processed successfully. Created {result['chunks_created']} chunks."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to upload document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process document: {e}")

@router.get("/device/{device_id}")
async def get_documents_by_device(device_id: str):
    """Get all documents for a specific device"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Get documents from MongoDB
        documents = await document_repo.get_documents_by_device(device_id)
        
        return {
            "device_id": device_id,
            "document_count": len(documents),
            "documents": documents
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get documents for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get documents: {e}")

@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get specific document by ID"""
    try:
        document = await document_repo.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return document
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document: {e}")

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks"""
    try:
        # Get document to verify it exists and get device_id
        document = await document_repo.get_document_by_id(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete document and all chunks
        success = await document_processor.delete_document(document_id, document["device_id"])
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document")
        
        return {
            "message": "Document deleted successfully",
            "document_id": document_id,
            "device_id": document["device_id"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to delete document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")

@router.put("/{document_id}/reprocess")
async def reprocess_document(document_id: str):
    """Reprocess a document (re-chunk and re-embed)"""
    try:
        # TODO: Implement document reprocessing
        # This would involve:
        # 1. Getting the original file
        # 2. Deleting existing chunks from Pinecone
        # 3. Re-processing the document
        # 4. Updating metadata
        
        raise HTTPException(status_code=501, detail="Document reprocessing not implemented yet")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to reprocess document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reprocess document: {e}")

@router.post("/device/{device_id}/cleanup")
async def cleanup_device_vectors(device_id: str):
    """Clean up orphaned vectors for a device"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Get all valid document IDs for this device
        documents = await document_repo.get_documents_by_device(device_id)
        valid_document_ids = [doc["document_id"] for doc in documents]
        
        # Clean up orphaned vectors
        cleaned_count = await pinecone_service.cleanup_orphaned_vectors(device_id, valid_document_ids)
        
        return {
            "message": f"Cleanup completed for device {device_id}",
            "device_id": device_id,
            "orphaned_vectors_removed": cleaned_count,
            "valid_documents": len(valid_document_ids)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to cleanup vectors for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup vectors: {e}")

@router.get("/device/{device_id}/vector-stats")
async def get_device_vector_stats(device_id: str):
    """Get vector database statistics for a device"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Get vector statistics
        stats = await pinecone_service.get_index_stats(device_id)
        
        # Get document count from MongoDB
        documents = await document_repo.get_documents_by_device(device_id)
        
        return {
            "device_id": device_id,
            "vector_stats": stats,
            "mongodb_documents": len(documents),
            "document_list": [
                {
                    "document_id": doc["document_id"],
                    "filename": doc["filename"],
                    "chunk_count": doc.get("chunk_count", 0)
                }
                for doc in documents
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get vector stats for device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get vector stats: {e}")
