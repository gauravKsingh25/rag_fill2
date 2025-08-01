from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import uuid
import logging
from pathlib import Path
import tempfile
import os
from docx import Document
import re

from app.models import TemplateRequest, TemplateResponse
from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from app.routers.devices import get_device

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload-and-fill", response_model=TemplateResponse)
async def upload_and_fill_template(
    device_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a template file and fill it with device knowledge"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Validate file type (only .docx for now)
        if not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=400,
                detail="Only .docx template files are supported"
            )
        
        # Read template content
        template_content = await file.read()
        
        # Process template
        filled_template_path, filled_fields, missing_fields = await process_template(
            template_content=template_content,
            filename=file.filename,
            device_id=device_id
        )
        
        return TemplateResponse(
            filled_template_url=f"/api/templates/download/{Path(filled_template_path).name}",
            filled_fields=filled_fields,
            missing_fields=missing_fields
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to process template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process template: {e}")

async def process_template(
    template_content: bytes,
    filename: str,
    device_id: str
) -> tuple[str, Dict[str, str], List[str]]:
    """Process template and fill placeholders using enhanced question-based approach"""
    try:
        # Create temporary file for processing
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
            temp_file.write(template_content)
            temp_file_path = temp_file.name
        
        # Load document
        doc = Document(temp_file_path)
        
        # Extract all text to analyze placeholders
        full_text = ""
        for paragraph in doc.paragraphs:
            full_text += paragraph.text + "\n"
        
        # Extract missing fields using enhanced pattern matching
        missing_field_info = await extract_missing_fields_enhanced(full_text)
        
        filled_fields = {}
        missing_fields = []
        print(missing_field_info)

        logger.info(f"🔍 Found {len(missing_field_info)} fields to fill: {[field['field_name'] for field in missing_field_info]}")
        
        # For each missing field, create targeted questions and search
        for field_info in missing_field_info:
            field_name = field_info['field_name']
            field_context = field_info['context']
            field_pattern = field_info['pattern']
            
            logger.info(f"🔍 Processing field: {field_name}")
            print(f"🔍 Field context: {field_context[:200]}...")  # Print first 200 chars of context

            # Generate multiple targeted questions for this field
            questions = await gemini_service.generate_field_questions(field_name, field_context)
            print(f"🔍 Generated questions: {questions}")
            
            # Search vector database with multiple queries
            all_search_results = []
            for question in questions:
                query_embedding = await gemini_service.get_embedding(question)
                search_results = await pinecone_service.search_vectors(
                    query_vector=query_embedding,
                    device_id=device_id,
                    top_k=5
                )
                all_search_results.extend(search_results)
            
            if all_search_results:
                # Remove duplicates and get unique content
                unique_results = {}
                for result in all_search_results:
                    if result.content not in unique_results:
                        unique_results[result.content] = result.score
                
                # Sort by relevance score
                sorted_results = sorted(unique_results.items(), key=lambda x: x[1], reverse=True)
                context_docs = [content for content, score in sorted_results[:5]]  # Top 5 results
                
                # Use enhanced field filling with context analysis
                field_value = await gemini_service.fill_template_field_enhanced(
                    field_name=field_name,
                    field_context=field_context,
                    context_docs=context_docs,
                    questions=questions,
                    device_id=device_id
                )
                
                if field_value and field_value.strip():
                    filled_fields[field_name] = field_value.strip()
                    logger.info(f"✅ Filled field '{field_name}': {field_value.strip()[:50]}...")
                else:
                    missing_fields.append(field_name)
                    logger.warning(f"❌ Could not fill field: {field_name}")
            else:
                missing_fields.append(field_name)
                logger.warning(f"❌ No search results for field: {field_name}")
        
        # Replace placeholders in document with enhanced pattern matching
        for paragraph in doc.paragraphs:
            original_text = paragraph.text
            for field_info in missing_field_info:
                field_name = field_info['field_name']
                field_pattern = field_info['pattern']
                
                if field_name in filled_fields:
                    value = filled_fields[field_name]
                    # Replace the exact pattern found
                    paragraph.text = paragraph.text.replace(field_pattern, value)
            
            if original_text != paragraph.text:
                logger.info(f"🔄 Updated paragraph: {original_text[:50]}... -> {paragraph.text[:50]}...")
        
        # Save filled template
        output_dir = Path("./filled_templates")
        output_dir.mkdir(exist_ok=True)
        
        filled_filename = f"filled_{uuid.uuid4().hex}_{filename}"
        filled_path = output_dir / filled_filename
        
        doc.save(str(filled_path))
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        logger.info(f"✅ Template processed: {len(filled_fields)} fields filled, {len(missing_fields)} missing")
        logger.info(f"✅ Filled fields: {list(filled_fields.keys())}")
        logger.info(f"❌ Missing fields: {missing_fields}")
        
        return str(filled_path), filled_fields, missing_fields
        
    except Exception as e:
        logger.error(f"❌ Failed to process template: {e}")
        raise

async def extract_missing_fields_enhanced(template_content: str) -> List[Dict[str, str]]:
    """Extract missing fields with enhanced pattern matching and context"""
    try:
        missing_fields = []
        
        # Define comprehensive patterns for missing fields
        patterns = [
            (r'\[MISSING\]', 'MISSING'),
            (r'\[TO BE FILLED\]', 'TO BE FILLED'),
            (r'\[.*?\]', 'BRACKET_PLACEHOLDER'),
            (r'\{.*?\}', 'BRACE_PLACEHOLDER'),
            (r'<.*?>', 'ANGLE_PLACEHOLDER'),
            (r'_{3,}', 'UNDERLINE_PLACEHOLDER'),  # Three or more underscores
            (r'\.{3,}', 'DOT_PLACEHOLDER'),      # Three or more dots
        ]
        
        lines = template_content.split('\n')
        
        for line_num, line in enumerate(lines):
            for pattern, pattern_type in patterns:
                matches = re.finditer(pattern, line)
                for match in matches:
                    matched_text = match.group()
                    
                    # Extract field name from context
                    field_name = extract_field_name_from_context(line, match.start(), matched_text)
                    
                    # Get surrounding context (previous and next lines)
                    context_lines = []
                    for i in range(max(0, line_num - 2), min(len(lines), line_num + 3)):
                        context_lines.append(lines[i].strip())
                    context = ' '.join(context_lines)
                    
                    missing_fields.append({
                        'field_name': field_name,
                        'pattern': matched_text,
                        'context': context,
                        'line': line.strip(),
                        'pattern_type': pattern_type
                    })
        
        # Remove duplicates
        unique_fields = {}
        for field in missing_fields:
            key = field['field_name']
            if key not in unique_fields:
                unique_fields[key] = field
        
        return list(unique_fields.values())
        
    except Exception as e:
        logger.error(f"❌ Failed to extract missing fields: {e}")
        return []

def extract_field_name_from_context(line: str, match_position: int, matched_text: str) -> str:
    """Extract field name from the context around the placeholder"""
    try:
        # Look for field names before the placeholder
        before_text = line[:match_position].strip()
        
        # Common patterns for field names
        field_patterns = [
            r'([A-Za-z\s]+):\s*$',  # "Field Name: [MISSING]"
            r'([A-Za-z\s]+)\s*$',   # "Field Name [MISSING]"
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, before_text)
            if match:
                field_name = match.group(1).strip()
                # Clean up common prefixes/suffixes
                field_name = re.sub(r'^(.*?)\b(No|Number|Name|Date|By)\b.*$', r'\1\2', field_name)
                return field_name.strip()
        
        # Fallback: use nearby words
        words = before_text.split()
        if words:
            # Take last 1-3 words as field name
            field_name = ' '.join(words[-3:]).strip(':').strip()
            if field_name:
                return field_name
        
        # Last resort: use the matched text itself
        return matched_text.strip('[]{}()<>_.')
        
    except Exception as e:
        logger.error(f"❌ Failed to extract field name from context: {e}")
        return matched_text

@router.get("/download/{filename}")
async def download_filled_template(filename: str):
    """Download a filled template file"""
    try:
        file_path = Path("./filled_templates") / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Template file not found")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download template: {e}")

