from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Dict, Any
import uuid
import logging
import re
from pathlib import Path
import tempfile
import os
from docx import Document

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
        
        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        full_text += paragraph.text + "\n"
        
        # Filter out table of contents, headers, footers before processing
        filtered_text = gemini_service._filter_template_content(full_text)
        
        # Extract missing fields using enhanced pattern matching on filtered content
        missing_field_info = await extract_missing_fields_enhanced(filtered_text)
        
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

            # ENHANCED: Generate comprehensive targeted questions for this field
            questions = await gemini_service.generate_field_questions(field_name, field_context)
            print(f"🔍 Generated questions: {questions}")
            
            # ENHANCED: Comprehensive multi-query search approach
            all_query_vectors = []
            
            # Generate embeddings for all questions
            for question in questions:
                query_embedding = await gemini_service.get_embedding(question)
                all_query_vectors.append(query_embedding)
            
            # Also add direct field name and context embeddings
            field_embedding = await gemini_service.get_embedding(field_name)
            all_query_vectors.append(field_embedding)
            
            # Add context-aware embedding
            context_query = f"{field_name} information from {field_context[:100]}"
            context_embedding = await gemini_service.get_embedding(context_query)
            all_query_vectors.append(context_embedding)
            
            # ENHANCED: Use comprehensive search for maximum document coverage
            comprehensive_results = await pinecone_service.comprehensive_search(
                query_vectors=all_query_vectors,
                device_id=device_id,
                top_k_per_query=10,  # More results per query
                final_top_k=20       # More final results for comprehensive analysis
            )
            
            if comprehensive_results:
                # Extract high-quality context documents
                context_docs = []
                high_importance_docs = []
                
                for result in comprehensive_results:
                    content = result.content
                    metadata = result.metadata
                    
                    if len(content) > 50:  # Ensure meaningful content
                        context_docs.append(content)
                        
                        # Separate high-importance content
                        importance_score = metadata.get('importance_score', 0.5)
                        if importance_score > 0.7 or metadata.get('has_form_fields', False):
                            high_importance_docs.append(content)
                
                # Prioritize high-importance documents but include comprehensive context
                final_context_docs = high_importance_docs[:10] + context_docs[:15]
                final_context_docs = list(dict.fromkeys(final_context_docs))  # Remove duplicates while preserving order
                
                if len(final_context_docs) >= 5:  # Ensure sufficient context
                    # Use enhanced field filling with comprehensive context analysis
                    field_value = await gemini_service.fill_template_field_enhanced(
                        field_name=field_name,
                        field_context=field_context,
                        context_docs=final_context_docs,
                        questions=questions,
                        device_id=device_id
                    )
                    
                    if field_value and field_value.strip():
                        filled_fields[field_name] = field_value.strip()
                        logger.info(f"✅ Filled field '{field_name}': {field_value.strip()[:50]}...")
                        print(f"✅ Filled '{field_name}' with: {field_value.strip()}")
                    else:
                        missing_fields.append(field_name)
                        logger.warning(f"❌ Could not fill field: {field_name} (AI could not extract value)")
                        print(f"❌ Could not extract value for: {field_name}")
                else:
                    missing_fields.append(field_name)
                    logger.warning(f"❌ Could not fill field: {field_name} (insufficient context documents: {len(final_context_docs)})")
                    print(f"❌ Insufficient context for: {field_name} (only {len(final_context_docs)} docs)")
            else:
                missing_fields.append(field_name)
                logger.warning(f"❌ No search results for field: {field_name}")
                print(f"❌ No search results for: {field_name}")
        
        # Replace placeholders in document with enhanced pattern matching
        replacement_count = 0
        for paragraph in doc.paragraphs:
            original_text = paragraph.text
            updated_text = original_text
            
            for field_info in missing_field_info:
                field_name = field_info['field_name']
                field_pattern = field_info['pattern']
                pattern_type = field_info['pattern_type']
                
                if field_name in filled_fields:
                    value = filled_fields[field_name]
                    
                    # Enhanced replacement based on pattern type
                    if pattern_type == 'COLON_FIELD':
                        # For colon fields, append the value after the colon
                        if field_pattern in updated_text:
                            updated_text = updated_text.replace(field_pattern, f"{field_pattern} {value}")
                            replacement_count += 1
                    elif pattern_type in ['COLON_FIELD_END', 'COLON_FIELD_INLINE']:
                        # Handle different colon field variations
                        colon_pattern = f"{field_name}:"
                        if colon_pattern in updated_text:
                            # Replace "Field Name:" with "Field Name: Value"
                            updated_text = updated_text.replace(colon_pattern, f"{colon_pattern} {value}")
                            replacement_count += 1
                    elif pattern_type in ['LONG_UNDERLINE', 'SHORT_UNDERLINE']:
                        # For underlines, replace with value but preserve some formatting
                        if field_pattern in updated_text:
                            # Keep the format but replace underlines with value
                            if len(value) <= len(field_pattern):
                                # Value fits within underlines
                                centered_value = value.center(len(field_pattern))
                                updated_text = updated_text.replace(field_pattern, centered_value)
                            else:
                                # Value is longer than underlines
                                updated_text = updated_text.replace(field_pattern, value)
                            replacement_count += 1
                    elif pattern_type in ['DATE_UNDERLINE', 'DATE_FORMAT', 'DATE_FORMAT_US']:
                        # For date fields, format appropriately
                        if field_pattern in updated_text:
                            # Try to format as date if possible
                            formatted_value = format_date_value(value, pattern_type)
                            updated_text = updated_text.replace(field_pattern, formatted_value)
                            replacement_count += 1
                    else:
                        # Standard replacement for other pattern types
                        if field_pattern in updated_text:
                            updated_text = updated_text.replace(field_pattern, value)
                            replacement_count += 1
            
            # Update paragraph if text changed
            if updated_text != original_text:
                paragraph.text = updated_text
                logger.info(f"🔄 Updated paragraph: {original_text[:50]}... -> {updated_text[:50]}...")
        
        # Also check tables for missing fields (tables are separate from paragraphs in docx)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        original_text = paragraph.text
                        updated_text = original_text
                        
                        for field_info in missing_field_info:
                            field_name = field_info['field_name']
                            field_pattern = field_info['pattern']
                            pattern_type = field_info['pattern_type']
                            
                            if field_name in filled_fields and field_pattern in updated_text:
                                value = filled_fields[field_name]
                                
                                if pattern_type == 'COLON_FIELD':
                                    updated_text = updated_text.replace(field_pattern, f"{field_pattern} {value}")
                                else:
                                    updated_text = updated_text.replace(field_pattern, value)
                                replacement_count += 1
                        
                        if updated_text != original_text:
                            paragraph.text = updated_text
                            logger.info(f"🔄 Updated table cell: {original_text[:30]}... -> {updated_text[:30]}...")
        
        logger.info(f"🔄 Made {replacement_count} replacements in document")
        
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
    """Extract missing fields with comprehensive pattern matching and context analysis, focusing on main content"""
    try:
        missing_fields = []
        
        # Define comprehensive patterns for missing fields (order matters - more specific first)
        patterns = [
            # Explicit missing markers
            (r'\[MISSING\]', 'MISSING_MARKER'),
            (r'\[TO BE FILLED\]', 'TO_BE_FILLED_MARKER'),
            (r'\[FILL\s*IN\]', 'FILL_IN_MARKER'),
            (r'\[TBD\]', 'TBD_MARKER'),
            (r'\[TBC\]', 'TBC_MARKER'),
            (r'\[PLACEHOLDER\]', 'PLACEHOLDER_MARKER'),
            
            # Bracketed placeholders (more specific patterns first)
            (r'\[(?:Enter|Insert|Add|Type)\s+[^\]]*\]', 'INSTRUCTION_BRACKET'),
            (r'\[[A-Za-z][^\]]*\]', 'BRACKET_PLACEHOLDER'),
            
            # Curly braces placeholders
            (r'\{[A-Za-z][^}]*\}', 'BRACE_PLACEHOLDER'),
            
            # Angle bracket placeholders
            (r'<(?:Enter|Insert|Add|Type)\s+[^>]*>', 'INSTRUCTION_ANGLE'),
            (r'<[A-Za-z][^>]*>', 'ANGLE_PLACEHOLDER'),
            
            # Underlines and dots (common form field patterns)
            (r'_{5,}', 'LONG_UNDERLINE'),      # Five or more underscores (signature lines)
            (r'_{3,4}', 'SHORT_UNDERLINE'),    # Three to four underscores (short fields)
            (r'\.{4,}', 'LONG_DOTS'),          # Four or more dots
            (r'\.{3}', 'THREE_DOTS'),          # Exactly three dots
            
            # Form field patterns with colons - FOCUS ON THESE
            (r'[A-Za-z][A-Za-z\s]*:\s*$', 'COLON_FIELD_END'),           # "Field Name: " at end of line
            (r'[A-Za-z][A-Za-z\s]*:\s*(?=\s|$)', 'COLON_FIELD_INLINE'), # "Field Name: " followed by space
            
            # Table cell patterns
            (r'\|\s*\|\s*\|', 'EMPTY_TABLE_CELL'),  # Empty table cells
            
            # Date patterns
            (r'__/__/____', 'DATE_UNDERLINE'),
            (r'DD/MM/YYYY', 'DATE_FORMAT'),
            (r'MM/DD/YYYY', 'DATE_FORMAT_US'),
            (r'Date:\s*$', 'DATE_FIELD'),
            
            # Signature patterns
            (r'Signature:\s*$', 'SIGNATURE_FIELD'),
            (r'Signed:\s*$', 'SIGNED_FIELD'),
            (r'By:\s*$', 'BY_FIELD'),
            
            # Number patterns
            (r'No\.?\s*:\s*$', 'NUMBER_FIELD'),
            (r'#\s*:\s*$', 'HASH_NUMBER_FIELD'),
        ]
        
        lines = template_content.split('\n')
        
        # Process each line for patterns
        for line_num, line in enumerate(lines):
            original_line = line
            
            # Skip lines that look like TOC entries or headers/footers
            if is_toc_or_header_line(line):
                continue
            
            # First, handle colon-based fields specially (MAIN FOCUS)
            colon_fields = extract_colon_fields(line, line_num, lines)
            missing_fields.extend(colon_fields)
            
            # Then handle other patterns
            for pattern, pattern_type in patterns:
                if pattern_type.startswith('COLON_'):
                    continue  # Already handled above
                    
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()
                    
                    # Extract field name from context
                    field_name = extract_field_name_from_context_enhanced(
                        line, match.start(), matched_text, pattern_type
                    )
                    
                    # Skip if field name is too generic or empty
                    if not field_name or len(field_name.strip()) < 2:
                        continue
                    
                    # Get surrounding context (more context for better understanding)
                    context_lines = []
                    for i in range(max(0, line_num - 3), min(len(lines), line_num + 4)):
                        if i < len(lines) and not is_toc_or_header_line(lines[i]):
                            context_lines.append(lines[i].strip())
                    context = ' '.join(context_lines)
                    
                    missing_fields.append({
                        'field_name': field_name,
                        'pattern': matched_text,
                        'context': context,
                        'line': line.strip(),
                        'pattern_type': pattern_type,
                        'line_number': line_num,
                        'position': match.start()
                    })
        
        # Remove duplicates and rank by importance
        unique_fields = {}
        for field in missing_fields:
            key = field['field_name'].lower().strip()
            
            # Prefer more specific pattern types
            if key not in unique_fields or is_better_pattern_type(field['pattern_type'], unique_fields[key]['pattern_type']):
                unique_fields[key] = field
                unique_fields[key]['field_name'] = field['field_name']  # Keep original case
        
        # Sort by line number for logical processing order
        result = sorted(unique_fields.values(), key=lambda x: x.get('line_number', 0))
        
        logger.info(f"🔍 Extracted {len(result)} unique fields from {len(missing_fields)} total matches")
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to extract missing fields: {e}")
        return []

