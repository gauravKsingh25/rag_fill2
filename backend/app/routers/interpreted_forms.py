from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import List, Optional, Union, Dict, Any
import json
import tempfile
import os
from pathlib import Path
import uuid

from ..services.interpreted_form_service import interpreted_form_service
from ..services.llm_service import LLMService
from ..services.document_processor import DocumentProcessor

router = APIRouter()

class UploadPersonDataRequest(BaseModel):
    device_id: str
    person_id: Optional[str] = None

class AnalyzeTemplateRequest(BaseModel):
    device_id: str
    template_name: str

class GenerateBatchFormsRequest(BaseModel):
    device_id: str
    person_id: str
    templates: List[Dict[str, Any]]
    batch_id: Optional[str] = None

class PersonDataUploadResponse(BaseModel):
    success: bool
    person_id: str
    chunks_processed: int
    message: str

class TemplateAnalysisResponse(BaseModel):
    success: bool
    template_analysis: Dict[str, Any]
    message: str

class BatchFormGenerationResponse(BaseModel):
    success: bool
    batch_id: str
    filled_documents: List[Dict[str, Any]]
    download_links: List[str]
    total_documents: int
    message: str

@router.post("/interpreted-forms/upload-person-data/", response_model=PersonDataUploadResponse)
async def upload_person_data(
    device_id: str = Form(...),
    person_id: Optional[str] = Form(None),
    data_file: UploadFile = File(...)
):
    """
    Upload person data to Pinecone database for form filling.
    Supports JSON, CSV, TXT, PDF, DOCX formats.
    """
    try:
        if not data_file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Read file content
        file_content = await data_file.read()
        
        # Upload to service
        result = await interpreted_form_service.upload_person_data(
            person_data_file=file_content,
            filename=data_file.filename,
            device_id=device_id,
            person_id=person_id
        )
        
        if result['success']:
            return PersonDataUploadResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Upload failed'))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading person data: {str(e)}")

@router.post("/interpreted-forms/analyze-template/", response_model=TemplateAnalysisResponse)
async def analyze_template(
    device_id: str = Form(...),
    template_file: UploadFile = File(...)
):
    """
    Analyze template to identify blank spaces and field requirements.
    """
    try:
        if not template_file.filename:
            raise HTTPException(status_code=400, detail="No template file provided")
        
        # Read file content
        file_content = await template_file.read()
        
        # Analyze template
        result = await interpreted_form_service.analyze_template(
            template_file=file_content,
            filename=template_file.filename,
            device_id=device_id
        )
        
        if result['success']:
            return TemplateAnalysisResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Analysis failed'))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing template: {str(e)}")