@router.post("/analyze")
async def analyze_template(
    device_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Analyze a template to show what fields can be filled"""
    try:
        # Verify device exists
        await get_device(device_id)
        
        # Validate file type
        if not file.filename.endswith('.docx'):
            raise HTTPException(
                status_code=400,
                detail="Only .docx template files are supported"
            )
        
        # Read and analyze template
        template_content = await file.read()
        
        # Create temporary file for analysis
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as temp_file:
            temp_file.write(template_content)
            temp_file_path = temp_file.name
        
        try:
            # Load document and extract text
            doc = Document(temp_file_path)
            full_text = ""
            for paragraph in doc.paragraphs:
                full_text += paragraph.text + "\n"
            
            # Extract placeholder fields
            placeholder_fields = await gemini_service.extract_template_fields(full_text)
            
            # For each field, check if we have relevant information
            field_analysis = {}
            
            for field in placeholder_fields:
                # Search for information related to this field
                query_embedding = await gemini_service.get_embedding(f"information about {field}")
                
                search_results = await pinecone_service.search_vectors(
                    query_vector=query_embedding,
                    device_id=device_id,
                    top_k=3
                )
                
                field_analysis[field] = {
                    "can_fill": len(search_results) > 0,
                    "confidence": search_results[0].score if search_results else 0,
                    "sources": len(search_results)
                }
            
            return {
                "device_id": device_id,
                "template_filename": file.filename,
                "total_fields": len(placeholder_fields),
                "fillable_fields": len([f for f, a in field_analysis.items() if a["can_fill"]]),
                "field_analysis": field_analysis
            }
            
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to analyze template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze template: {e}")