def is_toc_or_header_line(line: str) -> bool:
    """Check if a line is part of TOC, header, or footer and should be skipped"""
    line_lower = line.lower().strip()
    
    # Empty lines are ok
    if not line_lower:
        return False
    
    # Check for TOC patterns
    toc_patterns = [
        r'table\s+of\s+contents',
        r'contents',
        r'^\d+\.\s*.+\.\.\.\.\s*\d+$',  # TOC entry with dots
        r'^\d+\.\d+\s*.+\s+\d+\s*$',   # TOC sub-entry  
        r'^[A-Z\s]+\s+\d+\s*$',        # All caps with page number
        r'page\s+\d+',
        r'^\s*\d+\s*$',                 # Page number alone
        r'\.{3,}',                      # Dot leaders
    ]
    
    # Check for header/footer patterns
    header_footer_patterns = [
        r'header',
        r'footer', 
        r'confidential',
        r'proprietary',
        r'copyright',
        r'©\s*\d{4}',
        r'revision\s+\d+',
        r'version\s+\d+',
    ]
    
    for pattern in toc_patterns + header_footer_patterns:
        if re.search(pattern, line_lower):
            return True
    
    return False

def extract_colon_fields(line: str, line_num: int, all_lines: List[str]) -> List[Dict[str, str]]:
    """Extract fields that end with colons (form fields) - MAIN FOCUS for template filling"""
    colon_fields = []
    
    try:
        # Skip this line if it's part of TOC or headers
        if is_toc_or_header_line(line):
            return colon_fields
        
        # Pattern for fields ending with colon
        colon_pattern = r'([A-Za-z][A-Za-z\s\(\)/&-]*?):\s*$'
        matches = re.finditer(colon_pattern, line.strip())
        
        for match in matches:
            field_text = match.group(1).strip()
            
            # Clean up common prefixes and patterns
            field_text = re.sub(r'^\d+[\.\)]\s*', '', field_text)  # Remove numbering
            field_text = re.sub(r'^[a-z]\)\s*', '', field_text)    # Remove a), b), c) numbering
            
            # Skip very short or common words that are likely not real fields
            if len(field_text) < 3 or field_text.lower() in ['the', 'and', 'for', 'with', 'from', 'page', 'section']:
                continue
            
            # Skip TOC-like entries even if they have colons
            if re.search(r'\d+\s*$', field_text) or re.search(r'page|section|chapter', field_text.lower()):
                continue
            
            # Get context from surrounding lines (excluding TOC/header lines)
            context_lines = []
            for i in range(max(0, line_num - 2), min(len(all_lines), line_num + 3)):
                if i < len(all_lines) and not is_toc_or_header_line(all_lines[i]):
                    context_lines.append(all_lines[i].strip())
            context = ' '.join(context_lines)
            
            colon_fields.append({
                'field_name': field_text,
                'pattern': f"{field_text}:",
                'context': context,
                'line': line.strip(),
                'pattern_type': 'COLON_FIELD',
                'line_number': line_num,
                'position': match.start()
            })
    
    except Exception as e:
        logger.error(f"❌ Failed to extract colon fields: {e}")
    
    return colon_fields

