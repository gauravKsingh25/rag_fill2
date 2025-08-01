from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import uuid
import logging
import asyncio
from pathlib import Path
import tempfile
import os
from docx import Document
import re
from urllib.parse import unquote

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

@router.post("/analyze")
async def analyze_template(
    device_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Analyze a template to show what fields can be filled"""
    try:
        logger.info(f"📋 Starting template analysis for device: {device_id}")
        logger.info(f"📋 File: {file.filename}, Content-Type: {file.content_type}")
        
        # Verify device exists
        device = await get_device(device_id)
        logger.info(f"📋 Device verified: {device.name}")
        
        # Validate file type
        if not file.filename.endswith('.docx'):
            logger.error(f"❌ Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Only .docx template files are supported"
            )
        
        # Read and analyze template
        template_content = await file.read()
        logger.info(f"📋 Template content read: {len(template_content)} bytes")
        
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
            
            logger.info(f"📋 Extracted text length: {len(full_text)} characters")
            
            # Extract placeholder fields using enhanced detection
            missing_field_info = await extract_missing_fields_enhanced(full_text)
            logger.info(f"📋 Found {len(missing_field_info)} potential fields")
            
            # For each field, check if we have relevant information using optimized approach
            field_analysis = {}
            fillable_count = 0
            
            # OPTIMIZATION: Batch question generation for analysis
            try:
                logger.info("🚀 Generating questions for analysis in batch...")
                field_questions = await gemini_service.generate_questions_batch(missing_field_info)
                logger.info(f"✅ Generated questions for {len(field_questions)} fields")
            except Exception as e:
                logger.error(f"❌ Batch question generation failed: {e}")
                # Fallback to basic questions
                field_questions = {}
                for field_info in missing_field_info:
                    field_name = field_info['field_name']
                    field_questions[field_name] = [f"What is the {field_name}?"]
            
            # Analyze each field with generated questions
            for field_info in missing_field_info:
                field_name = field_info['field_name']
                field_context = field_info['context']
                
                logger.info(f"📋 Analyzing field: {field_name}")
                
                try:
                    # Use pre-generated questions
                    questions = field_questions.get(field_name, [f"What is the {field_name}?"])
                    logger.info(f"📋 Using {len(questions)} questions for {field_name}")
                    
                    # Search for information related to this field using multiple questions
                    all_search_results = []
                    best_score = 0
                    
                    for question in questions[:3]:  # Limit to 3 questions for analysis
                        query_embedding = await gemini_service.get_embedding(question)
                        search_results = await pinecone_service.search_vectors(
                            query_vector=query_embedding,
                            device_id=device_id,
                            top_k=3
                        )
                        all_search_results.extend(search_results)
                        
                        # Track best score
                        if search_results:
                            best_score = max(best_score, search_results[0].score)
                    
                    # Remove duplicates and get unique content
                    unique_results = {}
                    for result in all_search_results:
                        if result.content not in unique_results:
                            unique_results[result.content] = result.score
                    
                    can_fill = len(unique_results) > 0 and best_score > 0.3
                    confidence = best_score if can_fill else 0
                    
                    if can_fill:
                        fillable_count += 1
                    
                    logger.info(f"📋 Field {field_name}: can_fill={can_fill}, confidence={confidence:.3f}, sources={len(unique_results)}")
                    
                except Exception as field_error:
                    logger.error(f"❌ Error analyzing field {field_name}: {field_error}")
                    can_fill = False
                    confidence = 0
                    unique_results = {}
                    questions = []
                
                field_analysis[field_name] = {
                    "can_fill": can_fill,
                    "confidence": round(confidence, 3),
                    "sources": len(unique_results) if 'unique_results' in locals() else 0,
                    "context": field_context[:100] + "..." if len(field_context) > 100 else field_context,
                    "pattern_type": field_info.get('pattern_type', 'UNKNOWN'),
                    "questions_generated": len(questions) if 'questions' in locals() else 0
                }
            
            result = {
                "device_id": device_id,
                "template_filename": file.filename,
                "total_fields": len(missing_field_info),
                "fillable_fields": fillable_count,
                "field_analysis": field_analysis
            }
            
            logger.info(f"✅ Analysis complete: {fillable_count}/{len(missing_field_info)} fields fillable")
            return result
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to analyze template: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze template: {str(e)}")

@router.get("/download/{filename}")
async def download_filled_template(filename: str):
    """Download a filled template file"""
    try:
        # Decode URL-encoded filename
        decoded_filename = unquote(filename)
        logger.info(f"📥 Download request for: {filename} -> {decoded_filename}")
        
        # Ensure the filled_templates directory exists
        templates_dir = Path("./filled_templates")
        templates_dir.mkdir(exist_ok=True)
        
        # Try both original and decoded filenames
        possible_paths = [
            templates_dir / filename,
            templates_dir / decoded_filename
        ]
        
        file_path = None
        for path in possible_paths:
            logger.info(f"🔍 Checking path: {path}")
            if path.exists():
                file_path = path
                logger.info(f"✅ Found file at: {path}")
                break
        
        if not file_path:
            # List available files for debugging
            available_files = list(templates_dir.glob("*"))
            logger.error(f"❌ File not found. Available files: {[f.name for f in available_files]}")
            raise HTTPException(
                status_code=404, 
                detail=f"Template file not found. Requested: {decoded_filename}"
            )
        
        # Get the original filename for download (remove the UUID prefix)
        original_filename = decoded_filename
        if decoded_filename.startswith('filled_') and '_' in decoded_filename[7:]:
            # Remove "filled_" prefix and UUID
            parts = decoded_filename.split('_', 2)
            if len(parts) >= 3:
                original_filename = parts[2]
        
        logger.info(f"📤 Serving file: {file_path} as {original_filename}")
        
        return FileResponse(
            path=str(file_path),
            filename=original_filename,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to download template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download template: {e}")

@router.get("/stats/api-usage")
async def get_api_usage_stats():
    """Get API usage statistics for optimization monitoring"""
    try:
        stats = gemini_service.get_api_usage_stats()
        return {
            "gemini_api_stats": stats,
            "optimization_info": {
                "batching_enabled": True,
                "cache_enabled": True,
                "rate_limiting_enabled": True,
                "max_fields_per_batch": 8
            }
        }
    except Exception as e:
        logger.error(f"❌ Failed to get API stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get API stats: {e}")

async def process_template(
    template_content: bytes,
    filename: str,
    device_id: str
) -> tuple[str, Dict[str, str], List[str]]:
    """Process template and fill placeholders using optimized batch approach"""
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
        
        if not missing_field_info:
            logger.warning("No fields found to fill")
            # Save original template as filled template
            output_dir = Path("./filled_templates")
            output_dir.mkdir(exist_ok=True)
            
            safe_filename = re.sub(r'[^\w\s.-]', '', filename)
            filled_filename = f"filled_{uuid.uuid4().hex}_{safe_filename}"
            filled_path = output_dir / filled_filename
            
            doc.save(str(filled_path))
            
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
            return str(filled_path), {}, []
        
        # OPTIMIZATION 1: Batch question generation for all fields
        logger.info("� Generating questions for all fields in batch...")
        try:
            field_questions = await gemini_service.generate_questions_batch(missing_field_info)
            logger.info(f"✅ Generated questions for {len(field_questions)} fields")
        except Exception as e:
            logger.error(f"❌ Batch question generation failed: {e}")
            # Fallback to individual generation for critical fields
            field_questions = {}
            for field_info in missing_field_info[:5]:  # Limit to first 5 fields
                field_name = field_info['field_name']
                try:
                    questions = await gemini_service.generate_field_questions(
                        field_name, field_info['context']
                    )
                    field_questions[field_name] = questions
                except Exception as field_error:
                    logger.error(f"❌ Failed to generate questions for {field_name}: {field_error}")
                    field_questions[field_name] = [f"What is the {field_name}?"]
        
        # ENHANCED PARALLEL PROCESSING - Use the new optimized method
        logger.info("🚀 Using enhanced parallel processing...")
        try:
            # Configure parallel processing for optimal performance
            gemini_service.configure_parallel_processing(
                max_concurrent_api_calls=2,  # Conservative to avoid rate limits
                min_delay_between_calls=1.0,  # 1 second between calls
                max_batch_size=10  # 10 fields per batch for better token management
            )
            
            # Process all fields using the new parallel method
            processing_results = await gemini_service.process_template_fields_parallel(
                field_infos=missing_field_info,
                device_id=device_id,
                max_batch_size=10,  # Process 10 fields per API call
                max_concurrent_batches=2  # Max 2 concurrent API calls
            )
            
            # Extract filled fields and missing fields from results
            for field_name, result in processing_results.items():
                value = result.get('value')
                if value and value.strip():
                    filled_fields[field_name] = value.strip()
                    logger.info(f"✅ Filled '{field_name}': {value.strip()[:50]}...")
                else:
                    missing_fields.append(field_name)
                    logger.warning(f"❌ Could not fill field: {field_name}")
            
            logger.info(f"🎯 Enhanced parallel processing completed: {len(filled_fields)} filled, {len(missing_fields)} missing")
            
        except Exception as e:
            logger.error(f"❌ Enhanced parallel processing failed: {e}")
            logger.info("🔄 Falling back to original batch processing...")
            
            # FALLBACK: Original batch processing logic
        
        # OPTIMIZATION 2: Batch vector search and context collection
        logger.info("🔍 Collecting context for all fields...")
        fields_with_context = []
        
        for field_info in missing_field_info:
            field_name = field_info['field_name']
            field_context = field_info['context']
            questions = field_questions.get(field_name, [f"What is the {field_name}?"])
            
            # Search vector database with multiple queries for this field
            all_search_results = []
            for question in questions[:3]:  # Limit to 3 questions per field
                try:
                    query_embedding = await gemini_service.get_embedding(question)
                    search_results = await pinecone_service.search_vectors(
                        query_vector=query_embedding,
                        device_id=device_id,
                        top_k=3  # Reduced from 5 to 3
                    )
                    all_search_results.extend(search_results)
                except Exception as e:
                    logger.error(f"❌ Search failed for question '{question}': {e}")
            
            # Collect unique context documents
            context_docs = []
            if all_search_results:
                unique_results = {}
                for result in all_search_results:
                    if result.content not in unique_results:
                        unique_results[result.content] = result.score
                
                # Sort by relevance and take top results
                sorted_results = sorted(unique_results.items(), key=lambda x: x[1], reverse=True)
                context_docs = [content for content, score in sorted_results[:3]]  # Top 3 results
            
            fields_with_context.append({
                'field_name': field_name,
                'field_context': field_context,
                'questions': questions,
                'context_docs': context_docs
            })
        
        # OPTIMIZATION 3: Batch field filling (process in chunks of 8-10 fields)
        logger.info("✏️ Filling fields in optimized batches...")
        batch_size = 8  # Process 8 fields at a time to stay within token limits
        
        for i in range(0, len(fields_with_context), batch_size):
            batch = fields_with_context[i:i + batch_size]
            batch_field_names = [field['field_name'] for field in batch]
            
            logger.info(f"📦 Processing batch {i//batch_size + 1}: {batch_field_names}")
            
            try:
                # Fill this batch of fields
                batch_results = await gemini_service.fill_template_fields_batch(
                    batch, device_id
                )
                
                # Add successful results to filled_fields
                for field_name, value in batch_results.items():
                    if value and value.strip():
                        filled_fields[field_name] = value.strip()
                        logger.info(f"✅ Filled '{field_name}': {value.strip()[:50]}...")
                    else:
                        missing_fields.append(field_name)
                        logger.warning(f"❌ Could not fill field: {field_name}")
                        
                # Add small delay between batches to respect rate limits
                if i + batch_size < len(fields_with_context):
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"❌ Batch processing failed for batch {i//batch_size + 1}: {e}")
                # Fallback: try individual processing for this batch
                for field_data in batch:
                    field_name = field_data['field_name']
                    context_docs = field_data['context_docs']
                    
                    if context_docs:
                        try:
                            field_value = await gemini_service.fill_template_field_enhanced(
                                field_name=field_name,
                                field_context=field_data['field_context'],
                                context_docs=context_docs,
                                questions=field_data['questions'],
                                device_id=device_id
                            )
                            
                            if field_value and field_value.strip():
                                filled_fields[field_name] = field_value.strip()
                                logger.info(f"✅ Filled '{field_name}' (fallback): {field_value.strip()[:50]}...")
                            else:
                                missing_fields.append(field_name)
                        except Exception as field_error:
                            logger.error(f"❌ Individual fallback failed for {field_name}: {field_error}")
                            missing_fields.append(field_name)
                    else:
                        missing_fields.append(field_name)
        
        # Replace placeholders in document with enhanced pattern matching
        logger.info("🔄 Updating document with filled values...")
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
        
        # Create a cleaner filename without special characters that might cause issues
        safe_filename = re.sub(r'[^\w\s.-]', '', filename)
        filled_filename = f"filled_{uuid.uuid4().hex}_{safe_filename}"
        filled_path = output_dir / filled_filename
        
        doc.save(str(filled_path))
        
        # Verify the file was created
        if not filled_path.exists():
            raise Exception(f"Failed to save filled template to {filled_path}")
        
        logger.info(f"✅ Template saved to: {filled_path}")
        logger.info(f"✅ File size: {filled_path.stat().st_size} bytes")
        
        # Clean up temp file
        if os.path.exists(temp_file_path):
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
        
        # Define comprehensive patterns for missing fields - expanded for better detection
        patterns = [
            (r'\[MISSING\]', 'MISSING'),
            (r'\[TO BE FILLED\]', 'TO BE FILLED'),
            (r'\[.*?\]', 'BRACKET_PLACEHOLDER'),
            (r'\{.*?\}', 'BRACE_PLACEHOLDER'),
            (r'<.*?>', 'ANGLE_PLACEHOLDER'),
            (r'_{5,}', 'UNDERLINE_PLACEHOLDER'),  # Five or more underscores
            (r'\.{5,}', 'DOT_PLACEHOLDER'),      # Five or more dots
            (r'\s+_+\s+', 'SPACED_UNDERLINE'),   # Spaced underlines
            (r':\s*_+\s*', 'COLON_UNDERLINE'),   # Colon followed by underscores
            (r':\s*\.+\s*', 'COLON_DOTS'),       # Colon followed by dots
            (r'\b[A-Z\s]+:\s*$', 'LABEL_ONLY'),  # Labels without values (e.g., "NAME:" at end of line)
            (r'(?i)\b(fill\s+in|to\s+be\s+filled|insert\s+here|add\s+here|enter\s+here)\b', 'INSTRUCTION_TEXT'),
            # Enhanced patterns for better detection
            (r'_{3,}', 'SHORT_UNDERLINE'),       # Three or more underscores
            (r'\.{3,}', 'SHORT_DOT'),           # Three or more dots
            (r'\[\s*\]', 'EMPTY_BRACKET'),      # Empty brackets
            (r'\(\s*\)', 'EMPTY_PAREN'),        # Empty parentheses
        ]
        
        lines = template_content.split('\n')
        
        for line_num, line in enumerate(lines):
            # Skip empty lines
            if not line.strip():
                continue
                
            for pattern, pattern_type in patterns:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()
                    
                    # Extract field name from context
                    field_name = extract_field_name_from_context(line, match.start(), matched_text, pattern_type)
                    
                    # Skip if field name is too generic or empty
                    if not field_name or len(field_name.strip()) < 2:
                        continue
                        
                    # Get surrounding context (previous and next lines)
                    context_lines = []
                    for i in range(max(0, line_num - 3), min(len(lines), line_num + 4)):
                        if lines[i].strip():  # Only include non-empty lines
                            context_lines.append(lines[i].strip())
                    context = ' '.join(context_lines)
                    
                    missing_fields.append({
                        'field_name': field_name,
                        'pattern': matched_text,
                        'context': context,
                        'line': line.strip(),
                        'pattern_type': pattern_type,
                        'line_number': line_num
                    })
        
        # Also look for table-like structures and form fields
        missing_fields.extend(extract_table_fields(template_content))
        missing_fields.extend(extract_form_fields(template_content))
        
        # Remove duplicates and filter out generic fields
        unique_fields = {}
        for field in missing_fields:
            key = field['field_name'].lower().strip()
            # Skip overly generic or short field names
            if len(key) > 2 and key not in ['text', 'data', 'info', 'value', 'item', 'field']:
                if key not in unique_fields or len(field['context']) > len(unique_fields[key]['context']):
                    unique_fields[key] = field
        
        result = list(unique_fields.values())
        logger.info(f"🔍 Extracted {len(result)} unique fields: {[f['field_name'] for f in result]}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to extract missing fields: {e}")
        return []

def extract_field_name_from_context(line: str, match_position: int, matched_text: str, pattern_type: str) -> str:
    """Extract field name from the context around the placeholder with enhanced logic"""
    try:
        # Clean the line first
        clean_line = line.strip()
        before_text = clean_line[:match_position].strip()
        after_text = clean_line[match_position + len(matched_text):].strip()
        
        # Different strategies based on pattern type
        if pattern_type == 'LABEL_ONLY':
            # For labels like "NAME:", extract the label itself
            label_match = re.search(r'\b([A-Z\s]+):\s*$', before_text + matched_text, re.IGNORECASE)
            if label_match:
                return label_match.group(1).strip()
        
        # Look for field names before the placeholder
        field_patterns = [
            r'([A-Za-z][A-Za-z\s\d]+):\s*$',           # "Field Name: ___"
            r'([A-Za-z][A-Za-z\s\d]+)\s*$',            # "Field Name ___"
            r'([A-Za-z][A-Za-z\s\d]+)\s*[-–—]\s*$',    # "Field Name - ___"
            r'(\b[A-Z][A-Za-z\s]+\b).*$',              # Capitalized words
        ]
        
        for pattern in field_patterns:
            match = re.search(pattern, before_text)
            if match:
                field_name = match.group(1).strip()
                field_name = clean_field_name(field_name)
                if len(field_name) > 2:
                    return field_name
        
        # Look for field names after the placeholder (less common but possible)
        if not before_text.strip():
            after_patterns = [
                r'^\s*([A-Za-z][A-Za-z\s\d]+)',  # Text after placeholder
            ]
            for pattern in after_patterns:
                match = re.search(pattern, after_text)
                if match:
                    field_name = match.group(1).strip()
                    field_name = clean_field_name(field_name)
                    if len(field_name) > 2:
                        return field_name
        
        # Fallback: extract from surrounding context
        words = re.findall(r'\b[A-Za-z][A-Za-z\s]*\b', before_text)
        if words:
            # Take last meaningful words
            meaningful_words = [w.strip() for w in words if len(w.strip()) > 2]
            if meaningful_words:
                field_name = ' '.join(meaningful_words[-2:]).strip()
                return clean_field_name(field_name)
        
        # Last resort: generate descriptive name based on context
        return generate_descriptive_field_name(clean_line, matched_text)
        
    except Exception as e:
        logger.error(f"❌ Failed to extract field name from context: {e}")
        return clean_field_name(matched_text)

def clean_field_name(field_name: str) -> str:
    """Clean and normalize field names"""
    if not field_name:
        return ""
    
    # Remove common prefixes/suffixes and clean up
    field_name = re.sub(r'^(Enter|Insert|Add|Fill|Type|Write)\s+', '', field_name, flags=re.IGNORECASE)
    field_name = re.sub(r'\s+(here|below|above)$', '', field_name, flags=re.IGNORECASE)
    field_name = field_name.strip(' :.-_[]{}()<>')
    
    # Normalize spacing
    field_name = re.sub(r'\s+', ' ', field_name)
    
    # Capitalize appropriately
    if field_name.isupper() or field_name.islower():
        field_name = field_name.title()
    
    return field_name.strip()

def generate_descriptive_field_name(line: str, matched_text: str) -> str:
    """Generate a descriptive field name from the line context"""
    # Extract meaningful words from the line
    words = re.findall(r'\b[A-Za-z][A-Za-z]+\b', line)
    
    # Filter out common words
    common_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among', 'under', 'over'}
    meaningful_words = [w for w in words if w.lower() not in common_words and len(w) > 2]
    
    if meaningful_words:
        # Take first few meaningful words
        return ' '.join(meaningful_words[:3])
    
    return f"Field {hash(line) % 1000}"

def extract_table_fields(template_content: str) -> List[Dict[str, str]]:
    """Extract fields from table-like structures"""
    fields = []
    
    # Look for table patterns with underscores or dots
    table_patterns = [
        r'([A-Za-z][A-Za-z\s]+):\s*_{3,}',  # Name: ____
        r'([A-Za-z][A-Za-z\s]+)\s+_{3,}',   # Name ____
        r'([A-Za-z][A-Za-z\s]+):\s*\.{3,}', # Name: ....
    ]
    
    for pattern in table_patterns:
        matches = re.finditer(pattern, template_content)
        for match in matches:
            field_name = clean_field_name(match.group(1))
            if len(field_name) > 2:
                # Get context around the match
                start = max(0, match.start() - 100)
                end = min(len(template_content), match.end() + 100)
                context = template_content[start:end].replace('\n', ' ')
                
                fields.append({
                    'field_name': field_name,
                    'pattern': match.group(),
                    'context': context,
                    'line': match.group(),
                    'pattern_type': 'TABLE_FIELD'
                })
    
    return fields

def extract_form_fields(template_content: str) -> List[Dict[str, str]]:
    """Extract fields from form-like structures"""
    fields = []
    
    # Look for form field patterns
    form_patterns = [
        r'□\s*([A-Za-z][A-Za-z\s]+)',       # Checkbox with label
        r'☐\s*([A-Za-z][A-Za-z\s]+)',       # Empty checkbox with label
        r'\[\s*\]\s*([A-Za-z][A-Za-z\s]+)', # [  ] with label
        r'([A-Za-z][A-Za-z\s]+):\s*□',      # Label with checkbox
        r'([A-Za-z][A-Za-z\s]+):\s*☐',      # Label with empty checkbox
    ]
    
    for pattern in form_patterns:
        matches = re.finditer(pattern, template_content)
        for match in matches:
            field_name = clean_field_name(match.group(1))
            if len(field_name) > 2:
                # Get context around the match
                start = max(0, match.start() - 100)
                end = min(len(template_content), match.end() + 100)
                context = template_content[start:end].replace('\n', ' ')
                
                fields.append({
                    'field_name': field_name,
                    'pattern': match.group(),
                    'context': context,
                    'line': match.group(),
                    'pattern_type': 'FORM_FIELD'
                })
    
    return fields
