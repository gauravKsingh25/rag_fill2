"""
Document Reverse Processor Service
Converts filled documents back to blank templates by removing answers and keeping only question fields
"""

import os
import re
import uuid
import logging
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
from io import BytesIO
import tempfile
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import zipfile

# Import OCR service for PDF processing
from app.services.google_vision_ocr_service import google_vision_ocr_service

logger = logging.getLogger(__name__)

class DocumentReverseProcessor:
    """Service to convert filled documents back to blank templates"""
    
    def __init__(self):
        self.output_dir = Path("./blank_templates")
        self.output_dir.mkdir(exist_ok=True)
        
        # Patterns to identify form fields and answers
        self.field_patterns = [
            # Common field patterns
            r'([A-Za-z\s]+):\s*([^\n\r]+)',  # Label: Answer
            r'([A-Za-z\s]+)\s*[=]\s*([^\n\r]+)',  # Label = Answer
            r'([A-Za-z\s]+)\s*[-]\s*([^\n\r]+)',  # Label - Answer
            r'([A-Za-z\s]+)\s*[>]\s*([^\n\r]+)',  # Label > Answer
            
            # Form-like patterns
            r'(\[.*?\])\s*([^\n\r\[]+)',  # [Field] Answer
            r'(\{.*?\})\s*([^\n\r\{]+)',  # {Field} Answer
            r'(_+)\s*([^\n\r_]+)',  # _____ Answer (underline fields)
            
            # Table-like patterns
            r'([A-Za-z\s]+)\s*\|\s*([^\n\r\|]+)',  # Field | Answer
            r'([A-Za-z\s]+)\s*\t\s*([^\n\r\t]+)',  # Field    Answer (tab separated)
        ]
        
        # Common field labels to preserve
        self.common_field_labels = [
            'name', 'date', 'number', 'model', 'serial', 'version', 'manufacturer',
            'device', 'type', 'category', 'description', 'specifications',
            'address', 'phone', 'email', 'contact', 'company', 'organization',
            'reference', 'document', 'revision', 'approval', 'certification',
            'standard', 'compliance', 'regulation', 'requirement'
        ]
        
        logger.info("🔄 Document Reverse Processor initialized")
    
    async def process_filled_document(
        self, 
        file_content: bytes, 
        filename: str, 
        device_id: str
    ) -> Dict[str, Any]:
        """
        Main method to process a filled document and create a blank template
        """
        try:
            logger.info(f"🔄 Starting reverse processing for {filename}")
            
            file_extension = Path(filename).suffix.lower()
            
            if file_extension == '.pdf':
                return await self._process_filled_pdf(file_content, filename, device_id)
            elif file_extension in ['.docx', '.doc']:
                return await self._process_filled_word_doc(file_content, filename, device_id)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"❌ Failed to process filled document {filename}: {e}")
            raise
    
    async def _process_filled_pdf(
        self, 
        file_content: bytes, 
        filename: str, 
        device_id: str
    ) -> Dict[str, Any]:
        """Process filled PDF: OCR -> Extract text -> Create blank template -> Convert to Word"""
        try:
            logger.info(f"📄 Processing filled PDF: {filename}")
            
            # Step 1: Extract text using OCR
            logger.info("🔍 Step 1: Extracting text using OCR...")
            extracted_text, ocr_metadata = await google_vision_ocr_service.process_document(
                file_content, filename
            )
            
            if not extracted_text:
                raise ValueError("Could not extract text from PDF using OCR")
            
            logger.info(f"✅ OCR extracted {len(extracted_text)} characters")
            
            # Step 2: Analyze and create blank template
            logger.info("🔄 Step 2: Creating blank template from extracted text...")
            blank_template_text = self._create_blank_template_from_text(extracted_text)
            
            # Step 3: Convert to Word document
            logger.info("📝 Step 3: Converting to Word document...")
            word_doc_path = await self._create_word_document_from_text(
                blank_template_text, filename, device_id
            )
            
            return {
                "status": "success",
                "message": f"Successfully converted filled PDF to blank template",
                "original_filename": filename,
                "blank_template_path": word_doc_path,
                "blank_template_url": f"/api/document-reverse/download/{Path(word_doc_path).name}",
                "processing_details": {
                    "original_format": "pdf",
                    "output_format": "docx",
                    "ocr_used": True,
                    "text_length": len(extracted_text),
                    "template_length": len(blank_template_text),
                    "ocr_metadata": ocr_metadata
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process PDF {filename}: {e}")
            raise
    
    async def _process_filled_word_doc(
        self, 
        file_content: bytes, 
        filename: str, 
        device_id: str
    ) -> Dict[str, Any]:
        """Process filled Word document: Extract text -> Create blank template -> Save as Word"""
        try:
            logger.info(f"📝 Processing filled Word document: {filename}")
            
            # Step 1: Extract text from Word document
            logger.info("📄 Step 1: Extracting text from Word document...")
            extracted_text = self._extract_text_from_word_doc(file_content)
            
            if not extracted_text:
                raise ValueError("Could not extract text from Word document")
            
            logger.info(f"✅ Extracted {len(extracted_text)} characters from Word document")
            
            # Step 2: Create blank template
            logger.info("🔄 Step 2: Creating blank template...")
            blank_template_text = self._create_blank_template_from_text(extracted_text)
            
            # Step 3: Create new Word document
            logger.info("📝 Step 3: Creating new Word document...")
            word_doc_path = await self._create_word_document_from_text(
                blank_template_text, filename, device_id
            )
            
            return {
                "status": "success",
                "message": f"Successfully converted filled Word document to blank template",
                "original_filename": filename,
                "blank_template_path": word_doc_path,
                "blank_template_url": f"/api/document-reverse/download/{Path(word_doc_path).name}",
                "processing_details": {
                    "original_format": "docx",
                    "output_format": "docx",
                    "ocr_used": False,
                    "text_length": len(extracted_text),
                    "template_length": len(blank_template_text)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process Word document {filename}: {e}")
            raise
    
    def _extract_text_from_word_doc(self, file_content: bytes) -> str:
        """Extract text from Word document while preserving structure"""
        try:
            doc_file = BytesIO(file_content)
            doc = Document(doc_file)
            
            text_parts = []
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from Word document: {e}")
            raise
    
    def _create_blank_template_from_text(self, text: str) -> str:
        """
        Analyze filled text and convert it to a blank template by:
        1. Identifying field labels and their answers
        2. Removing answers and replacing with appropriate blanks
        3. Preserving the document structure
        """
        try:
            logger.info("🔄 Creating blank template from text...")
            
            lines = text.split('\n')
            template_lines = []
            
            for line in lines:
                if not line.strip():
                    template_lines.append(line)  # Preserve empty lines
                    continue
                
                # Process line to create blank template
                blank_line = self._process_line_for_blank_template(line)
                template_lines.append(blank_line)
            
            template_text = '\n'.join(template_lines)
            
            # Post-process to clean up and enhance the template
            template_text = self._post_process_template(template_text)
            
            logger.info(f"✅ Created blank template with {len(template_text)} characters")
            return template_text
            
        except Exception as e:
            logger.error(f"❌ Failed to create blank template: {e}")
            raise
    
    def _process_line_for_blank_template(self, line: str) -> str:
        """Process a single line to create blank template version"""
        try:
            original_line = line.strip()
            
            # Check if this line contains a field pattern
            for pattern in self.field_patterns:
                match = re.search(pattern, original_line, re.IGNORECASE)
                if match:
                    label = match.group(1).strip()
                    answer = match.group(2).strip() if len(match.groups()) > 1 else ""
                    
                    # Check if this looks like a form field
                    if self._is_likely_form_field(label, answer):
                        # Create blank version
                        blank_field = self._create_blank_field(label, answer, original_line)
                        logger.debug(f"🔄 Converted field: {original_line[:50]}... -> {blank_field[:50]}...")
                        return blank_field
            
            # Check for table-like structures
            if '|' in original_line and len(original_line.split('|')) > 1:
                return self._process_table_line(original_line)
            
            # Check for underline fields (_____)
            if '_' in original_line:
                return self._process_underline_field(original_line)
            
            # If no patterns match, return the original line (might be a header, instruction, etc.)
            return original_line
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to process line: {e}")
            return line
    
    def _is_likely_form_field(self, label: str, answer: str) -> bool:
        """Determine if a label-answer pair is likely a form field"""
        try:
            # Check if label contains common field keywords
            label_lower = label.lower()
            if any(keyword in label_lower for keyword in self.common_field_labels):
                return True
            
            # Check label patterns
            if re.match(r'^[A-Za-z\s]{2,30}$', label):  # Reasonable label length
                # Check if answer looks like filled data (not just text)
                if answer and len(answer) < 100:  # Reasonable answer length
                    return True
            
            # Check for specific patterns
            if any(pattern in label_lower for pattern in ['number', 'name', 'date', 'model', 'type']):
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to check if form field: {e}")
            return False
    
    def _create_blank_field(self, label: str, answer: str, original_line: str) -> str:
        """Create a blank field from a label-answer pair"""
        try:
            # Determine the separator used
            separator = ":"
            if "=" in original_line:
                separator = "="
            elif "-" in original_line:
                separator = "-"
            elif ">" in original_line:
                separator = ">"
            
            # Create appropriate blank based on answer length and type
            if len(answer) <= 20:
                blank = "_" * max(len(answer), 10)
            elif len(answer) <= 50:
                blank = "_" * 20
            else:
                blank = "_" * 30 + "\n" + "_" * 30
            
            # Check if answer looks like a specific type
            if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', answer):  # Date
                blank = "___/___/_______"
            elif re.match(r'^\d+$', answer):  # Number
                blank = "_" * max(len(answer), 5)
            elif '@' in answer:  # Email
                blank = "_" * 20 + "@" + "_" * 10
            
            return f"{label}{separator} {blank}"
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to create blank field: {e}")
            return original_line
    
    def _process_table_line(self, line: str) -> str:
        """Process table-like line with | separators"""
        try:
            parts = line.split('|')
            blank_parts = []
            
            for i, part in enumerate(parts):
                part = part.strip()
                if i == 0:  # First column is usually the label
                    blank_parts.append(part)
                else:  # Other columns might contain answers to blank out
                    if part and len(part) < 50 and not any(keyword in part.lower() for keyword in ['description', 'instruction', 'note']):
                        # This looks like data, replace with blank
                        blank_parts.append("_" * max(len(part), 10))
                    else:
                        blank_parts.append(part)
            
            return " | ".join(blank_parts)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to process table line: {e}")
            return line
    
    def _process_underline_field(self, line: str) -> str:
        """Process lines with underline fields (_______)"""
        try:
            # Find sequences of underscores that might be filled
            pattern = r'_{3,}'
            
            # If there's text after underscores, it might be a filled field
            if re.search(r'_{3,}\s*\w+', line):
                # Replace the pattern with just underscores
                return re.sub(r'_{3,}\s*\w+.*$', lambda m: '_' * 15, line)
            
            return line
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to process underline field: {e}")
            return line
    
    def _post_process_template(self, template_text: str) -> str:
        """Post-process the template to clean it up and enhance it"""
        try:
            # Remove excessive blank lines
            template_text = re.sub(r'\n{3,}', '\n\n', template_text)
            
            # Add instructions at the top
            header = """BLANK TEMPLATE
This template was automatically generated from a filled document.
Please fill in the blank fields marked with underscores (_____).

"""
            
            template_text = header + template_text
            
            # Add footer instructions
            footer = """

Instructions:
- Fill in all fields marked with underscores
- Replace _____ with appropriate information
- Ensure all required fields are completed
"""
            
            template_text = template_text + footer
            
            return template_text.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to post-process template: {e}")
            return template_text
    
    async def _create_word_document_from_text(
        self, 
        template_text: str, 
        original_filename: str, 
        device_id: str
    ) -> str:
        """Create a Word document from the blank template text"""
        try:
            # Create new document
            doc = Document()
            
            # Add title
            title = doc.add_heading('Blank Template', 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add subtitle with original filename
            subtitle = doc.add_paragraph(f'Generated from: {original_filename}')
            subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
            
            # Add a separator
            doc.add_paragraph('=' * 60)
            
            # Add the template content
            lines = template_text.split('\n')
            current_paragraph = None
            
            for line in lines:
                if not line.strip():
                    if current_paragraph:
                        current_paragraph = None
                    doc.add_paragraph()
                elif line.strip().startswith('BLANK TEMPLATE') or line.strip().startswith('Instructions:'):
                    # Add as heading
                    doc.add_heading(line.strip(), level=2)
                    current_paragraph = None
                else:
                    # Add as regular paragraph
                    current_paragraph = doc.add_paragraph(line)
            
            # Save document
            filename_base = Path(original_filename).stem
            output_filename = f"blank_template_{filename_base}_{uuid.uuid4().hex[:8]}.docx"
            output_path = self.output_dir / output_filename
            
            doc.save(str(output_path))
            
            logger.info(f"✅ Created Word document: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"❌ Failed to create Word document: {e}")
            raise
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported input formats"""
        return ['.pdf', '.docx', '.doc']
    
    def get_output_format(self) -> str:
        """Get the output format"""
        return '.docx'

# Global instance
document_reverse_processor = DocumentReverseProcessor()