def is_better_pattern_type(new_type: str, existing_type: str) -> bool:
    """Determine if a new pattern type is better than existing one"""
    # Priority order (higher number = better)
    priority = {
        'MISSING_MARKER': 10,
        'TO_BE_FILLED_MARKER': 9,
        'COLON_FIELD': 8,
        'INSTRUCTION_BRACKET': 7,
        'INSTRUCTION_ANGLE': 7,
        'BRACKET_PLACEHOLDER': 6,
        'BRACE_PLACEHOLDER': 6,
        'ANGLE_PLACEHOLDER': 5,
        'DATE_FIELD': 4,
        'SIGNATURE_FIELD': 4,
        'NUMBER_FIELD': 4,
        'LONG_UNDERLINE': 3,
        'SHORT_UNDERLINE': 2,
        'LONG_DOTS': 2,
        'THREE_DOTS': 1,
    }
    
    return priority.get(new_type, 0) > priority.get(existing_type, 0)

def format_date_value(value: str, pattern_type: str) -> str:
    """Format date values according to the expected pattern"""
    try:
        # If value is already in a date format, return as is
        if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', value):
            return value
        
        # If it's a date word, try to format it
        from datetime import datetime
        import re
        
        # Try to extract date components from text
        date_patterns = [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
            r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})',    # YYYY/MM/DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, value)
            if match:
                if pattern_type == 'DATE_FORMAT_US':
                    return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
                else:
                    return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
        
        # If no date pattern found, return original value
        return value
        
    except:
        return value

