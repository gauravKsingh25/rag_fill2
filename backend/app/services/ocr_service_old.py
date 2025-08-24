"""
OCR Service for Intelligent Document Processing
Handles optical character recognition for scanned PDFs and images
Implements intelligent detection and efficient processing strategies
"""

import os
import io
import logging
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from pathlib import Path
import base64
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
from dataclasses import dataclass
from enum import Enum
import asyncio
import concurrent.futures
import warnings

# Suppress PyTorch warnings about GPU not being available
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", message=".*accelerator.*")

# OCR Libraries
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
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Optional cloud OCR services
try:
    from google.cloud import vision
    GOOGLE_VISION_AVAILABLE = True
except ImportError:
    GOOGLE_VISION_AVAILABLE = False

logger = logging.getLogger(__name__)

class OCRMethod(Enum):
    """Available OCR methods"""
    TESSERACT = "tesseract"
    EASYOCR = "easyocr"
    GOOGLE_VISION = "google_vision"
    HYBRID = "hybrid"

class DocumentType(Enum):
    """Document type classification"""
    TEXT_PDF = "text_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE_PDF = "image_pdf"
    MIXED_PDF = "mixed_pdf"
    IMAGE_FILE = "image_file"

@dataclass
class OCRResult:
    """OCR processing result"""
    text: str
    confidence: float
    method_used: str
    processing_time: float
    page_count: int
    detected_quality: str
    preprocessing_applied: List[str]
    extraction_metadata: Dict[str, Any]

@dataclass
class PageAnalysis:
    """Analysis of a single page"""
    page_number: int
    has_text: bool
    has_images: bool
    text_coverage: float
    image_count: int
    requires_ocr: bool
    suggested_method: OCRMethod

class OCRConfig:
    """OCR Configuration"""
    def __init__(self):
        # General settings
        self.enabled = True
        self.auto_detect_scanned = True
        self.text_coverage_threshold = 0.1  # If text coverage < 10%, likely scanned
        self.min_confidence_threshold = 0.3  # Reduced from 0.6 for better text capture
        
        # Tesseract settings
        self.tesseract_config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,;:!?()[]{}"\'-_@#$%^&*+=|\\/<>'
        self.tesseract_timeout = 30
        
        # EasyOCR settings
        self.easyocr_languages = ['en']
        self.easyocr_gpu = False
        self.easyocr_timeout = 30  # Reduced timeout for EasyOCR processing
        
        # Performance settings
        self.max_workers = 2
        self.max_image_size = (2000, 2000)
        self.dpi_threshold = 150
        
        # Preprocessing settings
        self.enhance_contrast = True
        self.denoise = True
        self.sharpen = True
        self.auto_rotate = True

