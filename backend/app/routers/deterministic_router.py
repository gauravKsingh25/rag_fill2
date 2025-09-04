"""
API Router for Deterministic Document Filling
Exposes the enhanced deterministic filling approach via REST API
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging
import json
import tempfile
from pathlib import Path

from app.services.interpreted_form_service import InterpretedFormService
from app.services.template_mapping_service import TemplateMappingService
from app.services.file_cleanup_service import file_cleanup_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deterministic", tags=["Deterministic Filling"])

# Pydantic models for request/response
class DeterministicFillRequest(BaseModel):
    """Request model for deterministic form filling"""
    template_content: str = Field(..., description="Template content to analyze")
    input_data: Dict[str, Any] = Field(..., description="Form data to fill")
    template_name: Optional[str] = Field(None, description="Template type (auto-detected if not provided)")
    output_filename: Optional[str] = Field(None, description="Custom output filename")

class TemplateValidationRequest(BaseModel):
    """Request model for template validation"""
    template_name: str = Field(..., description="Template name to validate")
    input_data: Dict[str, Any] = Field(..., description="Data to validate")

class DeterministicFillResponse(BaseModel):
    """Response model for deterministic form filling"""
    success: bool
    method: str
    template_type: Optional[str] = None
    detected_template: Optional[str] = None
    filled_document_path: Optional[str] = None
    filename: Optional[str] = None
    message: str
    validation_passed: Optional[bool] = None
    fields_filled: Optional[int] = None
    available_templates: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None

@router.post("/fill-form", response_model=DeterministicFillResponse)
async def fill_form_deterministic(request: DeterministicFillRequest):
    """
    Fill form using deterministic mapping approach.
    Solves field confusion issues with explicit field mapping.
    """
    try:
        logger.info(f"🎯 Deterministic fill request: template_name={request.template_name}")
        
        # Initialize service
        form_service = InterpretedFormService()
        
        # Perform deterministic filling
        result = await form_service.fill_form_deterministic(
            template_content=request.template_content,
            input_data=request.input_data,
            template_name=request.template_name,
            output_filename=request.output_filename
        )
        
        return DeterministicFillResponse(**result)
        
    except Exception as e:
        logger.error(f"❌ Deterministic fill error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/validate-data")
async def validate_template_data(request: TemplateValidationRequest):
    """
    Validate input data against template requirements.
    Returns validation results and error details.
    """
    try:
        logger.info(f"🔍 Validating data for template: {request.template_name}")
        
        # Initialize mapping service
        mapping_service = TemplateMappingService()
        
        # Validate data
        is_valid, errors, validated_data = mapping_service.validate_input_data(
            request.template_name, request.input_data
        )
        
        return {
            "success": True,
            "template_name": request.template_name,
            "validation_passed": is_valid,
            "errors": errors,
            "validated_fields": len(validated_data),
            "validated_data": validated_data if is_valid else None,
            "message": "Validation completed" if is_valid else f"Validation failed with {len(errors)} errors"
        }
        
    except Exception as e:
        logger.error(f"❌ Validation error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def get_available_templates():
    """
    Get list of available templates for deterministic filling.
    Returns template configurations and field requirements.
    """
    try:
        logger.info("📚 Getting available templates")
        
        # Initialize mapping service
        mapping_service = TemplateMappingService()
        
        # Get available templates
        templates = mapping_service.get_available_templates()
        
        return {
            "success": True,
            "templates": templates,
            "total_templates": len(templates),
            "message": f"Found {len(templates)} available templates"
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting templates: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/template/{template_name}/config")
async def get_template_config(template_name: str):
    """
    Get detailed configuration for a specific template.
    Returns field mappings, validation rules, and requirements.
    """
    try:
        logger.info(f"🔧 Getting config for template: {template_name}")
        
        # Initialize mapping service
        mapping_service = TemplateMappingService()
        
        # Get template configuration
        config = mapping_service.export_template_config(template_name)
        
        if not config:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        return {
            "success": True,
            "template_config": config,
            "message": f"Configuration for {template_name} retrieved"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting template config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/template/{template_name}/preview")
async def get_template_preview(template_name: str):
    """
    Get preview of what fields will be filled for a template.
    Useful for understanding template requirements.
    """
    try:
        logger.info(f"👁️ Getting preview for template: {template_name}")
        
        # Initialize services
        form_service = InterpretedFormService()
        
        # Get template preview
        preview = form_service.deterministic_filler.get_template_preview(template_name)
        
        if not preview:
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        return {
            "success": True,
            "template_name": template_name,
            "preview": preview,
            "message": f"Preview for {template_name} generated"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting template preview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/detect-template")
async def detect_template_type(template_content: str = Form(...)):
    """
    Auto-detect template type from content.
    Returns detected template name and confidence.
    """
    try:
        logger.info("🔍 Auto-detecting template type")
        
        # Initialize mapping service
        mapping_service = TemplateMappingService()
        
        # Detect template type
        detected_template = mapping_service.detect_template_type(template_content)
        
        # Get available templates for reference
        available_templates = mapping_service.get_available_templates()
        
        if detected_template:
            return {
                "success": True,
                "detected_template": detected_template,
                "confidence": "high",
                "available_templates": available_templates,
                "message": f"Detected template type: {detected_template}"
            }
        else:
            return {
                "success": False,
                "detected_template": None,
                "confidence": "none",
                "available_templates": available_templates,
                "message": "Could not detect template type automatically"
            }
        
    except Exception as e:
        logger.error(f"❌ Template detection error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_filled_document(filename: str, background_tasks: BackgroundTasks):
    """
    Download a filled document by filename and schedule cleanup after download.
    Returns the document file for download.
    """
    try:
        logger.info(f"📥 Download request for: {filename}")
        
        # Construct file path
        file_path = Path("filled_templates") / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File '{filename}' not found")
        
        # Schedule file cleanup after download (30 seconds delay to ensure download completes)
        background_tasks.add_task(
            file_cleanup_service.schedule_file_cleanup,
            str(file_path),
            30  # 30 seconds delay
        )
        
        logger.info(f"📥 Downloading deterministic document: {filename} (cleanup scheduled)")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Download error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fill-with-upload")
async def fill_form_with_template_upload(
    template_file: UploadFile = File(...),
    input_data: str = Form(...),
    template_name: Optional[str] = Form(None)
):
    """
    Fill form by uploading template file and providing JSON data.
    Supports .docx and .txt template files.
    """
    try:
        logger.info(f"📤 Upload fill request: {template_file.filename}")
        
        # Read template content
        template_content = ""
        if template_file.filename.endswith('.txt'):
            template_content = (await template_file.read()).decode('utf-8')
        elif template_file.filename.endswith('.docx'):
            # For .docx files, you might want to extract text content
            # For now, treating as text content
            template_content = (await template_file.read()).decode('utf-8', errors='ignore')
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use .txt or .docx files.")
        
        # Parse input data
        try:
            parsed_data = json.loads(input_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON data provided")
        
        # Initialize service
        form_service = InterpretedFormService()
        
        # Perform deterministic filling
        result = await form_service.fill_form_deterministic(
            template_content=template_content,
            input_data=parsed_data,
            template_name=template_name,
            output_filename=f"filled_{template_file.filename.split('.')[0]}.docx"
        )
        
        return DeterministicFillResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Upload fill error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