def extract_field_name_from_context_enhanced(
    line: str, 
    match_position: int, 
    matched_text: str, 
    pattern_type: str
) -> str:
    """Enhanced field name extraction with better context understanding"""
    try:
        # For colon fields, the field name is already in the matched text
        if pattern_type == 'COLON_FIELD':
            return matched_text.rstrip(':').strip()
        
        # Look for field names before the placeholder
        before_text = line[:match_position].strip()
        after_text = line[match_position + len(matched_text):].strip()
        
        # Enhanced patterns for field names
        field_patterns = [
            # Most specific patterns first
            r'([A-Za-z][A-Za-z\s\(\)/&-]*?):\s*$',                    # "Field Name: [MISSING]"
            r'(\b[A-Z][A-Za-z\s]*(?:No|Number|Name|Date|ID|Code))\s*$', # "Document Number [MISSING]"
            r'(\b[A-Z][A-Za-z\s]{2,})\s*$',                           # "Generic Name [MISSING]"
            r'([A-Za-z][A-Za-z\s]*)\s*$',                             # Any text before placeholder
        ]
        
        # Try to extract from before text
        for pattern in field_patterns:
            match = re.search(pattern, before_text)
            if match:
                field_name = match.group(1).strip()
                field_name = clean_field_name(field_name)
                if field_name and len(field_name) > 1:
                    return field_name
        
        # If no good match before, try after text for certain patterns
        if pattern_type in ['LONG_UNDERLINE', 'SHORT_UNDERLINE']:
            after_patterns = [
                r'^([A-Za-z][A-Za-z\s]*)',  # Text after underlines
            ]
            for pattern in after_patterns:
                match = re.search(pattern, after_text)
                if match:
                    field_name = match.group(1).strip()
                    field_name = clean_field_name(field_name)
                    if field_name and len(field_name) > 1:
                        return field_name
        
        # Generate descriptive name based on pattern type
        return generate_field_name_from_pattern(matched_text, pattern_type, line)
        
    except Exception as e:
        logger.error(f"❌ Failed to extract field name from context: {e}")
        return matched_text