class IntelligentOCRService:
    """
    Intelligent OCR service that automatically detects scanned documents
    and applies the best OCR strategy for optimal results
    """
    
    def __init__(self, config: Optional[OCRConfig] = None):
        self.config = config or OCRConfig()
        self.easyocr_reader = None
        self._initialize_ocr_engines()
        
        # Performance tracking
        self.processing_stats = {
            'total_documents': 0,
            'ocr_documents': 0,
            'text_documents': 0,
            'avg_processing_time': 0.0,
            'method_usage': {method.value: 0 for method in OCRMethod}
        }
        
        logger.info("🔍 OCR Service initialized with intelligent document detection")
    
    def _initialize_ocr_engines(self):
        """Initialize available OCR engines"""
        self.available_methods = []
        
        if TESSERACT_AVAILABLE:
            try:
                # Test Tesseract installation
                pytesseract.get_tesseract_version()
                self.available_methods.append(OCRMethod.TESSERACT)
                logger.info("✅ Tesseract OCR engine available")
            except Exception as e:
                logger.warning(f"⚠️ Tesseract not properly configured: {e}")
        
        if EASYOCR_AVAILABLE:
            self.available_methods.append(OCRMethod.EASYOCR)
            logger.info("✅ EasyOCR engine available")
        
        if GOOGLE_VISION_AVAILABLE and os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
            self.available_methods.append(OCRMethod.GOOGLE_VISION)
            logger.info("✅ Google Vision API available")
        
        if not self.available_methods:
            logger.error("❌ No OCR engines available! Install pytesseract or easyocr")
        else:
            logger.info(f"🔧 Available OCR methods: {[m.value for m in self.available_methods]}")
    
    async def process_document(
        self, 
        file_content: bytes, 
        filename: str,
        force_ocr: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Main entry point for document processing
        Intelligently determines if OCR is needed and applies best strategy
        """
        try:
            start_time = time.time()
            logger.info(f"🔍 Starting intelligent document analysis: {filename}")
            
            # Update stats
            self.processing_stats['total_documents'] += 1
            
            # Step 1: Analyze document to determine if OCR is needed
            document_analysis = await self._analyze_document(file_content, filename)
            
            if not force_ocr and document_analysis['document_type'] == DocumentType.TEXT_PDF:
                logger.info(f"📄 Document {filename} contains readable text, no OCR needed")
                self.processing_stats['text_documents'] += 1
                return "", {
                    'ocr_required': False,
                    'document_type': 'text_pdf',
                    'analysis': document_analysis,
                    'processing_time': time.time() - start_time
                }
            
            # Step 2: OCR is needed - determine best strategy
            logger.info(f"🔍 OCR required for {filename} - Document type: {document_analysis['document_type'].value}")
            self.processing_stats['ocr_documents'] += 1
            
            # Step 3: Apply intelligent OCR processing
            ocr_result = await self._apply_intelligent_ocr(file_content, document_analysis)
            
            # Step 4: Post-process and validate results
            final_text = self._post_process_ocr_text(ocr_result.text)
            
            processing_time = time.time() - start_time
            self.processing_stats['avg_processing_time'] = (
                (self.processing_stats['avg_processing_time'] * (self.processing_stats['total_documents'] - 1) + processing_time) 
                / self.processing_stats['total_documents']
            )
            
            # Update method usage stats
            self.processing_stats['method_usage'][ocr_result.method_used] += 1
            
            logger.info(f"✅ OCR completed for {filename} - "
                       f"Method: {ocr_result.method_used}, "
                       f"Confidence: {ocr_result.confidence:.2f}, "
                       f"Time: {processing_time:.2f}s, "
                       f"Text length: {len(final_text)}")
            
            return final_text, {
                'ocr_required': True,
                'ocr_result': {
                    'method_used': ocr_result.method_used,
                    'confidence': ocr_result.confidence,
                    'processing_time': ocr_result.processing_time,
                    'page_count': ocr_result.page_count,
                    'detected_quality': ocr_result.detected_quality,
                    'preprocessing_applied': ocr_result.preprocessing_applied
                },
                'document_analysis': document_analysis,
                'total_processing_time': processing_time,
                'text_extracted_length': len(final_text)
            }
            
        except Exception as e:
            logger.error(f"❌ OCR processing failed for {filename}: {e}")
            raise
    
    async def _analyze_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Analyze document to determine if OCR is needed
        Returns comprehensive analysis including page-by-page breakdown
        """
        try:
            file_extension = Path(filename).suffix.lower()
            
            if file_extension in ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']:
                return {
                    'document_type': DocumentType.IMAGE_FILE,
                    'requires_ocr': True,
                    'confidence': 1.0,
                    'analysis_method': 'file_extension',
                    'page_analyses': [],
                    'total_pages': 1
                }
            
            if file_extension != '.pdf':
                return {
                    'document_type': DocumentType.TEXT_PDF,
                    'requires_ocr': False,
                    'confidence': 1.0,
                    'analysis_method': 'not_supported',
                    'page_analyses': [],
                    'total_pages': 0
                }
            
            # Analyze PDF content
            return await self._analyze_pdf_content(file_content)
            
        except Exception as e:
            logger.error(f"❌ Document analysis failed: {e}")
            # Default to requiring OCR if analysis fails
            return {
                'document_type': DocumentType.SCANNED_PDF,
                'requires_ocr': True,
                'confidence': 0.5,
                'analysis_method': 'fallback_due_to_error',
                'error': str(e),
                'page_analyses': [],
                'total_pages': 1
            }
    
    async def _analyze_pdf_content(self, file_content: bytes) -> Dict[str, Any]:
        """Analyze PDF to determine if it contains text or requires OCR"""
        try:
            if not PYMUPDF_AVAILABLE:
                logger.warning("⚠️ PyMuPDF not available for PDF analysis, assuming OCR needed")
                return {
                    'document_type': DocumentType.SCANNED_PDF,
                    'requires_ocr': True,
                    'confidence': 0.7,
                    'analysis_method': 'no_pymupdf',
                    'page_analyses': [],
                    'total_pages': 1
                }
            
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            total_pages = len(pdf_document)
            page_analyses = []
            
            text_pages = 0
            image_pages = 0
            mixed_pages = 0
            
            logger.info(f"📄 Analyzing {total_pages} pages for text/image content")
            
            for page_num in range(min(total_pages, 10)):  # Analyze first 10 pages for efficiency
                try:
                    page = pdf_document.load_page(page_num)
                    
                    # Extract text content
                    text_content = page.get_text().strip()
                    text_length = len(text_content)
                    
                    # Get page images
                    image_list = page.get_images()
                    image_count = len(image_list)
                    
                    # Calculate text coverage (rough estimate)
                    page_area = page.rect.width * page.rect.height
                    text_blocks = page.get_text("dict")["blocks"]
                    text_area = sum(
                        (block.get("bbox", [0, 0, 0, 0])[2] - block.get("bbox", [0, 0, 0, 0])[0]) *
                        (block.get("bbox", [0, 0, 0, 0])[3] - block.get("bbox", [0, 0, 0, 0])[1])
                        for block in text_blocks if "lines" in block
                    )
                    text_coverage = min(text_area / page_area if page_area > 0 else 0, 1.0)
                    
                    # Determine page type
                    has_meaningful_text = text_length > 50 and text_coverage > self.config.text_coverage_threshold
                    has_images = image_count > 0
                    
                    if has_meaningful_text and not has_images:
                        page_type = "text"
                        text_pages += 1
                        requires_ocr = False
                        suggested_method = None
                    elif not has_meaningful_text and has_images:
                        page_type = "image"
                        image_pages += 1
                        requires_ocr = True
                        suggested_method = self._select_best_ocr_method(image_count, text_coverage)
                    elif has_meaningful_text and has_images:
                        page_type = "mixed"
                        mixed_pages += 1
                        requires_ocr = True  # OCR for images, keep existing text
                        suggested_method = self._select_best_ocr_method(image_count, text_coverage)
                    else:
                        page_type = "empty"
                        requires_ocr = False
                        suggested_method = None
                    
                    page_analysis = PageAnalysis(
                        page_number=page_num + 1,
                        has_text=has_meaningful_text,
                        has_images=has_images,
                        text_coverage=text_coverage,
                        image_count=image_count,
                        requires_ocr=requires_ocr,
                        suggested_method=suggested_method
                    )
                    page_analyses.append(page_analysis)
                    
                    logger.debug(f"📄 Page {page_num + 1}: {page_type}, "
                               f"text_len={text_length}, images={image_count}, "
                               f"coverage={text_coverage:.2f}, ocr_needed={requires_ocr}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to analyze page {page_num + 1}: {e}")
                    continue
            
            pdf_document.close()
            
            # Determine overall document type
            total_analyzed = len(page_analyses)
            if total_analyzed == 0:
                document_type = DocumentType.SCANNED_PDF
                requires_ocr = True
                confidence = 0.5
            elif text_pages == total_analyzed:
                document_type = DocumentType.TEXT_PDF
                requires_ocr = False
                confidence = 0.9
            elif image_pages == total_analyzed:
                document_type = DocumentType.SCANNED_PDF
                requires_ocr = True
                confidence = 0.9
            else:
                document_type = DocumentType.MIXED_PDF
                requires_ocr = True
                confidence = 0.8
            
            logger.info(f"📊 PDF Analysis: {document_type.value} - "
                       f"Text pages: {text_pages}, Image pages: {image_pages}, "
                       f"Mixed pages: {mixed_pages}, OCR needed: {requires_ocr}")
            
            return {
                'document_type': document_type,
                'requires_ocr': requires_ocr,
                'confidence': confidence,
                'analysis_method': 'content_analysis',
                'total_pages': total_pages,
                'analyzed_pages': total_analyzed,
                'text_pages': text_pages,
                'image_pages': image_pages,
                'mixed_pages': mixed_pages,
                'page_analyses': [
                    {
                        'page_number': pa.page_number,
                        'has_text': pa.has_text,
                        'has_images': pa.has_images,
                        'text_coverage': pa.text_coverage,
                        'image_count': pa.image_count,
                        'requires_ocr': pa.requires_ocr,
                        'suggested_method': pa.suggested_method.value if pa.suggested_method else None
                    }
                    for pa in page_analyses
                ]
            }
            
        except Exception as e:
            logger.error(f"❌ PDF content analysis failed: {e}")
            return {
                'document_type': DocumentType.SCANNED_PDF,
                'requires_ocr': True,
                'confidence': 0.5,
                'analysis_method': 'fallback_due_to_error',
                'error': str(e),
                'page_analyses': [],
                'total_pages': 1
            }
    
    def _select_best_ocr_method(self, image_count: int, text_coverage: float) -> OCRMethod:
        """Select the best OCR method based on content analysis"""
        # For complex documents with many images, prefer EasyOCR
        if image_count > 3 and OCRMethod.EASYOCR in self.available_methods:
            return OCRMethod.EASYOCR
        
        # For documents with some text, use hybrid approach
        if text_coverage > 0.05 and len(self.available_methods) > 1:
            return OCRMethod.HYBRID
        
        # Default to the best available method
        if OCRMethod.EASYOCR in self.available_methods:
            return OCRMethod.EASYOCR
        elif OCRMethod.TESSERACT in self.available_methods:
            return OCRMethod.TESSERACT
        elif OCRMethod.GOOGLE_VISION in self.available_methods:
            return OCRMethod.GOOGLE_VISION
        else:
            return self.available_methods[0] if self.available_methods else OCRMethod.TESSERACT
    
    async def _apply_intelligent_ocr(
        self, 
        file_content: bytes, 
        document_analysis: Dict[str, Any]
    ) -> OCRResult:
        """Apply intelligent OCR based on document analysis"""
        try:
            start_time = time.time()
            
            # Determine OCR strategy
            document_type = document_analysis['document_type']
            
            if document_type == DocumentType.IMAGE_FILE:
                return await self._process_image_file(file_content, document_analysis)
            elif document_type in [DocumentType.SCANNED_PDF, DocumentType.IMAGE_PDF, DocumentType.MIXED_PDF]:
                return await self._process_pdf_with_ocr(file_content, document_analysis)
            else:
                raise ValueError(f"Unsupported document type for OCR: {document_type}")
                
        except Exception as e:
            logger.error(f"❌ Intelligent OCR failed: {e}")
            raise
    
    async def _process_image_file(
        self, 
        file_content: bytes, 
        document_analysis: Dict[str, Any]
    ) -> OCRResult:
        """Process image file with OCR"""
        try:
            start_time = time.time()
            
            # Load and preprocess image
            image = Image.open(io.BytesIO(file_content))
            preprocessed_image, preprocessing_steps = await self._preprocess_image(image)
            
            # Apply OCR using the best available method
            method = self._select_best_ocr_method(1, 0.0)
            
            if method == OCRMethod.HYBRID:
                text, confidence = await self._apply_hybrid_ocr(preprocessed_image)
            elif method == OCRMethod.EASYOCR:
                text, confidence = await self._apply_easyocr(preprocessed_image)
            elif method == OCRMethod.TESSERACT:
                text, confidence = await self._apply_tesseract(preprocessed_image)
            elif method == OCRMethod.GOOGLE_VISION:
                text, confidence = await self._apply_google_vision(preprocessed_image)
            else:
                raise ValueError(f"Unsupported OCR method: {method}")
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=text,
                confidence=confidence,
                method_used=method.value,
                processing_time=processing_time,
                page_count=1,
                detected_quality=self._assess_image_quality(image),
                preprocessing_applied=preprocessing_steps,
                extraction_metadata={
                    'image_size': image.size,
                    'image_mode': image.mode,
                    'estimated_dpi': self._estimate_dpi(image)
                }
            )
            
        except Exception as e:
            logger.error(f"❌ Image file OCR failed: {e}")
            raise
    
    async def _process_pdf_with_ocr(
        self, 
        file_content: bytes, 
        document_analysis: Dict[str, Any]
    ) -> OCRResult:
        """Process PDF with intelligent OCR strategy"""
        try:
            start_time = time.time()
            
            if not PYMUPDF_AVAILABLE:
                raise ValueError("PyMuPDF required for PDF OCR processing")
            
            pdf_document = fitz.open(stream=file_content, filetype="pdf")
            total_pages = len(pdf_document)
            
            extracted_texts = []
            preprocessing_steps = []
            page_confidences = []
            
            # Process pages based on analysis
            page_analyses = document_analysis.get('page_analyses', [])
            
            logger.info(f"📄 Processing {total_pages} pages with intelligent OCR")
            
            # Use thread pool for parallel processing of pages
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                tasks = []
                
                for page_num in range(total_pages):
                    page_analysis = None
                    if page_num < len(page_analyses):
                        page_analysis = page_analyses[page_num]
                    
                    # Create task for page processing
                    task = executor.submit(
                        self._process_pdf_page_sync,
                        pdf_document,
                        page_num,
                        page_analysis
                    )
                    tasks.append(task)
                
                # Collect results
                for i, task in enumerate(concurrent.futures.as_completed(tasks)):
                    try:
                        page_result = task.result()
                        if page_result:
                            extracted_texts.append(page_result['text'])
                            page_confidences.append(page_result['confidence'])
                            preprocessing_steps.extend(page_result['preprocessing'])
                        logger.debug(f"📄 Completed page {i + 1}/{total_pages}")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to process page {i + 1}: {e}")
                        continue
            
            pdf_document.close()
            
            # Combine results
            full_text = "\n\n".join(extracted_texts)
            avg_confidence = sum(page_confidences) / len(page_confidences) if page_confidences else 0.0
            processing_time = time.time() - start_time
            
            # Determine method used (based on most common)
            method_used = self._select_best_ocr_method(1, 0.0).value
            
            return OCRResult(
                text=full_text,
                confidence=avg_confidence,
                method_used=method_used,
                processing_time=processing_time,
                page_count=total_pages,
                detected_quality=self._assess_pdf_quality(document_analysis),
                preprocessing_applied=list(set(preprocessing_steps)),
                extraction_metadata={
                    'pages_processed': len(extracted_texts),
                    'pages_with_text': len([t for t in extracted_texts if t.strip()]),
                    'avg_text_length_per_page': len(full_text) / total_pages if total_pages > 0 else 0
                }
            )
            
        except Exception as e:
            logger.error(f"❌ PDF OCR processing failed: {e}")
            raise
    
    def _process_pdf_page_sync(
        self, 
        pdf_document, 
        page_num: int, 
        page_analysis: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Synchronous method for processing a single PDF page (for thread pool)"""
        try:
            page = pdf_document.load_page(page_num)
            
            # Check if this page needs OCR
            if page_analysis and not page_analysis.get('requires_ocr', True):
                # Page already has readable text, extract it directly
                text = page.get_text()
                return {
                    'text': text,
                    'confidence': 0.95,  # High confidence for direct text extraction
                    'preprocessing': ['direct_text_extraction']
                }
            
            # Extract images from page for OCR
            image_list = page.get_images()
            if not image_list:
                # No images to process, try to get any existing text
                text = page.get_text()
                return {
                    'text': text,
                    'confidence': 0.8 if text.strip() else 0.0,
                    'preprocessing': ['no_images_found']
                }
            
            page_texts = []
            page_confidences = []
            preprocessing_applied = []
            
            # Process each image on the page
            for img_index, img in enumerate(image_list):
                try:
                    # Extract image
                    xref = img[0]
                    pix = fitz.Pixmap(pdf_document, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        # Convert to PIL Image
                        img_data = pix.tobytes("png")
                        image = Image.open(io.BytesIO(img_data))
                        
                        # Preprocess image
                        preprocessed_image, preprocessing_steps = self._preprocess_image_sync(image)
                        preprocessing_applied.extend(preprocessing_steps)
                        
                        # Apply OCR
                        text, confidence = self._apply_ocr_sync(preprocessed_image)
                        
                        if text.strip():
                            page_texts.append(text)
                            page_confidences.append(confidence)
                    
                    pix = None  # Free memory
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to process image {img_index} on page {page_num + 1}: {e}")
                    continue
            
            # Combine page results
            combined_text = "\n".join(page_texts)
            avg_confidence = sum(page_confidences) / len(page_confidences) if page_confidences else 0.0
            
            return {
                'text': combined_text,
                'confidence': avg_confidence,
                'preprocessing': preprocessing_applied
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to process PDF page {page_num + 1}: {e}")
            return None
    
    async def _preprocess_image(self, image: Image.Image) -> Tuple[Image.Image, List[str]]:
        """Preprocess image for better OCR results"""
        try:
            preprocessing_steps = []
            processed_image = image.copy()
            
            # Convert to RGB if needed
            if processed_image.mode != 'RGB':
                processed_image = processed_image.convert('RGB')
                preprocessing_steps.append('convert_to_rgb')
            
            # Resize if too large
            if max(processed_image.size) > max(self.config.max_image_size):
                # Use LANCZOS instead of deprecated ANTIALIAS
                processed_image.thumbnail(self.config.max_image_size, Image.Resampling.LANCZOS)
                preprocessing_steps.append('resize')
            
            # Enhance contrast
            if self.config.enhance_contrast:
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(1.2)
                preprocessing_steps.append('enhance_contrast')
            
            # Sharpen
            if self.config.sharpen:
                processed_image = processed_image.filter(ImageFilter.SHARPEN)
                preprocessing_steps.append('sharpen')
            
            # Denoise (simple median filter)
            if self.config.denoise:
                processed_image = processed_image.filter(ImageFilter.MedianFilter(size=3))
                preprocessing_steps.append('denoise')
            
            return processed_image, preprocessing_steps
            
        except Exception as e:
            logger.warning(f"⚠️ Image preprocessing failed: {e}")
            return image, ['preprocessing_failed']
    
    def _preprocess_image_sync(self, image: Image.Image) -> Tuple[Image.Image, List[str]]:
        """Synchronous version of image preprocessing"""
        # Same logic as async version, but synchronous
        try:
            preprocessing_steps = []
            processed_image = image.copy()
            
            if processed_image.mode != 'RGB':
                processed_image = processed_image.convert('RGB')
                preprocessing_steps.append('convert_to_rgb')
            
            if max(processed_image.size) > max(self.config.max_image_size):
                # Use LANCZOS instead of deprecated ANTIALIAS
                processed_image.thumbnail(self.config.max_image_size, Image.Resampling.LANCZOS)
                preprocessing_steps.append('resize')
            
            if self.config.enhance_contrast:
                enhancer = ImageEnhance.Contrast(processed_image)
                processed_image = enhancer.enhance(1.2)
                preprocessing_steps.append('enhance_contrast')
            
            if self.config.sharpen:
                processed_image = processed_image.filter(ImageFilter.SHARPEN)
                preprocessing_steps.append('sharpen')
            
            if self.config.denoise:
                processed_image = processed_image.filter(ImageFilter.MedianFilter(size=3))
                preprocessing_steps.append('denoise')
            
            return processed_image, preprocessing_steps
            
        except Exception as e:
            logger.warning(f"⚠️ Image preprocessing failed: {e}")
            return image, ['preprocessing_failed']
    
    async def _apply_hybrid_ocr(self, image: Image.Image) -> Tuple[str, float]:
        """Apply multiple OCR methods and combine results"""
        try:
            results = []
            
            # Try EasyOCR
            if OCRMethod.EASYOCR in self.available_methods:
                try:
                    text, confidence = await self._apply_easyocr(image)
                    results.append(('easyocr', text, confidence))
                except Exception as e:
                    logger.warning(f"⚠️ EasyOCR failed in hybrid mode: {e}")
            
            # Try Tesseract
            if OCRMethod.TESSERACT in self.available_methods:
                try:
                    text, confidence = await self._apply_tesseract(image)
                    results.append(('tesseract', text, confidence))
                except Exception as e:
                    logger.warning(f"⚠️ Tesseract failed in hybrid mode: {e}")
            
            if not results:
                raise ValueError("No OCR methods succeeded in hybrid mode")
            
            # Select best result based on confidence and text length
            best_result = max(results, key=lambda x: x[2] * (len(x[1]) / 100))
            
            return best_result[1], best_result[2]
            
        except Exception as e:
            logger.error(f"❌ Hybrid OCR failed: {e}")
            raise
    
    async def _apply_easyocr(self, image: Image.Image) -> Tuple[str, float]:
        """Apply EasyOCR to image using thread pool to avoid blocking"""
        try:
            logger.info("🚀 Starting EasyOCR processing with timeout protection...")
            
            # Run the synchronous EasyOCR processing in a thread pool with timeout
            loop = asyncio.get_event_loop()
            
            # Use a more aggressive approach with nested timeouts
            start_time = time.time()
            
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, self._apply_easyocr_sync, image),
                    timeout=self.config.easyocr_timeout
                )
                
                processing_time = time.time() - start_time
                logger.info(f"✅ EasyOCR completed successfully in {processing_time:.2f} seconds")
                
                return result
                
            except asyncio.TimeoutError:
                processing_time = time.time() - start_time
                logger.error(f"❌ EasyOCR timed out after {processing_time:.2f} seconds (limit: {self.config.easyocr_timeout}s)")
                
                # Return empty result instead of raising to allow system to continue
                logger.warning("⚠️ Returning empty result due to timeout - document processing will continue")
                return "", 0.0
            
        except Exception as e:
            logger.error(f"❌ EasyOCR processing failed with exception: {e}")
            # Return empty result instead of raising to allow system to continue
            logger.warning("⚠️ Returning empty result due to error - document processing will continue")
            return "", 0.0
    
    async def _apply_tesseract(self, image: Image.Image) -> Tuple[str, float]:
        """Apply Tesseract OCR to image"""
        try:
            # Convert image to bytes for Tesseract
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Apply Tesseract
            text = pytesseract.image_to_string(
                image,
                config=self.config.tesseract_config,
                timeout=self.config.tesseract_timeout
            )
            
            # Get confidence data
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
            except:
                avg_confidence = 0.7  # Default confidence
            
            return text.strip(), avg_confidence
            
        except Exception as e:
            logger.error(f"❌ Tesseract processing failed: {e}")
            raise
    
    async def _apply_google_vision(self, image: Image.Image) -> Tuple[str, float]:
        """Apply Google Vision API OCR"""
        try:
            if not GOOGLE_VISION_AVAILABLE:
                raise ValueError("Google Vision API not available")
            
            client = vision.ImageAnnotatorClient()
            
            # Convert PIL image to bytes
            img_bytes = io.BytesIO()
            image.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            vision_image = vision.Image(content=img_bytes.read())
            
            # Perform text detection
            response = client.text_detection(image=vision_image)
            texts = response.text_annotations
            
            if texts:
                # First annotation contains the entire detected text
                full_text = texts[0].description
                confidence = 0.9  # Google Vision doesn't provide confidence scores
                return full_text, confidence
            else:
                return "", 0.0
                
        except Exception as e:
            logger.error(f"❌ Google Vision processing failed: {e}")
            raise
    
    def _apply_ocr_sync(self, image: Image.Image) -> Tuple[str, float]:
        """Synchronous OCR application for thread pool usage"""
        try:
            # Use the best available method
            if OCRMethod.EASYOCR in self.available_methods:
                return self._apply_easyocr_sync(image)
            elif OCRMethod.TESSERACT in self.available_methods:
                return self._apply_tesseract_sync(image)
            else:
                return "", 0.0
        except Exception as e:
            logger.warning(f"⚠️ Synchronous OCR failed: {e}")
            return "", 0.0
    
    def _apply_easyocr_sync(self, image: Image.Image) -> Tuple[str, float]:
        """Synchronous EasyOCR application"""
        try:
            logger.info("🔄 Starting EasyOCR processing...")
            start_time = time.time()
            
            if self.easyocr_reader is None:
                logger.info("📦 Initializing EasyOCR reader (this may take a moment)...")
                init_start = time.time()
                self.easyocr_reader = easyocr.Reader(
                    self.config.easyocr_languages,
                    gpu=self.config.easyocr_gpu
                )
                init_time = time.time() - init_start
                logger.info(f"✅ EasyOCR reader initialized in {init_time:.2f} seconds")
            
            logger.info("🔍 Processing image with EasyOCR...")
            img_array = np.array(image)
            results = self.easyocr_reader.readtext(img_array)
            
            processing_time = time.time() - start_time
            logger.info(f"✅ EasyOCR processing completed in {processing_time:.2f} seconds")
            logger.info(f"📊 Found {len(results)} text regions")
            
            text_parts = []
            confidences = []
            
            for (bbox, text, confidence) in results:
                logger.debug(f"🔍 OCR detected: '{text}' (confidence: {confidence:.2f})")
                if confidence > self.config.min_confidence_threshold:
                    text_parts.append(text)
                    confidences.append(confidence)
                else:
                    logger.debug(f"⏭️ Skipping low confidence: '{text}' ({confidence:.2f} < {self.config.min_confidence_threshold})")
            
            combined_text = ' '.join(text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            logger.info(f"📝 Final result: {len(combined_text)} characters, {len(text_parts)} accepted regions, avg confidence: {avg_confidence:.2f}")
            
            return combined_text, avg_confidence
            
        except Exception as e:
            logger.error(f"❌ Synchronous EasyOCR failed: {e}")
            return "", 0.0
    
    def _apply_tesseract_sync(self, image: Image.Image) -> Tuple[str, float]:
        """Synchronous Tesseract application"""
        try:
            text = pytesseract.image_to_string(
                image,
                config=self.config.tesseract_config,
                timeout=self.config.tesseract_timeout
            )
            
            try:
                data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.0
            except:
                avg_confidence = 0.7
            
            return text.strip(), avg_confidence
            
        except Exception as e:
            logger.warning(f"⚠️ Synchronous Tesseract failed: {e}")
            return "", 0.0
    
    def _post_process_ocr_text(self, text: str) -> str:
        """Clean and improve OCR text"""
        try:
            if not text:
                return ""
            
            # Remove excessive whitespace
            import re
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            # Fix common OCR errors
            corrections = {
                'rn': 'm',  # Common OCR error
                'vv': 'w',
                '0': 'O',   # Numbers that should be letters (context-dependent)
                '1': 'I',   # Context-dependent
                '5': 'S',   # Context-dependent
            }
            
            # Apply corrections cautiously (only if surrounded by letters)
            for wrong, correct in corrections.items():
                pattern = f'(?<=[a-zA-Z]){re.escape(wrong)}(?=[a-zA-Z])'
                text = re.sub(pattern, correct, text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ OCR text post-processing failed: {e}")
            return text
    
    def _assess_image_quality(self, image: Image.Image) -> str:
        """Assess image quality for OCR"""
        try:
            width, height = image.size
            pixel_count = width * height
            
            if pixel_count > 2000000:  # 2MP+
                return "high"
            elif pixel_count > 500000:  # 0.5MP+
                return "medium"
            else:
                return "low"
                
        except Exception:
            return "unknown"
    
    def _assess_pdf_quality(self, document_analysis: Dict[str, Any]) -> str:
        """Assess PDF quality based on analysis"""
        try:
            image_pages = document_analysis.get('image_pages', 0)
            text_pages = document_analysis.get('text_pages', 0)
            total_pages = document_analysis.get('total_pages', 1)
            
            if text_pages / total_pages > 0.8:
                return "high"
            elif image_pages / total_pages > 0.8:
                return "low"
            else:
                return "medium"
                
        except Exception:
            return "unknown"
    
    def _estimate_dpi(self, image: Image.Image) -> int:
        """Estimate DPI of image"""
        try:
            # Try to get DPI from image info
            if hasattr(image, 'info') and 'dpi' in image.info:
                return int(image.info['dpi'][0])
            
            # Estimate based on size (rough heuristic)
            width, height = image.size
            if width > 2000 or height > 2000:
                return 300
            elif width > 1000 or height > 1000:
                return 150
            else:
                return 75
                
        except Exception:
            return 150  # Default assumption
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get OCR processing statistics"""
        return {
            'total_documents_processed': self.processing_stats['total_documents'],
            'documents_requiring_ocr': self.processing_stats['ocr_documents'],
            'text_only_documents': self.processing_stats['text_documents'],
            'ocr_rate': (
                self.processing_stats['ocr_documents'] / 
                max(self.processing_stats['total_documents'], 1)
            ),
            'average_processing_time': self.processing_stats['avg_processing_time'],
            'method_usage_distribution': self.processing_stats['method_usage'],
            'available_ocr_methods': [method.value for method in self.available_methods],
            'configuration': {
                'auto_detect_enabled': self.config.auto_detect_scanned,
                'text_coverage_threshold': self.config.text_coverage_threshold,
                'min_confidence_threshold': self.config.min_confidence_threshold,
                'max_workers': self.config.max_workers
            }
        }

# Global OCR service instance
ocr_service = IntelligentOCRService()

# Export availability flag for easy checking
OCR_AVAILABLE = True
