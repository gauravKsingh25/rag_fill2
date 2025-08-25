"""
Google Vision OCR Service
Advanced OCR service using Google Cloud Vision API for superior text extraction
"""

import os
import io
import logging
import time
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from PIL import Image
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading
from dotenv import load_dotenv

# Google Cloud Vision imports
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

try:
    import fitz  # PyMuPDF for PDF processing
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

load_dotenv()
logger = logging.getLogger(__name__)

class GoogleVisionOCRService:
    """Google Vision OCR service for high-quality text extraction"""
    
    def __init__(self):
        self.client = None
        self.ocr_lock = threading.Lock()
        self.max_image_size = (2048, 2048)  # Google Vision recommended size
        self.timeout = 300  # 5-minute timeout per operation
        self.credentials_path = None
        
        # Initialize Google Vision client
        self._initialize_client()
        
        logger.info(f"🔍 Google Vision OCR Service initialized - Available: {self.is_available()}")
    
    def _initialize_client(self):
        """Initialize Google Vision client"""
        try:
            if not GOOGLE_VISION_AVAILABLE:
                logger.error("❌ Google Cloud Vision library not installed")
                return
            
            # Check for credentials
            creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "rag-fill-py-d1a683dcf003.json"
            if os.path.exists(creds_file):
                self.credentials_path = creds_file
                logger.info(f"✅ Found Google credentials: {creds_file}")
            else:
                logger.error(f"❌ Google credentials not found: {creds_file}")
                return
            
            # Initialize client
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials_path
            self.client = vision.ImageAnnotatorClient()
            
            logger.info("✅ Google Vision OCR client initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Vision client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Google Vision OCR service is available"""
        return GOOGLE_VISION_AVAILABLE and self.client is not None
    
    def should_process_with_ocr(self, filename: str) -> bool:
        """Check if file should be processed with OCR"""
        file_extension = Path(filename).suffix.lower()
        ocr_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp']
        return file_extension in ocr_extensions
    
    async def process_document(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process document and extract text using Google Vision OCR
        Returns (extracted_text, metadata)
        """
        try:
            start_time = time.time()
            
            if not self.is_available():
                logger.error("❌ Google Vision OCR service not available")
                return "", {
                    'error': 'google_vision_not_available',
                    'processing_time': 0
                }
            
            if not self.should_process_with_ocr(filename):
                return "", {
                    'ocr_required': False,
                    'reason': 'file_type_not_supported',
                    'processing_time': 0
                }
            
            file_extension = Path(filename).suffix.lower()
            
            # Process based on file type
            if file_extension == '.pdf':
                text, metadata = await self._process_pdf(file_content, filename)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp']:
                text, metadata = await self._process_image(file_content, filename)
            else:
                return "", {
                    'ocr_required': False,
                    'reason': 'unsupported_file_type',
                    'processing_time': 0
                }
            
            processing_time = time.time() - start_time
            metadata['total_processing_time'] = processing_time
            metadata['ocr_method'] = 'google_vision'
            metadata['ocr_required'] = True
            
            logger.info(f"✅ Google Vision OCR completed for {filename} - "
                       f"Text length: {len(text)}, "
                       f"Time: {processing_time:.2f}s")
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"❌ Google Vision OCR processing failed for {filename}: {e}")
            return "", {
                'ocr_required': True,
                'error': str(e),
                'processing_time': time.time() - start_time if 'start_time' in locals() else 0
            }
    
    async def _process_pdf(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Process PDF file - extract text first, then OCR if needed"""
        try:
            if not PYMUPDF_AVAILABLE:
                logger.warning("⚠️ PyMuPDF not available - treating PDF as image")
                return "", {'error': 'pymupdf_not_available'}
            
            # First try to extract text directly
            text_content = await self._extract_pdf_text_directly(file_content)
            
            if len(text_content.strip()) > 100:
                # PDF has readable text
                logger.info(f"📄 PDF has readable text ({len(text_content)} chars) - no OCR needed")
                return text_content, {
                    'method': 'direct_text_extraction',
                    'text_length': len(text_content),
                    'ocr_applied': False
                }
            
            # PDF appears to be scanned - apply Google Vision OCR
            logger.info("🔍 PDF appears to be scanned - applying Google Vision OCR")
            return await self._extract_pdf_with_google_vision(file_content, filename)
            
        except Exception as e:
            logger.error(f"❌ PDF processing failed: {e}")
            return "", {'error': str(e)}
    
    async def _extract_pdf_text_directly(self, file_content: bytes) -> str:
        """Extract text directly from PDF without OCR"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            text_parts = []
            
            for page_num in range(min(len(doc), 10)):  # Check first 10 pages
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)
            
            doc.close()
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.warning(f"⚠️ Direct PDF text extraction failed: {e}")
            return ""
    
    async def _extract_pdf_with_google_vision(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF using Google Vision OCR"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            total_pages = len(doc)
            
            logger.info(f"📄 Processing {total_pages} pages with Google Vision OCR")
            
            text_parts = []
            confidence_scores = []
            
            # Process pages with thread pool for better performance
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=3) as executor:  # Increased workers for Google Vision
                
                # Process in smaller batches to avoid rate limits
                batch_size = 5  # Smaller batches for Google Vision API
                logger.info(f"📦 Processing {total_pages} pages in batches of {batch_size}")
                
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    logger.info(f"🔄 Processing pages {batch_start + 1}-{batch_end} with Google Vision")
                    
                    batch_tasks = []
                    for page_num in range(batch_start, batch_end):
                        task = loop.run_in_executor(
                            executor, 
                            self._process_pdf_page_with_vision, 
                            doc, 
                            page_num
                        )
                        batch_tasks.append((page_num, task))
                    
                    # Process batch with timeout
                    try:
                        batch_timeout = 120  # 2 minutes per batch for Google Vision
                        logger.info(f"🔄 Processing batch {batch_start + 1}-{batch_end} with {batch_timeout}s timeout")
                        
                        batch_results = await asyncio.wait_for(
                            asyncio.gather(*[task for _, task in batch_tasks], return_exceptions=True),
                            timeout=batch_timeout
                        )
                        
                        # Process batch results
                        for i, result in enumerate(batch_results):
                            page_num = batch_start + i
                            if isinstance(result, Exception):
                                logger.warning(f"⚠️ Page {page_num + 1} failed: {result}")
                                continue
                            
                            if result and isinstance(result, tuple) and len(result) == 2:
                                page_text, confidence = result
                                if page_text and page_text.strip():
                                    text_parts.append(page_text)
                                    confidence_scores.append(confidence)
                                    logger.debug(f"✅ Page {page_num + 1}: {len(page_text)} characters, confidence: {confidence:.2f}")
                        
                        # Log batch progress
                        successful_pages = len([r for r in batch_results if isinstance(r, tuple)])
                        logger.info(f"✅ Completed batch {batch_start + 1}-{batch_end}: {successful_pages} pages successful")
                        
                        # Add small delay between batches to respect API limits
                        if batch_end < total_pages:
                            await asyncio.sleep(1)
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ Batch {batch_start + 1}-{batch_end} timed out after {batch_timeout}s")
                        continue
            
            doc.close()
            
            # Enhanced page combining that preserves table structure
            combined_text = self._combine_pages_preserving_structure(text_parts)
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            return combined_text, {
                'method': 'google_vision_pdf_ocr',
                'total_pages': total_pages,
                'processed_pages': len(text_parts),
                'text_length': len(combined_text),
                'average_confidence': avg_confidence,
                'ocr_applied': True,
                'api_used': 'google_cloud_vision'
            }
            
        except Exception as e:
            logger.error(f"❌ Google Vision PDF OCR extraction failed: {e}")
            return "", {'error': str(e)}
    
    def _process_pdf_page_with_vision(self, doc, page_num: int) -> Tuple[str, float]:
        """Process a single PDF page with Google Vision (runs in thread)"""
        try:
            page = doc.load_page(page_num)
            
            # Convert page to image
            mat = fitz.Matrix(2.0, 2.0)  # Higher resolution for better OCR
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            
            # Process with Google Vision
            text, confidence = self._apply_google_vision_sync(img_data)
            
            pix = None  # Free memory
            return text, confidence
            
        except Exception as e:
            logger.error(f"❌ Failed to process page {page_num + 1} with Google Vision: {e}")
            return "", 0.0
    
    async def _process_image(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Process image file with Google Vision OCR"""
        try:
            # Preprocess image if needed
            processed_image_data = self._preprocess_image_data(file_content)
            
            # Apply Google Vision OCR in thread pool
            loop = asyncio.get_event_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, self._apply_google_vision_sync, processed_image_data),
                timeout=60  # 1-minute timeout for individual image
            )
            
            if isinstance(result, tuple):
                text, confidence = result
            else:
                text, confidence = result, 0.0
            
            return text, {
                'method': 'google_vision_image_ocr',
                'text_length': len(text),
                'confidence': confidence,
                'ocr_applied': True,
                'api_used': 'google_cloud_vision'
            }
            
        except Exception as e:
            logger.error(f"❌ Google Vision image processing failed: {e}")
            return "", {'error': str(e)}
    
    def _preprocess_image_data(self, image_data: bytes) -> bytes:
        """Simple image preprocessing for better OCR"""
        try:
            # Load image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode not in ['RGB', 'L']:
                image = image.convert('RGB')
            
            # Resize if too large (Google Vision has size limits)
            if max(image.size) > max(self.max_image_size):
                image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
            
            # Convert back to bytes
            output = io.BytesIO()
            image.save(output, format='PNG', optimize=True)
            return output.getvalue()
            
        except Exception as e:
            logger.warning(f"⚠️ Image preprocessing failed: {e}")
            return image_data
    
    def _apply_google_vision_sync(self, image_data: bytes) -> Tuple[str, float]:
        """Apply Google Vision OCR synchronously (for thread pool)"""
        try:
            if not self.client:
                logger.error("❌ Google Vision client not initialized")
                raise Exception("Google Vision client not initialized. Check credentials and API enablement.")
            
            # Create vision image object
            image = vision.Image(content=image_data)
            
            # Perform text detection with enhanced features
            response = self.client.text_detection(
                image=image,
                image_context=vision.ImageContext(
                    language_hints=['en'],  # English language hint
                )
            )
            
            # Check for errors with detailed messages
            if response.error.message:
                error_msg = response.error.message
                logger.error(f"❌ Google Vision API error: {error_msg}")
                
                if "SERVICE_DISABLED" in error_msg:
                    raise Exception(f"Google Vision API is not enabled. Please enable it at: https://console.cloud.google.com/apis/library/vision.googleapis.com?project=rag-fill-py")
                elif "PERMISSION_DENIED" in error_msg:
                    raise Exception(f"Service account lacks permissions. Add 'Cloud Vision API Service Agent' role to rag-fill@rag-fill-py.iam.gserviceaccount.com")
                elif "BILLING_DISABLED" in error_msg:
                    raise Exception(f"Billing must be enabled for this project. Check: https://console.cloud.google.com/billing?project=rag-fill-py")
                else:
                    raise Exception(f"Google Vision API error: {error_msg}")
            
            # Extract text and confidence
            texts = response.text_annotations
            if not texts:
                logger.info("ℹ️ No text detected by Google Vision (blank or image-only page)")
                return "", 0.0
            
            # First annotation contains the full text
            full_text = texts[0].description
            
            # Calculate overall confidence from individual words
            word_confidences = []
            for text_annotation in texts[1:]:  # Skip the first (full text) annotation
                # Google Vision doesn't provide confidence directly for text_detection
                # We'll use a heuristic based on bounding box stability
                vertices = text_annotation.bounding_poly.vertices
                if len(vertices) == 4:
                    # Calculate bounding box area and regularity as confidence proxy
                    width = abs(vertices[1].x - vertices[0].x)
                    height = abs(vertices[2].y - vertices[0].y)
                    if width > 0 and height > 0:
                        # Normalized confidence based on text length and bounding box
                        confidence = min(1.0, len(text_annotation.description) / max(width/10, 1))
                        word_confidences.append(confidence)
            
            overall_confidence = sum(word_confidences) / len(word_confidences) if word_confidences else 0.8
            
            logger.debug(f"✅ Google Vision extracted {len(full_text)} characters with estimated confidence {overall_confidence:.2f}")
            
            return full_text.strip(), overall_confidence
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Google Vision OCR failed: {error_msg}")
            
            # Provide specific guidance based on error type
            if "403" in error_msg or "PERMISSION_DENIED" in error_msg:
                logger.error("🔧 FIX: Add 'Cloud Vision API Service Agent' role to your service account")
            elif "400" in error_msg or "invalid argument" in error_msg:
                logger.error("🔧 FIX: Check service account permissions and billing status")
            elif "SERVICE_DISABLED" in error_msg:
                logger.error("🔧 FIX: Enable Google Vision API and wait 5-10 minutes")
                
            raise Exception(f"Google Vision OCR failed: {error_msg}")
    
    def _combine_pages_preserving_structure(self, text_parts: List[str]) -> str:
        """Combine pages while preserving table and form structure"""
        try:
            if not text_parts:
                return ""
            
            combined_lines = []
            
            for i, page_text in enumerate(text_parts):
                page_lines = page_text.split('\n')
                
                # Check if this page continues a table from previous page
                if i > 0 and combined_lines:
                    last_line = combined_lines[-1].strip() if combined_lines else ""
                    first_line = page_lines[0].strip() if page_lines else ""
                    
                    # If both lines look like table rows, merge without extra spacing
                    if (self._looks_like_table_row(last_line) and 
                        self._looks_like_table_row(first_line)):
                        # Continue table without page break spacing
                        combined_lines.extend(page_lines)
                        continue
                
                # Add page break spacing for non-table content
                if i > 0:
                    combined_lines.append("")  # Single line break instead of double
                
                combined_lines.extend(page_lines)
            
            return '\n'.join(combined_lines)
            
        except Exception as e:
            logger.warning(f"⚠️ Page combining failed, using simple join: {e}")
            return "\n\n".join(text_parts)
    
    def _looks_like_table_row(self, line: str) -> bool:
        """Quick check if a line looks like a table row"""
        if not line.strip():
            return False
        
        # Check for common table separators
        separators = ['|', '\t']
        for sep in separators:
            if line.count(sep) >= 1:
                parts = [p.strip() for p in line.split(sep) if p.strip()]
                if len(parts) >= 2:
                    return True
        
        # Check for spaced columns (multiple spaces)
        if re.search(r'\w+\s{2,}\w+', line):
            return True
            
        return False
    
    async def get_detailed_document_analysis(self, file_content: bytes) -> Dict[str, Any]:
        """Get detailed document analysis using Google Vision Document AI"""
        try:
            if not self.client:
                return {'error': 'client_not_initialized'}
            
            # Use document_text_detection for more detailed analysis
            image = vision.Image(content=file_content)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.document_text_detection(image=image)
            )
            
            if response.error.message:
                return {'error': response.error.message}
            
            # Extract detailed information
            document = response.full_text_annotation
            
            analysis = {
                'text': document.text,
                'confidence': self._calculate_document_confidence(document),
                'pages': len(document.pages),
                'paragraphs': sum(len(page.blocks) for page in document.pages),
                'words': sum(len(paragraph.words) for page in document.pages 
                            for block in page.blocks for paragraph in block.paragraphs),
                'detected_languages': [lang.language_code for lang in document.pages[0].property.detected_languages] if document.pages else []
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Detailed document analysis failed: {e}")
            return {'error': str(e)}
    
    def _calculate_document_confidence(self, document) -> float:
        """Calculate average confidence from document analysis"""
        try:
            confidences = []
            for page in document.pages:
                for block in page.blocks:
                    if hasattr(block, 'confidence'):
                        confidences.append(block.confidence)
                    for paragraph in block.paragraphs:
                        if hasattr(paragraph, 'confidence'):
                            confidences.append(paragraph.confidence)
                        for word in paragraph.words:
                            if hasattr(word, 'confidence'):
                                confidences.append(word.confidence)
            
            return sum(confidences) / len(confidences) if confidences else 0.0
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to calculate document confidence: {e}")
            return 0.0

# Global instance
google_vision_ocr_service = GoogleVisionOCRService()