def clean_field_name(field_name: str) -> str:
    """Clean and standardize field names"""
    try:
        # Remove common prefixes (numbering, bullets, etc.)
        field_name = re.sub(r'^\d+[\.\)]\s*', '', field_name)  # Remove "1. ", "2) "
        field_name = re.sub(r'^[a-z]\)\s*', '', field_name)    # Remove "a) ", "b) "
        field_name = re.sub(r'^\W+', '', field_name)           # Remove leading non-word chars
        
        # Remove common suffixes that don't add value
        field_name = re.sub(r'\s*(is|are|was|were)\s*$', '', field_name, flags=re.IGNORECASE)
        
        # Standardize spacing
        field_name = re.sub(r'\s+', ' ', field_name).strip()
        
        # Title case for better readability
        if field_name and not field_name.isupper():
            field_name = field_name.title()
        
        return field_name
    except:
        return field_name

def generate_field_name_from_pattern(matched_text: str, pattern_type: str, line: str) -> str:
    """Generate descriptive field names based on pattern type"""
    try:
        # Create descriptive names based on pattern type
        pattern_names = {
            'MISSING_MARKER': 'Missing Information',
            'TO_BE_FILLED_MARKER': 'To Be Filled',
            'FILL_IN_MARKER': 'Fill In',
            'TBD_MARKER': 'To Be Determined',
            'TBC_MARKER': 'To Be Confirmed',
            'PLACEHOLDER_MARKER': 'Placeholder',
            'BRACKET_PLACEHOLDER': 'Information',
            'BRACE_PLACEHOLDER': 'Information',
            'ANGLE_PLACEHOLDER': 'Information', 
            'INSTRUCTION_BRACKET': 'Instruction Field',
            'INSTRUCTION_ANGLE': 'Instruction Field',
            'LONG_UNDERLINE': 'Signature',
            'SHORT_UNDERLINE': 'Field',
            'LONG_DOTS': 'Information',
            'THREE_DOTS': 'Continuation',
            'DATE_UNDERLINE': 'Date',
            'DATE_FORMAT': 'Date',
            'DATE_FORMAT_US': 'Date',
            'DATE_FIELD': 'Date',
            'SIGNATURE_FIELD': 'Signature',
            'SIGNED_FIELD': 'Signature',
            'BY_FIELD': 'Signed By',
            'NUMBER_FIELD': 'Number',
            'HASH_NUMBER_FIELD': 'Number',
            'EMPTY_TABLE_CELL': 'Table Data',
        }
        
        base_name = pattern_names.get(pattern_type, 'Field')
        
        # Try to make it more specific based on context
        line_lower = line.lower()
        
        # Check for context clues in the line
        if 'name' in line_lower:
            return 'Name'
        elif 'date' in line_lower:
            return 'Date'
        elif 'number' in line_lower or 'no.' in line_lower or '#' in line_lower:
            return 'Number'
        elif 'model' in line_lower:
            return 'Model'
        elif 'version' in line_lower:
            return 'Version'
        elif 'serial' in line_lower:
            return 'Serial Number'
        elif 'manufacturer' in line_lower:
            return 'Manufacturer'
        elif 'generic' in line_lower:
            return 'Generic Name'
        elif 'document' in line_lower:
            return 'Document'
        elif 'signature' in line_lower or 'sign' in line_lower:
            return 'Signature'
        elif 'address' in line_lower:
            return 'Address'
        elif 'phone' in line_lower or 'tel' in line_lower:
            return 'Phone'
        elif 'email' in line_lower:
            return 'Email'
        
        return base_name
        
    except:
        return 'Field'

def extract_field_name_from_context(line: str, match_position: int, matched_text: str) -> str:
    """Legacy function - keeping for compatibility"""
    return extract_field_name_from_context_enhanced(line, match_position, matched_text, 'UNKNOWN')

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
            
            # Also extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for paragraph in cell.paragraphs:
                            full_text += paragraph.text + "\n"
            
            # Filter out unwanted content before field extraction
            filtered_text = gemini_service._filter_template_content(full_text)
            
            # Extract placeholder fields from filtered content
            placeholder_fields = await gemini_service.extract_template_fields(filtered_text)
            
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
