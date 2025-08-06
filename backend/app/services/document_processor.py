import os
import uuid
import json
import aiofiles
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging
from docx import Document
import PyPDF2
import re
import unicodedata
from io import BytesIO
from dotenv import load_dotenv

# Optional imports for enhanced PDF processing
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available - using alternative PDF processors")

try:
    from pdfminer.high_level import extract_text as pdfminer_extract_text
    from pdfminer.layout import LAParams
    PDFMINER_AVAILABLE = True
except ImportError:
    PDFMINER_AVAILABLE = False

# Load environment variables
load_dotenv()

from app.services.gemini_service import gemini_service
from app.services.pinecone_service import pinecone_service
from app.database import document_repo

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads"))
        self.upload_dir.mkdir(exist_ok=True)
        # ENHANCED: Optimized chunk sizes for better information capture
        self.chunk_size = 1500  # Increased for more context
        self.chunk_overlap = 400  # Increased overlap for better continuity
        self.min_chunk_size = 300  # Minimum viable chunk size
    
    async def process_uploaded_file(
        self, 
        file_content: bytes, 
        filename: str, 
        device_id: str
    ) -> Dict[str, Any]:
        """Process uploaded file and store in vector database"""
        try:
            logger.info(f"🚀 Starting to process document: {filename} for device: {device_id}")
            
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Extract text from file
            text_content = await self._extract_text(file_content, filename)
            if not text_content:
                raise ValueError("Could not extract text from file")
            
            # Create chunks
            chunks = self._create_chunks(text_content)
            if not chunks:
                raise ValueError("No chunks were created from the document")
            
            logger.info(f"📦 Created {len(chunks)} chunks from document")
            
            # Generate embeddings and store in Pinecone
            await self._store_chunks_in_pinecone(chunks, document_id, device_id, filename)
            
            # Store metadata in MongoDB
            document_metadata = {
                "document_id": document_id,
                "filename": filename,
                "file_size": len(file_content),
                "file_type": Path(filename).suffix.lower(),
                "device_id": device_id,
                "chunk_count": len(chunks),
                "processed": True
            }
            
            await document_repo.create_document(document_metadata)
            
            # Save file to disk (optional, for backup)
            file_path = self.upload_dir / f"{document_id}_{filename}"
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
            
            logger.info(f"✅ Successfully processed document {filename} for device {device_id} - Created {len(chunks)} chunks")
            
            return {
                "document_id": document_id,
                "filename": filename,
                "device_id": device_id,
                "chunks_created": len(chunks),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process document {filename}: {e}")
            raise
    
    async def _extract_text(self, file_content: bytes, filename: str) -> str:
        """Extract text from different file types"""
        try:
            file_extension = Path(filename).suffix.lower()
            logger.info(f"📄 Extracting text from {filename} (type: {file_extension})")
            
            extracted_text = ""
            
            if file_extension == '.txt':
                extracted_text = file_content.decode('utf-8')
            
            elif file_extension == '.pdf':
                extracted_text = self._extract_text_from_pdf(file_content)
            
            elif file_extension == '.docx':
                extracted_text = self._extract_text_from_docx(file_content)
            
            elif file_extension == '.md':
                extracted_text = file_content.decode('utf-8')
            
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
            
            # Clean up the extracted text
            cleaned_text = extracted_text.strip()
            if not cleaned_text:
                raise ValueError(f"No text content found in file {filename}")
            
            logger.info(f"✅ Extracted {len(cleaned_text)} characters from {filename}")
            return cleaned_text
                
        except Exception as e:
            logger.error(f"❌ Failed to extract text from {filename}: {e}")
            raise
    
    def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Enhanced PDF text extraction using multiple methods for better accuracy"""
        try:
            logger.info("🔍 Starting enhanced PDF text extraction...")
            pdf_file = BytesIO(file_content)
            
            # Method 1: Try pdfplumber (best for layout preservation)
            text_plumber = self._extract_with_pdfplumber(pdf_file)
            if text_plumber and len(text_plumber.strip()) > 100:
                logger.info("✅ Successfully extracted text using pdfplumber")
                return self._clean_extracted_text(text_plumber)
            
            # Method 2: Try PyMuPDF (good for most PDFs)
            pdf_file.seek(0)
            text_pymupdf = self._extract_with_pymupdf(pdf_file)
            if text_pymupdf and len(text_pymupdf.strip()) > 100:
                logger.info("✅ Successfully extracted text using PyMuPDF")
                return self._clean_extracted_text(text_pymupdf)
            
            # Method 3: Try pdfminer (good for complex layouts)
            pdf_file.seek(0)
            text_pdfminer = self._extract_with_pdfminer(pdf_file)
            if text_pdfminer and len(text_pdfminer.strip()) > 100:
                logger.info("✅ Successfully extracted text using pdfminer")
                return self._clean_extracted_text(text_pdfminer)
            
            # Method 4: Fallback to PyPDF2 (basic extraction)
            pdf_file.seek(0)
            text_pypdf2 = self._extract_with_pypdf2(pdf_file)
            if text_pypdf2 and len(text_pypdf2.strip()) > 50:
                logger.info("⚠️ Using PyPDF2 as fallback")
                return self._clean_extracted_text(text_pypdf2)
            
            # If all methods fail but we got some text, use the best available
            all_texts = [text_plumber, text_pymupdf, text_pdfminer, text_pypdf2]
            best_text = max((text for text in all_texts if text), key=len, default="")
            
            if best_text and len(best_text.strip()) > 20:
                logger.warning("⚠️ Using partial text extraction result")
                return self._clean_extracted_text(best_text)
            
            raise ValueError("No readable text could be extracted from PDF using any method")
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from PDF: {e}")
            raise
    
    def _extract_with_pdfplumber(self, pdf_file: BytesIO) -> str:
        """Extract text using pdfplumber (best for layout preservation)"""
        try:
            if not PDFPLUMBER_AVAILABLE:
                logger.warning("⚠️ pdfplumber not available, skipping this extraction method")
                return ""
                
            text_parts = []
            
            with pdfplumber.open(pdf_file) as pdf:
                logger.info(f"📄 PDF has {len(pdf.pages)} pages")
                
                for page_num, page in enumerate(pdf.pages):
                    try:
                        # Extract text with layout preservation
                        page_text = page.extract_text(
                            x_tolerance=3,
                            y_tolerance=3,
                            layout=True,
                            x_density=7.25,
                            y_density=13
                        )
                        
                        if page_text and page_text.strip():
                            # Validate text quality before processing
                            if self._is_text_quality_good(page_text):
                                # Clean up spacing and formatting
                                cleaned_text = re.sub(r'\n\s*\n', '\n\n', page_text)
                                cleaned_text = re.sub(r' +', ' ', cleaned_text)
                                text_parts.append(cleaned_text)
                                logger.debug(f"📄 Extracted {len(page_text)} chars from page {page_num + 1}")
                            else:
                                logger.warning(f"⚠️ Poor text quality detected on page {page_num + 1}, skipping")
                        
                        # Also try table extraction for structured data
                        tables = page.extract_tables()
                        for table in tables:
                            if table:
                                table_text = "\n".join([" | ".join([str(cell) if cell else "" for cell in row]) for row in table])
                                if table_text.strip():
                                    text_parts.append(f"\n[TABLE DATA]\n{table_text}\n[/TABLE DATA]\n")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to extract from page {page_num + 1} with pdfplumber: {e}")
                        continue
            
            if text_parts:
                full_text = "\n\n".join(text_parts)
                logger.info(f"✅ pdfplumber extracted {len(full_text)} characters from {len(text_parts)} pages")
                return full_text
            
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ pdfplumber extraction failed: {e}")
            return ""
    
    def _extract_with_pymupdf(self, pdf_file: BytesIO) -> str:
        """Extract text using PyMuPDF (good for most PDFs)"""
        try:
            if not PYMUPDF_AVAILABLE:
                logger.warning("⚠️ PyMuPDF not available, skipping this extraction method")
                return ""
                
            text_parts = []
            
            doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
            logger.info(f"📄 PDF has {len(doc)} pages")
            
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    
                    # Extract text with layout preservation
                    text_dict = page.get_text("dict")
                    page_text = self._process_pymupdf_blocks(text_dict)
                    
                    if page_text and page_text.strip():
                        text_parts.append(page_text)
                        logger.debug(f"📄 Extracted {len(page_text)} chars from page {page_num + 1}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract from page {page_num + 1} with PyMuPDF: {e}")
                    continue
            
            doc.close()
            
            if text_parts:
                full_text = "\n\n".join(text_parts)
                logger.info(f"✅ PyMuPDF extracted {len(full_text)} characters from {len(text_parts)} pages")
                return full_text
            
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ PyMuPDF extraction failed: {e}")
            return ""
    
    def _process_pymupdf_blocks(self, text_dict: dict) -> str:
        """Process PyMuPDF text blocks to preserve layout"""
        try:
            text_parts = []
            
            for block in text_dict.get("blocks", []):
                if "lines" in block:  # Text block
                    block_text = []
                    for line in block["lines"]:
                        line_text = []
                        for span in line.get("spans", []):
                            if "text" in span:
                                text = span["text"].strip()
                                if text:
                                    line_text.append(text)
                        if line_text:
                            block_text.append(" ".join(line_text))
                    
                    if block_text:
                        text_parts.append("\n".join(block_text))
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to process PyMuPDF blocks: {e}")
            return ""
    
    def _extract_with_pdfminer(self, pdf_file: BytesIO) -> str:
        """Extract text using pdfminer (good for complex layouts)"""
        try:
            if not PDFMINER_AVAILABLE:
                logger.warning("⚠️ pdfminer not available, skipping this extraction method")
                return ""
            
            # Configure layout analysis parameters
            laparams = LAParams(
                char_margin=2.0,
                line_margin=0.5,
                word_margin=0.1,
                boxes_flow=0.5,
                detect_vertical=True,
                all_texts=False
            )
            
            text = pdfminer_extract_text(
                pdf_file,
                laparams=laparams
            )
            
            if text and text.strip():
                logger.info(f"✅ pdfminer extracted {len(text)} characters")
                return text
            
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ pdfminer extraction failed: {e}")
            return ""
    
    def _extract_with_pypdf2(self, pdf_file: BytesIO) -> str:
        """Extract text using PyPDF2 (basic fallback)"""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if len(pdf_reader.pages) == 0:
                return ""
            
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_parts.append(page_text)
                        logger.debug(f"📄 PyPDF2 extracted text from page {page_num + 1}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to extract from page {page_num + 1} with PyPDF2: {e}")
                    continue
            
            if text_parts:
                full_text = "\n\n".join(text_parts)
                logger.info(f"✅ PyPDF2 extracted {len(full_text)} characters from {len(text_parts)} pages")
                return full_text
            
            return ""
            
        except Exception as e:
            logger.warning(f"⚠️ PyPDF2 extraction failed: {e}")
            return ""
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        try:
            if not text:
                return ""
            
            # Normalize unicode characters
            text = unicodedata.normalize('NFKD', text)
            
            # Remove or replace problematic characters
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', ' ', text)
            
            # Enhanced fix for common OCR errors and encoding issues
            replacements = {
                # Smart quotes and dashes - MORE COMPREHENSIVE
                'â€™': "'", 'â€˜': "'", ''': "'", ''': "'",
                'â€œ': '"', 'â€\x9d': '"', '"': '"', '"': '"',
                'â€"': '—', 'â€"': '–', '–': '-', '—': '-',
                'â€¦': '...', '…': '...',
                
                # Non-breaking spaces and similar issues - EXPANDED
                'Â ': ' ', 'Â': ' ', '\xa0': ' ', '\u00a0': ' ',
                '\u2000': ' ', '\u2001': ' ', '\u2002': ' ', '\u2003': ' ',
                '\u2004': ' ', '\u2005': ' ', '\u2006': ' ', '\u2007': ' ',
                '\u2008': ' ', '\u2009': ' ', '\u200a': ' ', '\u200b': '',
                
                # Common bullet points and symbols
                'â€¢': '•', 'â—': '•', '•': '•',
                'â–ª': '▪', 'â–«': '▫', '▪': '▪', '▫': '▫',
                'â€º': '›', 'â€¹': '‹', '›': '>', '‹': '<',
                
                # Currency and special symbols
                'â‚¬': '€', 'Â£': '£', 'Â¥': '¥',
                'Â®': '®', 'Â©': '©', 'â„¢': '™',
                '®': '®', '©': '©', '™': 'TM',
                
                # Accented characters (common encoding issues) - EXPANDED
                'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
                'Ã ': 'à', 'Ã¨': 'è', 'Ã¬': 'ì', 'Ã²': 'ò', 'Ã¹': 'ù',
                'Ã¢': 'â', 'Ãª': 'ê', 'Ã®': 'î', 'Ã´': 'ô', 'Ã»': 'û',
                'Ã¤': 'ä', 'Ã«': 'ë', 'Ã¯': 'ï', 'Ã¶': 'ö', 'Ã¼': 'ü',
                'Ã±': 'ñ', 'Ã§': 'ç', 'Ã¿': 'ÿ',
                
                # Additional problematic sequences - MUCH MORE COMPREHENSIVE
                'ï¿½': '',    # Replacement character (usually garbled)
                'â–': '-',    # Various dash issues
                'â€': '',     # Common prefix for encoding issues
                'â€ ': ' ',   # Another variant
                'â€\x9c': '"', 'â€\x9d': '"',  # More quote variants
                'â€\x98': "'", 'â€\x99': "'",  # More quote variants
                'â€\x93': '-', 'â€\x94': '-',  # More dash variants
                'â€\xa6': '...', # Ellipsis variant
                
                # Remove complex garbled sequences
                'â€™s': "'s",  # Possessive apostrophe
                'â€œthe': '"the',  # Quote before word
                'â€\x9cthe': '"the',  # Another quote variant
                
                # Table and form artifacts
                '|': ' | ',  # Keep table separators readable
                
                # Remove obviously corrupted sequences
                'â€š': ',', 'â€ž': '"', 'â€°': '%',
                'âˆ': '', 'â•': '', 'â–': '',
                'â—': '', 'â˜': '', 'â™': '',
                'âš': '', 'â›': '', 'âœ': '',
                'â': '', 'âž': '', 'âŸ': '',
            }
            
            # Apply all replacements
            for old, new in replacements.items():
                text = text.replace(old, new)
            
            # Additional aggressive cleaning for remaining artifacts
            # Remove any remaining â€ sequences that weren't caught above
            text = re.sub(r'â€[^\w\s]', '', text)  # Remove â€ followed by special chars
            text = re.sub(r'â€\w{1,2}', '', text)  # Remove â€ followed by 1-2 chars
            
            # Remove sequences that are likely encoding artifacts
            # More aggressive removal of garbled sequences
            text = re.sub(r'[^\w\s.,;:!?()&@#$%^*+=|\\/<>[\]{}"\'`~-]{3,}', ' ', text)
            
            # Remove isolated special characters that might be artifacts
            text = re.sub(r'\b[^\w\s.,;:!?()-]\b', ' ', text)
            
            # Clean up multiple encoding artifacts in sequence
            text = re.sub(r'(â€|Â|ï¿½|â–|â‚¬|â„¢|Ã){2,}', ' ', text)
            
            # Remove excessive whitespace while preserving paragraph breaks
            text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
            text = re.sub(r'\n[ \t]+', '\n', text)  # Remove leading whitespace on lines
            text = re.sub(r'[ \t]+\n', '\n', text)  # Remove trailing whitespace on lines
            text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double newline
            
            # Remove page numbers and headers/footers that might interfere
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                
                # Skip likely page numbers (standalone numbers)
                if re.match(r'^\d+$', line) and len(line) <= 3:
                    continue
                
                # Skip lines that are just page markers
                if re.match(r'^(page|página)\s*\d+', line.lower()):
                    continue
                
                # Skip very short lines that might be artifacts (but keep field labels with colons)
                if len(line) < 3 and ':' not in line:
                    continue
                
                cleaned_lines.append(line)
            
            # Rejoin and do final cleanup
            text = '\n'.join(cleaned_lines)
            text = text.strip()
            
            # Log cleaning results
            logger.debug(f"🧹 Text cleaning: {len(text)} characters after cleanup")
            
            return text
            
        except Exception as e:
            logger.warning(f"⚠️ Text cleaning failed: {e}")
            return text  # Return original text if cleaning fails
    
    def _is_text_quality_good(self, text: str) -> bool:
        """Check if extracted text has good quality (not corrupted/garbled)"""
        try:
            if not text or len(text.strip()) < 5:
                return False
            
            # Special handling for table data - be more lenient
            is_table_data = '[TABLE DATA]' in text or '|' in text or text.count(' | ') > 3
            
            # Check for reasonable ASCII character ratio (less strict for tables)
            printable_chars = sum(1 for c in text if c.isprintable() and ord(c) < 256)
            ascii_ratio = printable_chars / len(text)
            min_ascii_ratio = 0.6 if is_table_data else 0.7  # More lenient for tables
            if ascii_ratio < min_ascii_ratio:
                logger.debug(f"❌ Text quality poor: ASCII ratio {ascii_ratio:.2f} < {min_ascii_ratio}")
                return False
            
            # Check for excessive encoding artifacts (less strict for tables)
            artifact_patterns = [
                'â€', 'â€™', 'â€œ', 'â€\x9d', 'Â', 'ï¿½', 'â–', 'â‚¬',
                'â€˜', 'â€"', 'â€"', 'â€¦', 'â€¢', 'â—', 'â–ª', 'â–«',
                'â€º', 'â€¹', 'Â®', 'Â©', 'â„¢', 'Ã¡', 'Ã©', 'Ã­',
                'Ã³', 'Ãº', 'Ã ', 'Ã¨', 'Ã¬', 'Ã²', 'Ã¹', 'Ã¢',
                'Ãª', 'Ã®', 'Ã´', 'Ã»', 'Ã¤', 'Ã«', 'Ã¯', 'Ã¶',
                'Ã¼', 'Ã±', 'Ã§', 'Ã¿', 'âˆ', 'â•', 'â–', 'â—',
                'â˜', 'â™', 'âš', 'â›', 'âœ', 'â', 'âž', 'âŸ'
            ]
            artifact_count = sum(text.count(pattern) for pattern in artifact_patterns)
            max_artifacts = len(text) / 50 if is_table_data else len(text) / 100  # More lenient for tables
            if artifact_count > max_artifacts:
                logger.debug(f"❌ Text quality poor: {artifact_count} artifacts in {len(text)} chars (max: {max_artifacts:.0f})")
                return False
            
            # Check for reasonable word structure (more lenient)
            words = text.split()
            if len(words) < 2:  # Reduced from 3
                return False
            
            # Skip detailed checks for table data
            if is_table_data:
                logger.debug(f"✅ Table data accepted: {len(text)} chars, {len(words)} words")
                return True
            
            # Check average word length (should be reasonable)
            avg_word_length = sum(len(word.strip('.,;:!?()|')) for word in words) / len(words)
            if avg_word_length < 2.0 or avg_word_length > 15:  # More lenient range
                logger.debug(f"❌ Text quality poor: avg word length {avg_word_length}")
                return False
            
            # Check for too many very short words (likely artifacts) - more lenient
            short_words = sum(1 for word in words if len(word.strip('.,;:!?()|')) <= 1)
            if short_words / len(words) > 0.6:  # Increased threshold
                logger.debug(f"❌ Text quality poor: {short_words}/{len(words)} words are too short")
                return False
            
            # Check for reasonable character distribution - more lenient
            alpha_chars = sum(1 for c in text if c.isalpha())
            if alpha_chars / len(text) < 0.25:  # Reduced from 0.4 - allow more numbers/symbols
                logger.debug(f"❌ Text quality poor: only {alpha_chars/len(text)*100:.1f}% alphabetic")
                return False
            
            # Check for excessive repetitive patterns - more lenient
            repetitive_pattern_count = len(re.findall(r'(.)\1{5,}', text))  # 6+ same chars (was 4+)
            if repetitive_pattern_count > len(text) / 100:  # Increased threshold
                logger.debug(f"❌ Text quality poor: {repetitive_pattern_count} repetitive patterns")
                return False
            
            logger.debug(f"✅ Text quality good: {len(text)} chars, {len(words)} words, {artifact_count} artifacts")
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to check text quality: {e}")
            return True  # Default to good quality on error
    
    def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX file"""
        try:
            docx_file = BytesIO(file_content)
            doc = Document(docx_file)
            
            text_parts = []
            
            # Extract text from paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_parts.append(cell.text)
            
            if not text_parts:
                raise ValueError("No text content found in DOCX file")
            
            full_text = "\n".join(text_parts)
            logger.info(f"✅ Extracted text from DOCX with {len(doc.paragraphs)} paragraphs and {len(doc.tables)} tables")
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"❌ Failed to extract text from DOCX: {e}")
            raise
    
    def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Create optimized overlapping chunks from text with better boundary detection and enhanced coverage"""
        try:
            if not text or len(text.strip()) == 0:
                logger.warning("⚠️ Empty or whitespace-only text provided for chunking")
                return []
            
            # Clean and prepare text for chunking
            cleaned_text = self._prepare_text_for_chunking(text)
            
            chunks = []
            start = 0
            chunk_id = 0
            text_length = len(cleaned_text)
            
            logger.info(f"📊 Creating chunks from text of length {text_length} characters")
            logger.info(f"🔧 Chunk size: {self.chunk_size}, overlap: {self.chunk_overlap}")
            
            # ENHANCED: Create comprehensive chunks with improved coverage
            while start < text_length:
                end = min(start + self.chunk_size, text_length)
                
                # Find the best boundary for splitting
                chunk_text, actual_end = self._find_optimal_chunk_boundary(
                    cleaned_text, start, end, text_length
                )
                
                # Only add meaningful chunks
                chunk_content = chunk_text.strip()
                if self._is_valid_chunk(chunk_content):
                    # Enhance chunk with metadata
                    chunk_metadata = self._extract_chunk_metadata(chunk_content)
                    
                    # ENHANCED: Better context preservation and keyword extraction
                    enhanced_metadata = self._enhance_chunk_metadata(chunk_content, chunk_id, start, actual_end)
                    chunk_metadata.update(enhanced_metadata)
                    
                    chunks.append({
                        "chunk_id": chunk_id,
                        "content": chunk_content,
                        "start_index": start,
                        "end_index": actual_end,
                        "word_count": len(chunk_content.split()),
                        "has_structured_data": chunk_metadata["has_structured_data"],
                        "contains_fields": chunk_metadata["contains_fields"],
                        "content_type": chunk_metadata["content_type"],
                        "importance_score": chunk_metadata.get("importance_score", 0.5),
                        "semantic_keywords": chunk_metadata.get("semantic_keywords", []),
                        "entity_density": chunk_metadata.get("entity_density", 0.0),
                        "information_richness": chunk_metadata.get("information_richness", 0.0),
                        "chunk_quality_score": chunk_metadata.get("chunk_quality_score", 0.5),
                        "coverage_info": {
                            "chunk_position": f"{chunk_id}/{chunk_id}",  # Will be updated later
                            "document_coverage": f"{start}-{actual_end}",
                            "total_length": len(cleaned_text)
                        }
                    })
                    logger.debug(f"📦 Created chunk {chunk_id}: {len(chunk_content)} chars, type: {chunk_metadata['content_type']}, importance: {chunk_metadata.get('importance_score', 0.5):.2f}")
                    chunk_id += 1
                elif chunk_content:
                    logger.debug(f"⏭️ Skipped invalid chunk ({len(chunk_content)} chars): {chunk_content[:50]}...")
                
                # Calculate next start position with smart overlap
                next_start = self._calculate_next_start(
                    start, actual_end, cleaned_text, self.chunk_overlap
                )
                
                # Prevent infinite loop
                if next_start <= start:
                    start += 1
                else:
                    start = next_start
                
                if start >= text_length:
                    break
            
            # ENHANCED: Post-process chunks for better coverage
            enhanced_chunks = self._post_process_chunks(chunks, cleaned_text)
            
            logger.info(f"✅ Created {len(enhanced_chunks)} enhanced chunks from document")
            
            if len(enhanced_chunks) == 0:
                logger.error(f"❌ ZERO CHUNKS CREATED! Text length: {text_length}")
                logger.error(f"❌ First 500 chars of text: {cleaned_text[:500]}")
                logger.error(f"❌ Text is all whitespace: {cleaned_text.isspace()}")
                logger.error(f"❌ Text stripped length: {len(cleaned_text.strip())}")
            
            return enhanced_chunks
            
        except Exception as e:
            logger.error(f"❌ Failed to create chunks: {e}")
            raise
    
    def _prepare_text_for_chunking(self, text: str) -> str:
        """Prepare text for optimal chunking"""
        try:
            # Normalize line breaks
            text = re.sub(r'\r\n', '\n', text)
            text = re.sub(r'\r', '\n', text)
            
            # Preserve important formatting markers
            text = re.sub(r'\n\n+', '\n\n', text)  # Multiple newlines to double
            
            # Mark important sections for better chunking
            # Mark field labels (important for form processing)
            text = re.sub(r'^([A-Za-z][A-Za-z\s]*:)\s*$', r'\1 [FIELD_LABEL]', text, flags=re.MULTILINE)
            
            # Mark structured data patterns
            text = re.sub(r'(\[TABLE DATA\].*?\[/TABLE DATA\])', r'\1 [STRUCTURED_CONTENT]', text, flags=re.DOTALL)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to prepare text for chunking: {e}")
            return text
    
    def _find_optimal_chunk_boundary(self, text: str, start: int, end: int, text_length: int) -> tuple:
        """Find the optimal boundary for chunk splitting"""
        try:
            if end >= text_length:
                return text[start:end], end
            
            chunk_text = text[start:end]
            
            # Look for natural boundaries in order of preference
            boundaries = [
                (r'\n\n', 2),  # Paragraph breaks (highest priority)
                (r'\.\s+[A-Z]', 2),  # Sentence endings followed by capital letters
                (r'\.\n', 2),  # Sentence endings at line breaks
                (r'\n', 1),  # Line breaks
                (r'\.\s', 2),  # Sentence endings
                (r';\s', 2),  # Semicolons
                (r',\s', 2),  # Commas
                (r'\s', 1),  # Any whitespace
            ]
            
            # Find the best boundary within the last 25% of the chunk
            search_start = max(start + int(self.chunk_size * 0.75), start + self.chunk_size // 2)
            search_text = text[search_start:end]
            
            for pattern, offset in boundaries:
                matches = list(re.finditer(pattern, search_text))
                if matches:
                    # Use the last match (closest to end)
                    last_match = matches[-1]
                    boundary_pos = search_start + last_match.start() + offset
                    return text[start:boundary_pos], boundary_pos
            
            # No good boundary found, use original end
            return chunk_text, end
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to find optimal boundary: {e}")
            return text[start:end], end
    
    def _is_valid_chunk(self, chunk_content: str) -> bool:
        """Determine if a chunk is valid and worth storing"""
        try:
            if not chunk_content or len(chunk_content.strip()) < 10:  # Reduced from 20
                return False
            
            # Check for special content types that should be preserved
            is_table_data = '[TABLE DATA]' in chunk_content or chunk_content.count('|') > 3
            is_structured_content = '[STRUCTURED_CONTENT]' in chunk_content
            has_field_markers = ':' in chunk_content and any(field in chunk_content.lower() for field in ['name', 'number', 'date', 'model', 'manufacturer', 'format', 'effective'])
            
            # Be very lenient with table data and structured content
            if is_table_data or is_structured_content or has_field_markers:
                logger.debug(f"✅ Accepting structured content: table={is_table_data}, structured={is_structured_content}, fields={has_field_markers}")
                return True
            
            # Check for minimum word count - more lenient
            words = chunk_content.split()
            if len(words) < 3:  # Reduced from 5
                return False
            
            # Avoid chunks that are mostly special characters or numbers - more lenient
            alphanumeric_ratio = sum(c.isalnum() for c in chunk_content) / len(chunk_content)
            if alphanumeric_ratio < 0.3:  # Reduced from 0.5
                return False
            
            # Check for reasonable character distribution (avoid garbled text) - more lenient
            ascii_ratio = sum(1 for c in chunk_content if ord(c) < 128) / len(chunk_content)
            if ascii_ratio < 0.7:  # Reduced from 0.8
                return False
            
            # Avoid chunks with too many special encoding characters - more lenient
            encoding_artifacts = ['â€', 'Â', 'ï¿½', 'â–', 'â€œ', 'â€\x9d']
            artifact_count = sum(chunk_content.count(artifact) for artifact in encoding_artifacts)
            if artifact_count > 5:  # Increased from 3
                return False
            
            # Check for reasonable word length distribution - more lenient
            if words:
                avg_word_length = sum(len(word) for word in words) / len(words)
                if avg_word_length < 1.5 or avg_word_length > 20:  # More lenient range
                    return False
                
                # Check for too many very short or very long words - more lenient
                short_words = sum(1 for word in words if len(word) <= 2)
                long_words = sum(1 for word in words if len(word) > 25)
                if short_words / len(words) > 0.8 or long_words / len(words) > 0.15:  # More lenient
                    return False
            
            # Avoid chunks that are just repeated characters - more lenient
            unique_chars = len(set(chunk_content.lower().replace(' ', '').replace('\n', '')))
            if unique_chars < 5:  # Reduced from 10
                return False
            
            # Check for reasonable sentence structure - more lenient
            sentences = re.split(r'[.!?]+', chunk_content)
            if len(sentences) > 1:
                avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / max(1, len([s for s in sentences if s.strip()]))
                if avg_sentence_length < 2 or avg_sentence_length > 150:  # More lenient range
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to validate chunk: {e}")
            return True  # Default to valid on error
    
    def _extract_chunk_metadata(self, chunk_content: str) -> Dict[str, Any]:
        """Extract metadata about chunk content for better processing"""
        try:
            metadata = {
                "has_structured_data": False,
                "contains_fields": False,
                "content_type": "text"
            }
            
            # Check for structured data
            if any(marker in chunk_content for marker in ['[TABLE DATA]', '[STRUCTURED_CONTENT]']):
                metadata["has_structured_data"] = True
                metadata["content_type"] = "structured"
            
            # Check for form fields
            if re.search(r'.*:\s*[_\[\{]|.*:\s*$', chunk_content, re.MULTILINE):
                metadata["contains_fields"] = True
                if metadata["content_type"] == "text":
                    metadata["content_type"] = "form"
            
            # Check for lists or enumerations
            if re.search(r'^\s*[\d\w]\.\s', chunk_content, re.MULTILINE):
                if metadata["content_type"] == "text":
                    metadata["content_type"] = "list"
            
            return metadata
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract chunk metadata: {e}")
            return {"has_structured_data": False, "contains_fields": False, "content_type": "text"}
    
    def _calculate_next_start(self, current_start: int, current_end: int, text: str, overlap: int) -> int:
        """Calculate the next start position with smart overlap"""
        try:
            basic_next_start = max(current_end - overlap, current_start + 1)
            
            # Try to start at a natural boundary within the overlap region
            search_start = max(basic_next_start - 50, current_start + 1)
            search_end = min(basic_next_start + 50, len(text))
            search_text = text[search_start:search_end]
            
            # Look for paragraph or sentence boundaries
            boundaries = [r'\n\n', r'\.\s+[A-Z]', r'\n', r'\.\s']
            
            for pattern in boundaries:
                matches = list(re.finditer(pattern, search_text))
                if matches:
                    # Find the match closest to our basic start position
                    target_pos = basic_next_start - search_start
                    best_match = min(matches, key=lambda m: abs(m.start() - target_pos))
                    return search_start + best_match.end()
            
            return basic_next_start
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate smart overlap: {e}")
            return max(current_end - overlap, current_start + 1)
    
    async def _store_chunks_in_pinecone(
        self, 
        chunks: List[Dict[str, Any]], 
        document_id: str, 
        device_id: str, 
        filename: str
    ):
        """Generate embeddings and store chunks in Pinecone with enhanced metadata"""
        try:
            logger.info(f"🔗 Storing {len(chunks)} chunks in vector database for document {filename}")
            
            vectors = []
            
            for i, chunk in enumerate(chunks):
                try:
                    # Prepare text for embedding (clean version)
                    embedding_text = self._prepare_text_for_embedding(chunk["content"])
                    
                    # Generate embedding for cleaned chunk
                    embedding = await gemini_service.get_embedding(embedding_text)
                    
                    # Create enhanced metadata
                    metadata = {
                        "document_id": document_id,
                        "chunk_id": chunk["chunk_id"],
                        "content": chunk["content"][:2000],  # Increased storage for better context
                        "filename": filename,
                        "device_id": device_id,
                        "start_index": chunk["start_index"],
                        "end_index": chunk["end_index"],
                        "word_count": chunk.get("word_count", 0),
                        "content_type": chunk.get("content_type", "text"),
                        "has_structured_data": chunk.get("has_structured_data", False),
                        "contains_fields": chunk.get("contains_fields", False),
                        "text_length": len(chunk["content"]),
                        "extraction_quality": self._assess_extraction_quality(chunk["content"]),
                        # ENHANCED: More comprehensive metadata for better retrieval
                        "importance_score": chunk.get("importance_score", 0.5),
                        "entity_density": chunk.get("entity_density", 0.0),
                        "information_richness": chunk.get("information_richness", 0.0),
                        "semantic_keywords": ' '.join(chunk.get("semantic_keywords", [])),
                        "position_info": json.dumps(chunk.get("position_info", {})),
                        "coverage_info": json.dumps(chunk.get("coverage_info", {})),
                        # Add searchable keywords for better retrieval
                        "keywords": self._extract_keywords(chunk["content"]),
                        "has_numbers": bool(re.search(r'\d', chunk["content"])),
                        "has_dates": bool(re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', chunk["content"])),
                        "has_technical_terms": self._has_technical_terms(chunk["content"]),
                        "has_form_fields": bool(re.search(r'[A-Za-z\s]+:\s*(?:$|_|\.\.\.)', chunk["content"])),
                        "chunk_quality_score": self._calculate_chunk_quality_score(chunk["content"])
                    }
                    
                    # Create vector with enhanced metadata
                    vector = {
                        "id": f"{document_id}_{chunk['chunk_id']}",
                        "values": embedding,
                        "metadata": metadata
                    }
                    vectors.append(vector)
                    
                    if (i + 1) % 10 == 0:
                        logger.debug(f"📊 Processed {i + 1}/{len(chunks)} embeddings")
                        
                except Exception as e:
                    logger.error(f"❌ Failed to create embedding for chunk {i}: {e}")
                    # Continue with other chunks instead of failing completely
                    continue
            
            # Store in Pinecone
            if vectors:
                await pinecone_service.upsert_vectors(vectors, device_id)
                logger.info(f"✅ Successfully stored {len(vectors)} vectors in Pinecone for device {device_id}")
                
                # Log quality statistics
                avg_quality = sum(v["metadata"]["extraction_quality"] for v in vectors) / len(vectors)
                structured_count = sum(1 for v in vectors if v["metadata"]["has_structured_data"])
                field_count = sum(1 for v in vectors if v["metadata"]["contains_fields"])
                
                logger.info(f"📊 Quality stats - Avg: {avg_quality:.2f}, Structured: {structured_count}, Fields: {field_count}")
            else:
                raise ValueError("No vectors were created for storage")
            
        except Exception as e:
            logger.error(f"❌ Failed to store chunks in Pinecone: {e}")
            raise
    
    def _prepare_text_for_embedding(self, text: str) -> str:
        """Prepare text for embedding generation"""
        try:
            # Remove embedding markers we added for chunking
            text = re.sub(r'\s*\[FIELD_LABEL\]', '', text)
            text = re.sub(r'\s*\[STRUCTURED_CONTENT\]', '', text)
            
            # Clean up excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to prepare text for embedding: {e}")
            return text
    
    def _assess_extraction_quality(self, text: str) -> float:
        """Assess the quality of extracted text (0.0 to 1.0)"""
        try:
            if not text:
                return 0.0
            
            quality_score = 1.0
            
            # Check for encoding issues
            if any(char in text for char in ['â€™', 'â€œ', 'â€\x9d', 'Â ']):
                quality_score -= 0.2
            
            # Check for excessive special characters
            special_char_ratio = sum(1 for c in text if not c.isalnum() and c not in ' \n\t.,;:!?-()[]{}') / len(text)
            if special_char_ratio > 0.3:
                quality_score -= 0.3
            
            # Check for reasonable word distribution
            words = text.split()
            if words:
                avg_word_length = sum(len(word) for word in words) / len(words)
                if avg_word_length < 2 or avg_word_length > 15:
                    quality_score -= 0.2
            
            # Check for readable sentence structure
            sentences = re.split(r'[.!?]+', text)
            if sentences:
                avg_sentence_length = sum(len(sentence.split()) for sentence in sentences) / len(sentences)
                if avg_sentence_length < 3 or avg_sentence_length > 50:
                    quality_score -= 0.1
            
            return max(0.0, min(1.0, quality_score))
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to assess extraction quality: {e}")
            return 0.5  # Default to medium quality
    
    def _extract_keywords(self, text: str) -> str:
        """Extract important keywords from text for better searchability"""
        try:
            # Convert to lowercase for processing
            text_lower = text.lower()
            
            # Common important terms in medical/technical documents
            important_terms = {
                # Medical device terms
                'device', 'medical', 'equipment', 'instrument', 'apparatus',
                'monitor', 'sensor', 'probe', 'catheter', 'implant',
                'diagnosis', 'treatment', 'therapy', 'procedure',
                
                # Document terms
                'specification', 'manual', 'guide', 'instruction', 'protocol',
                'standard', 'requirement', 'compliance', 'validation',
                'certificate', 'approval', 'registration', 'license',
                
                # Technical terms
                'model', 'serial', 'version', 'revision', 'configuration',
                'parameter', 'setting', 'calibration', 'measurement',
                'accuracy', 'precision', 'range', 'limit', 'threshold',
                
                # Company/regulatory terms
                'manufacturer', 'supplier', 'vendor', 'distributor',
                'fda', 'ce', 'iso', 'iec', 'astm', 'ansi',
                'regulation', 'directive', 'standard', 'guideline'
            }
            
            # Find matching terms
            found_terms = []
            for term in important_terms:
                if term in text_lower:
                    found_terms.append(term)
            
            # Also extract potential model numbers, document numbers, etc.
            numbers = re.findall(r'\b[A-Z0-9]{2,}[-]?[A-Z0-9]*\b', text)
            found_terms.extend(numbers[:5])  # Limit to first 5 numbers
            
            return ' '.join(found_terms[:10])  # Limit to first 10 keywords
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract keywords: {e}")
            return ""
    
    def _has_technical_terms(self, text: str) -> bool:
        """Check if text contains technical terms"""
        try:
            text_lower = text.lower()
            technical_indicators = [
                # Medical terms
                'medical', 'clinical', 'diagnostic', 'therapeutic', 'surgical',
                'patient', 'physician', 'hospital', 'healthcare',
                
                # Technical terms
                'specification', 'parameter', 'calibration', 'measurement',
                'accuracy', 'precision', 'frequency', 'voltage', 'current',
                'temperature', 'pressure', 'humidity', 'sterilization',
                
                # Regulatory terms
                'compliance', 'validation', 'verification', 'regulation',
                'standard', 'requirement', 'guideline', 'protocol',
                
                # Document types
                'manual', 'guide', 'instruction', 'procedure', 'checklist'
            ]
            
            return any(term in text_lower for term in technical_indicators)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to check technical terms: {e}")
            return False
    
    def _enhance_chunk_metadata(self, chunk_content: str, chunk_id: int, start_index: int, end_index: int) -> Dict[str, Any]:
        """Enhanced metadata extraction for better retrieval"""
        try:
            metadata = {}
            
            # Calculate importance score based on content richness
            metadata["importance_score"] = self._calculate_importance_score(chunk_content)
            
            # Extract semantic keywords for better matching
            metadata["semantic_keywords"] = self._extract_semantic_keywords(chunk_content)
            
            # Calculate entity density (names, numbers, technical terms)
            metadata["entity_density"] = self._calculate_entity_density(chunk_content)
            
            # Calculate information richness
            metadata["information_richness"] = self._calculate_information_richness(chunk_content)
            
            # Calculate chunk quality score
            metadata["chunk_quality_score"] = self._calculate_chunk_quality_score(chunk_content)
            
            # Identify chunk position in document
            metadata["position_info"] = {
                "chunk_id": chunk_id,
                "relative_position": start_index / max(end_index, 1),
                "is_beginning": start_index < 1000,
                "is_middle": 1000 <= start_index <= end_index - 1000,
                "is_end": start_index > end_index - 1000
            }
            
            return metadata
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to enhance chunk metadata: {e}")
            return {}
    
    def _calculate_importance_score(self, text: str) -> float:
        """Calculate importance score based on content indicators"""
        try:
            score = 0.5  # Base score
            text_lower = text.lower()
            
            # High importance indicators
            high_importance_terms = [
                'device name', 'model number', 'serial number', 'manufacturer',
                'document number', 'version', 'date', 'specification',
                'requirements', 'standards', 'compliance', 'approval',
                'certification', 'generic name', 'intended use'
            ]
            
            for term in high_importance_terms:
                if term in text_lower:
                    score += 0.1
            
            # Form field indicators (very important for template filling)
            if ':' in text and any(field in text_lower for field in ['name', 'number', 'date', 'model', 'manufacturer']):
                score += 0.2
            
            # Technical data indicators
            if any(indicator in text for indicator in [':', ';', '(', ')', '[', ']', '{', '}']):
                score += 0.05
            
            # Presence of numbers (often important data)
            import re
            numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
            if numbers:
                score += min(len(numbers) * 0.02, 0.15)
            
            # Uppercase abbreviations (often important)
            abbreviations = re.findall(r'\b[A-Z]{2,}\b', text)
            if abbreviations:
                score += min(len(abbreviations) * 0.03, 0.1)
            
            return min(score, 1.0)  # Cap at 1.0
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate importance score: {e}")
            return 0.5
    
    def _extract_semantic_keywords(self, text: str) -> List[str]:
        """Extract semantic keywords for better retrieval"""
        try:
            import re
            
            keywords = set()
            text_lower = text.lower()
            
            # Domain-specific terms
            domain_terms = [
                # Device types
                'pulse oximeter', 'oximeter', 'monitor', 'sensor', 'probe',
                'catheter', 'implant', 'stent', 'pacemaker', 'defibrillator',
                
                # Medical terms
                'medical device', 'diagnostic', 'therapeutic', 'surgical',
                'clinical', 'patient', 'physician', 'hospital',
                
                # Document types
                'dmf', 'device master file', 'specification', 'manual',
                'guide', 'instruction', 'protocol', 'standard',
                
                # Regulatory terms
                'fda', 'ce mark', 'iso', 'iec', 'compliance', 'validation',
                'verification', 'approval', 'certification', 'registration',
                
                # Technical terms
                'model', 'version', 'serial', 'manufacturer', 'supplier',
                'accuracy', 'precision', 'calibration', 'measurement'
            ]
            
            for term in domain_terms:
                if term in text_lower:
                    keywords.add(term)
            
            # Extract numbers and codes (often important identifiers)
            numbers = re.findall(r'\b[A-Z0-9]{2,}[-/]?[A-Z0-9]*\b', text)
            keywords.update(numbers[:5])  # Limit to first 5
            
            # Extract capitalized terms (proper nouns, brands)
            capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
            keywords.update([term.lower() for term in capitalized[:5]])
            
            return list(keywords)[:10]  # Limit to 10 keywords
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to extract semantic keywords: {e}")
            return []
    
    def _calculate_entity_density(self, text: str) -> float:
        """Calculate density of named entities and important identifiers"""
        try:
            import re
            
            words = text.split()
            if not words:
                return 0.0
            
            entity_count = 0
            
            # Count capitalized words (potential proper nouns)
            entity_count += len(re.findall(r'\b[A-Z][a-z]+\b', text))
            
            # Count numbers
            entity_count += len(re.findall(r'\b\d+\b', text))
            
            # Count codes/identifiers
            entity_count += len(re.findall(r'\b[A-Z0-9]{2,}\b', text))
            
            # Count technical abbreviations
            entity_count += len(re.findall(r'\b[A-Z]{2,}\b', text))
            
            return min(entity_count / len(words), 1.0)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate entity density: {e}")
            return 0.0
    
    def _calculate_information_richness(self, text: str) -> float:
        """Calculate how information-rich the text is"""
        try:
            # Base richness on various factors
            richness = 0.0
            
            # Sentence structure diversity
            sentences = text.split('.')
            if len(sentences) > 1:
                avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
                if 5 <= avg_sentence_length <= 25:  # Good sentence length
                    richness += 0.2
            
            # Punctuation diversity (indicates structured content)
            unique_punct = set(c for c in text if c in '.,;:!?()[]{}')
            richness += min(len(unique_punct) * 0.05, 0.3)
            
            # Vocabulary diversity
            words = text.lower().split()
            if words:
                unique_words = len(set(words))
                vocabulary_ratio = unique_words / len(words)
                richness += min(vocabulary_ratio, 0.3)
            
            # Presence of structured data indicators
            if any(indicator in text for indicator in [':', '=', '->', '=>', '|']):
                richness += 0.2
            
            return min(richness, 1.0)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate information richness: {e}")
            return 0.5
    
    def _post_process_chunks(self, chunks: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
        """Post-process chunks to ensure comprehensive coverage"""
        try:
            if not chunks:
                return chunks
            
            # Sort chunks by importance score (highest first)
            chunks.sort(key=lambda x: x.get('importance_score', 0.5), reverse=True)
            
            # Ensure we have good coverage of important content
            enhanced_chunks = []
            
            for chunk in chunks:
                enhanced_chunks.append(chunk)
                
                # Add position context for better understanding
                chunk['coverage_info'] = {
                    'total_chunks': len(chunks),
                    'chunk_rank_by_importance': enhanced_chunks.index(chunk) + 1,
                    'contains_critical_info': chunk.get('importance_score', 0) > 0.7
                }
            
            # Log coverage statistics
            high_importance_count = sum(1 for chunk in enhanced_chunks if chunk.get('importance_score', 0) > 0.7)
            logger.info(f"📊 Chunk coverage: {high_importance_count}/{len(enhanced_chunks)} high-importance chunks")
            
            # Ensure minimum coverage of document
            if len(enhanced_chunks) < 3 and len(full_text) > 2000:
                logger.warning(f"⚠️ Low chunk count ({len(enhanced_chunks)}) for document size ({len(full_text)} chars)")
            
            return enhanced_chunks
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to post-process chunks: {e}")
            return chunks
    
    def _calculate_chunk_quality_score(self, content: str) -> float:
        """Calculate overall quality score for a chunk"""
        try:
            quality_score = 0.0
            
            # Text coherence (sentence structure)
            sentences = content.split('.')
            if len(sentences) > 1:
                avg_length = sum(len(s.split()) for s in sentences if s.strip()) / max(1, len([s for s in sentences if s.strip()]))
                if 5 <= avg_length <= 30:
                    quality_score += 0.3
            
            # Information density
            words = content.split()
            if words:
                # Good word length distribution
                avg_word_length = sum(len(word) for word in words) / len(words)
                if 3 <= avg_word_length <= 8:
                    quality_score += 0.2
                
                # Vocabulary richness
                unique_words = len(set(word.lower() for word in words))
                if unique_words / len(words) > 0.6:  # Good vocabulary diversity
                    quality_score += 0.2
            
            # Structured content indicators
            if any(indicator in content for indicator in [':', ';', '(', ')', '[', ']']):
                quality_score += 0.1
            
            # Technical content indicators
            if self._has_technical_terms(content):
                quality_score += 0.1
            
            # Form field indicators (important for template filling)
            if re.search(r'[A-Za-z\s]+:\s*(?:$|_|\.\.\.)', content):
                quality_score += 0.1
            
            return min(quality_score, 1.0)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate chunk quality score: {e}")
            return 0.5
    
    async def delete_document(self, document_id: str, device_id: str) -> bool:
        """Delete document and all its chunks"""
        try:
            # Get document metadata to verify it exists
            document = await document_repo.get_document_by_id(document_id)
            if not document:
                logger.warning(f"⚠️ Document {document_id} not found in database")
                # Continue with cleanup attempt anyway
            
            # Method 1: Delete all vectors for this document using metadata filtering (more reliable)
            logger.info(f"🗑️ Deleting all vectors for document {document_id} from device {device_id}")
            deletion_success = await pinecone_service.delete_document_vectors(document_id, device_id)
            
            # Method 2: Fallback - try to delete by chunk IDs if metadata filtering failed
            if not deletion_success and document and "chunk_count" in document:
                logger.info(f"🔄 Fallback: Attempting deletion by chunk IDs for document {document_id}")
                chunk_ids = [f"{document_id}_{i}" for i in range(document["chunk_count"])]
                deletion_success = await pinecone_service.delete_vectors(chunk_ids, device_id)
            
            # Delete from MongoDB
            await document_repo.delete_document(document_id)
            
            # Delete file from disk
            try:
                if document:
                    file_path = self.upload_dir / f"{document_id}_{document['filename']}"
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"🗑️ Deleted file from disk: {file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete file from disk: {e}")
            
            if deletion_success:
                logger.info(f"✅ Successfully deleted document {document_id} and all its chunks for device {device_id}")
            else:
                logger.warning(f"⚠️ Document {document_id} metadata deleted, but vector cleanup may have failed")
            
            return True  # Return True even if vector deletion failed, since metadata is cleaned up
            
        except Exception as e:
            logger.error(f"❌ Failed to delete document {document_id}: {e}")
            return False

# Global instance
document_processor = DocumentProcessor()