@router.post("/interpreted-forms/generate-forms/", response_model=BatchFormGenerationResponse)
async def generate_filled_forms(
    device_id: str = Form(...),
    person_id: str = Form(...),
    templates_data: str = Form(...),  # JSON string of template analyses
    batch_id: Optional[str] = Form(None)
):
    """
    Generate filled forms using person data and template analyses.
    Supports up to 5 templates at once.
    """
    try:
        # Parse templates data
        try:
            templates = json.loads(templates_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid templates data format")
        
        if not isinstance(templates, list):
            raise HTTPException(status_code=400, detail="Templates must be a list")
        
        if len(templates) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 templates allowed per batch")
        
        # Generate forms
        result = await interpreted_form_service.generate_filled_forms(
            person_id=person_id,
            templates=templates,
            device_id=device_id,
            batch_id=batch_id
        )
        
        if result['success']:
            return BatchFormGenerationResponse(**result)
        else:
            raise HTTPException(status_code=500, detail=result.get('message', 'Form generation failed'))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating forms: {str(e)}")

@router.get("/interpreted-forms/download/{filename}")
async def download_filled_document(filename: str):
    """
    Download a filled document or batch zip file.
    """
    try:
        file_path = Path("filled_templates") / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Determine media type based on file extension
        if filename.endswith('.zip'):
            media_type = "application/zip"
        elif filename.endswith('.pdf'):
            media_type = "application/pdf"
        elif filename.endswith('.docx'):
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            media_type = "text/plain"
        
        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=filename
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading file: {str(e)}")

@router.get("/download/interpreted/{filename}")
async def download_filled_document_legacy(filename: str):
    """
    Legacy download endpoint for backward compatibility.
    """
    return await download_filled_document(filename)

@router.get("/interpreted-forms/status/{person_id}")
async def get_person_data_status(person_id: str, device_id: str):
    """
    Get status of uploaded person data.
    """
    try:
        # This would query Pinecone to check if person data exists
        # For now, return a simple response
        return {
            "person_id": person_id,
            "device_id": device_id,
            "status": "active",
            "message": "Person data available for form filling"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")

@router.get("/interpreted-forms/debug/{device_id}")
async def debug_stored_data(device_id: str, person_id: str = None):
    """
    Debug endpoint to check what data is stored for a device/person
    """
    try:
        result = await interpreted_form_service.debug_stored_data(device_id, person_id)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error debugging data: {str(e)}")

@router.get("/interpreted-forms/list-persons/{device_id}")
async def list_person_ids(device_id: str):
    """
    List all person_ids available for a device
    """
    try:
        # Check local storage
        from pathlib import Path
        import json
        
        storage_file = Path("local_vector_storage") / f"device_{device_id}_vectors.json"
        
        if storage_file.exists():
            with open(storage_file, 'r', encoding='utf-8') as f:
                stored_data = json.load(f)
            
            # Get unique person_ids
            person_ids = list(set(v.get('metadata', {}).get('person_id') for v in stored_data if v.get('metadata', {}).get('person_id')))
            
            return {
                "success": True,
                "device_id": device_id,
                "person_ids": person_ids,
                "total_vectors": len(stored_data),
                "total_persons": len(person_ids)
            }
        else:
            return {
                "success": False,
                "message": f"No data found for device {device_id}",
                "person_ids": []
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing persons: {str(e)}")

@router.get("/interpreted-forms/list-all-persons")
async def list_all_persons():
    """
    List all persons in the separate person storage
    """
    try:
        result = await interpreted_form_service.debug_stored_data("", None)
        return {
            "success": True,
            "available_persons": result.get('person_data', {}).get('available_person_ids', []),
            "total_persons": result.get('person_data', {}).get('total_persons', 0)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing all persons: {str(e)}")

# Legacy endpoints for backward compatibility

class FormField(BaseModel):
    name: str
    value: str
    type: str  # 'text', 'date', 'number', 'textarea'
    required: bool
    description: Optional[str] = None

class InterpretFormRequest(BaseModel):
    device_id: str
    form_type: str
    text_input: Optional[str] = None

class GenerateFormDocumentRequest(BaseModel):
    device_id: str
    form_type: str
    fields: List[FormField]

class FormInterpretationResponse(BaseModel):
    success: bool
    form_type: str
    fields: List[FormField]
    message: Optional[str] = None

class DocumentGenerationResponse(BaseModel):
    success: bool
    generated_document: str
    download_url: Optional[str] = None
    message: Optional[str] = None

# Form templates for different types
FORM_TEMPLATES = {
    "affidavit": {
        "title": "Affidavit",
        "fields": [
            {"name": "affiant_name", "type": "text", "required": True, "description": "Full name of the person making the affidavit"},
            {"name": "affiant_address", "type": "textarea", "required": True, "description": "Complete address of the affiant"},
            {"name": "statement", "type": "textarea", "required": True, "description": "The sworn statement or declaration"},
            {"name": "date", "type": "date", "required": True, "description": "Date when the affidavit is made"},
            {"name": "notary_name", "type": "text", "required": False, "description": "Name of the notary public"},
            {"name": "state", "type": "text", "required": True, "description": "State where the affidavit is executed"},
            {"name": "county", "type": "text", "required": True, "description": "County where the affidavit is executed"}
        ]
    },
    "general": {
        "title": "General Form",
        "fields": [
            {"name": "full_name", "type": "text", "required": True, "description": "Full legal name"},
            {"name": "date_of_birth", "type": "date", "required": False, "description": "Date of birth"},
            {"name": "address", "type": "textarea", "required": True, "description": "Complete address"},
            {"name": "phone_number", "type": "text", "required": False, "description": "Contact phone number"},
            {"name": "email", "type": "text", "required": False, "description": "Email address"},
            {"name": "description", "type": "textarea", "required": True, "description": "Description or purpose"}
        ]
    }
}

@router.post("/interpret-form/", response_model=FormInterpretationResponse)
async def interpret_form(
    device_id: str = Form(...),
    form_type: str = Form(...),
    text_input: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    Interpret content from text or uploaded file to extract form fields
    """
    try:
        content = ""
        
        # Process uploaded file if provided
        if file:
            if file.content_type not in ["text/plain", "application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp_file:
                content_bytes = await file.read()
                tmp_file.write(content_bytes)
                tmp_file_path = tmp_file.name
            
            try:
                # Extract text from file
                doc_processor = DocumentProcessor()
                content = doc_processor.extract_text(tmp_file_path)
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
        
        elif text_input:
            content = text_input
        else:
            raise HTTPException(status_code=400, detail="Either text_input or file must be provided")
        
        # Get form template
        if form_type not in FORM_TEMPLATES:
            raise HTTPException(status_code=400, detail=f"Unsupported form type: {form_type}")
        
        template = FORM_TEMPLATES[form_type]
        
        # Use LLM to interpret content and extract field values
        llm_service = LLMService()
        interpreted_fields = await llm_service.interpret_form_content(
            content=content,
            form_type=form_type,
            template_fields=template["fields"]
        )
        
        # Convert to FormField objects
        fields = []
        for field_template in template["fields"]:
            field_value = interpreted_fields.get(field_template["name"], "")
            fields.append(FormField(
                name=field_template["name"],
                value=field_value,
                type=field_template["type"],
                required=field_template["required"],
                description=field_template.get("description")
            ))
        
        return FormInterpretationResponse(
            success=True,
            form_type=form_type,
            fields=fields,
            message="Content interpreted successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interpreting form: {str(e)}")

@router.post("/generate-form-document/", response_model=DocumentGenerationResponse)
async def generate_form_document(request: GenerateFormDocumentRequest):
    """
    Generate a completed form document from interpreted fields
    """
    try:
        if request.form_type not in FORM_TEMPLATES:
            raise HTTPException(status_code=400, detail=f"Unsupported form type: {request.form_type}")
        
        template = FORM_TEMPLATES[request.form_type]
        
        # Generate document content based on form type
        document_content = generate_document_content(request.form_type, request.fields, template)
        
        # Save document to local storage
        output_dir = Path("filled_templates")
        output_dir.mkdir(exist_ok=True)
        
        filename = f"interpreted_{request.form_type}_{request.device_id}.txt"
        output_path = output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(document_content)
        
        return DocumentGenerationResponse(
            success=True,
            generated_document=document_content,
            download_url=f"/api/interpreted-forms/download/{filename}",
            message="Document generated successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating document: {str(e)}")

def generate_document_content(form_type: str, fields: List[FormField], template: dict) -> str:
    """
    Generate formatted document content based on form type and fields
    """
    field_dict = {field.name: field.value for field in fields}
    
    if form_type == "affidavit":
        return f"""
AFFIDAVIT

State of {field_dict.get('state', '[STATE]')}
County of {field_dict.get('county', '[COUNTY]')}

I, {field_dict.get('affiant_name', '[AFFIANT NAME]')}, being duly sworn, depose and state:

1. That I am of legal age and competent to make this affidavit.

2. That I reside at {field_dict.get('affiant_address', '[ADDRESS]')}.

3. That {field_dict.get('statement', '[STATEMENT]')}.

4. That this affidavit is made by me voluntarily, without any duress, menace, fraud, misrepresentation or undue influence of any person whomsoever.

5. That the statements made in this affidavit are true and correct to the best of my knowledge and belief.

_____________________________
{field_dict.get('affiant_name', '[AFFIANT NAME]')}
Affiant

Subscribed and sworn to before me this {field_dict.get('date', '[DATE]')}.

_____________________________
{field_dict.get('notary_name', '[NOTARY NAME]')}
Notary Public
"""
    
    elif form_type == "will":
        return f"""
LAST WILL AND TESTAMENT
OF
{field_dict.get('testator_name', '[TESTATOR NAME]')}

I, {field_dict.get('testator_name', '[TESTATOR NAME]')}, a resident of {field_dict.get('testator_address', '[ADDRESS]')}, being of sound mind and disposing memory, do hereby make, publish and declare this to be my Last Will and Testament, hereby revoking all former wills and codicils by me made.

FIRST: I direct that all my just debts and funeral expenses be paid as soon as practicable after my death.

SECOND: I nominate and appoint {field_dict.get('executor_name', '[EXECUTOR NAME]')}, residing at {field_dict.get('executor_address', '[EXECUTOR ADDRESS]')}, as Executor of this my Last Will and Testament.

THIRD: I give, devise and bequeath my property as follows:
{field_dict.get('assets_distribution', '[ASSETS DISTRIBUTION]')}

FOURTH: The beneficiaries of this will are:
{field_dict.get('beneficiaries', '[BENEFICIARIES]')}

IN WITNESS WHEREOF, I have hereunto set my hand this {field_dict.get('date', '[DATE]')}.

_____________________________
{field_dict.get('testator_name', '[TESTATOR NAME]')}
Testator

WITNESSES:
The foregoing instrument was signed by the Testator in our presence, and we, at the Testator's request and in the Testator's presence, and in the presence of each other, have subscribed our names as witnesses.

_____________________________     _____________________________
{field_dict.get('witness1_name', '[WITNESS 1]')}                    {field_dict.get('witness2_name', '[WITNESS 2]')}
Witness                            Witness
"""
    
    elif form_type == "power_of_attorney":
        return f"""
POWER OF ATTORNEY

KNOW ALL MEN BY THESE PRESENTS that I, {field_dict.get('principal_name', '[PRINCIPAL NAME]')}, of {field_dict.get('principal_address', '[PRINCIPAL ADDRESS]')}, do hereby constitute and appoint {field_dict.get('agent_name', '[AGENT NAME]')}, of {field_dict.get('agent_address', '[AGENT ADDRESS]')}, as my true and lawful attorney-in-fact.

POWERS GRANTED:
{field_dict.get('powers_granted', '[POWERS GRANTED]')}

This Power of Attorney shall become effective on {field_dict.get('effective_date', '[EFFECTIVE DATE]')}.

{f"This Power of Attorney shall expire on {field_dict.get('expiration_date')}" if field_dict.get('expiration_date') else "This Power of Attorney shall remain in effect until revoked by me."}

{field_dict.get('durability_clause', 'This Power of Attorney shall survive my disability or incapacity.')}

IN WITNESS WHEREOF, I have executed this Power of Attorney this _____ day of _________, 20__.

_____________________________
{field_dict.get('principal_name', '[PRINCIPAL NAME]')}
Principal
"""
    
    elif form_type == "contract":
        return f"""
CONTRACT AGREEMENT

This Agreement is made between {field_dict.get('party1_name', '[PARTY 1]')}, located at {field_dict.get('party1_address', '[PARTY 1 ADDRESS]')}, and {field_dict.get('party2_name', '[PARTY 2]')}, located at {field_dict.get('party2_address', '[PARTY 2 ADDRESS]')}.

SUBJECT MATTER:
{field_dict.get('contract_subject', '[CONTRACT SUBJECT]')}

TERMS AND CONDITIONS:
{field_dict.get('terms_conditions', '[TERMS AND CONDITIONS]')}

CONSIDERATION:
{field_dict.get('consideration', '[CONSIDERATION]')}

This agreement shall be effective from {field_dict.get('effective_date', '[EFFECTIVE DATE]')}{f" until {field_dict.get('termination_date')}" if field_dict.get('termination_date') else ""}.

IN WITNESS WHEREOF, the parties have executed this Agreement.

_____________________________     _____________________________
{field_dict.get('party1_name', '[PARTY 1]')}                    {field_dict.get('party2_name', '[PARTY 2]')}
Party 1                            Party 2

Date: ________________         Date: ________________
"""
    
    else:  # general form
        return f"""
GENERAL FORM

Name: {field_dict.get('full_name', '[FULL NAME]')}
Date of Birth: {field_dict.get('date_of_birth', '[DATE OF BIRTH]')}
Address: {field_dict.get('address', '[ADDRESS]')}
Phone: {field_dict.get('phone_number', '[PHONE]')}
Email: {field_dict.get('email', '[EMAIL]')}

Description/Purpose:
{field_dict.get('description', '[DESCRIPTION]')}

Date: ________________

Signature: _____________________________
"""

@router.get("/form-templates/")
async def get_form_templates():
    """
    Get available form templates
    """
    return {
        "templates": [
            {"value": key, "label": template["title"], "fields": len(template["fields"])}
            for key, template in FORM_TEMPLATES.items()
        ]
    }

@router.get("/form-template/{form_type}")
async def get_form_template(form_type: str):
    """
    Get specific form template details
    """
    if form_type not in FORM_TEMPLATES:
        raise HTTPException(status_code=404, detail="Form template not found")
    
    return FORM_TEMPLATES[form_type]
