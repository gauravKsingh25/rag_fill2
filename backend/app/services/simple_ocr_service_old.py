"""
Simple and Reliable OCR Service
Handles PDF, PNG, JPG, and other image formats with proper async handling
"""

import os
import io
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import threading

# OCR Libraries with fallback
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

try:
    import fitz  # PyMuPDF for PDF processing
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

logger = logging.getLogger(__name__)

class SimpleOCRService:
    """Simple, reliable OCR service for scanned documents"""
    
    def __init__(self):
        self.easyocr_reader = None
        self.ocr_lock = threading.Lock()
        self.max_image_size = (1500, 1500)  # Reasonable size limit
        self.timeout = 300  # 5-minute timeout per operation
        
        # Initialize available methods
        self.available_methods = []
        self._check_available_methods()
        
        logger.info(f"🔍 Simple OCR Service initialized - Available methods: {self.available_methods}")
    
    def _check_available_methods(self):
        """Check which OCR methods are available"""
        if TESSERACT_AVAILABLE:
            try:
                pytesseract.get_tesseract_version()
                self.available_methods.append("tesseract")
                logger.info("✅ Tesseract OCR available")
            except Exception as e:
                logger.warning(f"⚠️ Tesseract not properly configured: {e}")
        
        if EASYOCR_AVAILABLE:
            self.available_methods.append("easyocr")
            logger.info("✅ EasyOCR available")
        
        if not self.available_methods:
            logger.error("❌ No OCR engines available! Please install pytesseract or easyocr")
    
    def should_process_with_ocr(self, filename: str) -> bool:
        """Check if file should be processed with OCR"""
        file_extension = Path(filename).suffix.lower()
        ocr_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']
        return file_extension in ocr_extensions
    
    async def process_document(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """
        Process document and extract text using OCR if needed
        Returns (extracted_text, metadata)
        """
        try:
            start_time = time.time()
            
            if not self.should_process_with_ocr(filename):
                return "", {
                    'ocr_required': False,
                    'reason': 'file_type_not_supported',
                    'processing_time': 0
                }
            
            if not self.available_methods:
                logger.error("❌ No OCR methods available")
                return "", {
                    'ocr_required': True,
                    'error': 'no_ocr_methods_available',
                    'processing_time': 0
                }
            
            file_extension = Path(filename).suffix.lower()
            
            # Process based on file type
            if file_extension == '.pdf':
                text, metadata = await self._process_pdf(file_content, filename)
            elif file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif']:
                text, metadata = await self._process_image(file_content, filename)
            else:
                return "", {
                    'ocr_required': False,
                    'reason': 'unsupported_file_type',
                    'processing_time': 0
                }
            
            processing_time = time.time() - start_time
            metadata['total_processing_time'] = processing_time
            metadata['ocr_required'] = True
            
            logger.info(f"✅ OCR completed for {filename} - "
                       f"Text length: {len(text)}, "
                       f"Time: {processing_time:.2f}s")
            
            return text, metadata
            
        except Exception as e:
            logger.error(f"❌ OCR processing failed for {filename}: {e}")
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
            
            # PDF appears to be scanned - apply OCR
            logger.info("🔍 PDF appears to be scanned - applying OCR")
            return await self._extract_pdf_with_ocr(file_content, filename)
            
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
    
    async def _extract_pdf_with_ocr(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF using OCR"""
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            total_pages = len(doc)
            
            logger.info(f"📄 Processing {total_pages} pages with OCR")
            
            # Process ALL pages - no limit for complete OCR
            logger.info(f"🔍 Processing all {total_pages} pages with OCR")
            
            text_parts = []
            
            # Process pages with thread pool for better performance
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=2) as executor:
                tasks = []
                
                # Process in smaller batches to avoid memory issues
                batch_size = 10
                logger.info(f"📦 Processing {total_pages} pages in batches of {batch_size}")
                
                for batch_start in range(0, total_pages, batch_size):
                    batch_end = min(batch_start + batch_size, total_pages)
                    logger.info(f"🔄 Processing pages {batch_start + 1}-{batch_end}")
                    
                    batch_tasks = []
                    for page_num in range(batch_start, batch_end):
                        task = loop.run_in_executor(
                            executor, 
                            self._process_pdf_page, 
                            doc, 
                            page_num
                        )
                        batch_tasks.append((page_num, task))
                    
                    # Process batch with extended timeout - no restrictive timeout
                    try:
                        # Much longer timeout for batch processing - 10 minutes per batch
                        batch_timeout = 600  # 10 minutes per batch
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
                            if result and result.strip():
                                text_parts.append(result)
                                logger.debug(f"✅ Page {page_num + 1}: {len(result)} characters")
                        
                        # Log batch progress
                        logger.info(f"✅ Completed batch {batch_start + 1}-{batch_end}: {len([r for r in batch_results if isinstance(r, str) and r.strip()])} pages successful")
                        
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ Batch {batch_start + 1}-{batch_end} timed out after {batch_timeout}s - continuing with next batch")
                        continue
            
            doc.close()
            
            combined_text = "\n\n".join(text_parts)
            
            return combined_text, {
                'method': 'pdf_ocr',
                'total_pages': total_pages,
                'processed_pages': len(text_parts),
                'text_length': len(combined_text),
                'ocr_applied': True
            }
            
        except Exception as e:
            logger.error(f"❌ PDF OCR extraction failed: {e}")
            return "", {'error': str(e)}
    
    def _process_pdf_page(self, doc, page_num: int) -> str:
        """Process a single PDF page (runs in thread)"""
        try:
            page = doc.load_page(page_num)
            
            # Get images from page
            image_list = page.get_images()
            if not image_list:
                return ""
            
            page_text = ""
            
            # Process each image on the page
            for img_index, img in enumerate(image_list[:3]):  # Max 3 images per page
                try:
                    xref = img[0]
                    pix = fitz.Pixmap(doc, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        image = Image.open(io.BytesIO(img_data))
                        
                        # Apply OCR to image
                        text = self._apply_ocr_sync(image)
                        if text and text.strip():
                            page_text += text + "\n"
                    
                    pix = None  # Free memory
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process image {img_index} on page {page_num + 1}: {e}")
                    continue
            
            return page_text.strip()
            
        except Exception as e:
            logger.error(f"❌ Failed to process page {page_num + 1}: {e}")
            return ""
    
    async def _process_image(self, file_content: bytes, filename: str) -> Tuple[str, Dict[str, Any]]:
        """Process image file with OCR"""
        try:
            # Load image
            image = Image.open(io.BytesIO(file_content))
            
            # Preprocess image
            processed_image = self._preprocess_image(image)
            
            # Apply OCR in thread pool with extended timeout
            loop = asyncio.get_event_loop()
            text = await asyncio.wait_for(
                loop.run_in_executor(None, self._apply_ocr_sync, processed_image),
                timeout=300  # 5-minute timeout for individual image
            )
            
            return text, {
                'method': 'image_ocr',
                'image_size': image.size,
                'text_length': len(text),
                'ocr_applied': True
            }
            
        except Exception as e:
            logger.error(f"❌ Image processing failed: {e}")
            return "", {'error': str(e)}
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Simple image preprocessing for better OCR"""
        try:
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Resize if too large
            if max(image.size) > max(self.max_image_size):
                image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.2)
            
            # Sharpen
            image = image.filter(ImageFilter.SHARPEN)
            
            return image
            
        except Exception as e:
            logger.warning(f"⚠️ Image preprocessing failed: {e}")
            return image
    
    def _apply_ocr_sync(self, image: Image.Image) -> str:
        """Apply OCR synchronously (for thread pool)"""
        try:
            # Try EasyOCR first if available
            if "easyocr" in self.available_methods:
                return self._apply_easyocr_sync(image)
            
            # Fallback to Tesseract
            elif "tesseract" in self.available_methods:
                return self._apply_tesseract_sync(image)
            
            return ""
            
        except Exception as e:
            logger.error(f"❌ OCR application failed: {e}")
            return ""
    
    def _apply_easyocr_sync(self, image: Image.Image) -> str:
        """Apply EasyOCR synchronously"""
        try:
            # Initialize reader if needed (thread-safe)
            with self.ocr_lock:
                if self.easyocr_reader is None:
                    logger.info("📦 Initializing EasyOCR reader...")
                    self.easyocr_reader = easyocr.Reader(['en'], gpu=False)
                    logger.info("✅ EasyOCR reader initialized")
            
            # Convert PIL image to numpy array
            img_array = np.array(image)
            
            # Apply OCR
            results = self.easyocr_reader.readtext(img_array)
            
            # Extract text with confidence filtering
            text_parts = []
            for (bbox, text, confidence) in results:
                if confidence > 0.3:  # Filter low-confidence results
                    text_parts.append(text)
            
            return " ".join(text_parts)
            
        except Exception as e:
            logger.error(f"❌ EasyOCR failed: {e}")
            return ""
    
    def _apply_tesseract_sync(self, image: Image.Image) -> str:
        """Apply Tesseract OCR synchronously"""
        try:
            # Basic Tesseract configuration
            config = '--oem 3 --psm 6'
            
            text = pytesseract.image_to_string(
                image, 
                config=config,
                timeout=300  # 5-minute timeout for tesseract
            )
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"❌ Tesseract OCR failed: {e}")
            return ""
    
    def is_available(self) -> bool:
        """Check if OCR service is available"""
        return len(self.available_methods) > 0

# Global instance
simple_ocr_service = SimpleOCRService()
