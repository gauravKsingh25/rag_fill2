"""
Alternative PDF processing without PyMuPDF dependency
"""
import pdfplumber
import PyPDF2
from typing import List, Dict, Any
import io
import logging

logger = logging.getLogger(__name__)

class AlternativePDFProcessor:
    """PDF processor using pdfplumber and PyPDF2 instead of PyMuPDF"""
    
    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        """Extract text using pdfplumber as primary, PyPDF2 as fallback"""
        try:
            # Try pdfplumber first (better text extraction)
            return AlternativePDFProcessor._extract_with_pdfplumber(pdf_bytes)
        except Exception as e:
            logger.warning(f"pdfplumber failed: {e}, trying PyPDF2...")
            try:
                return AlternativePDFProcessor._extract_with_pypdf2(pdf_bytes)
            except Exception as e2:
                logger.error(f"Both PDF processors failed: {e2}")
                return ""
    
    @staticmethod
    def _extract_with_pdfplumber(pdf_bytes: bytes) -> str:
        """Extract text using pdfplumber"""
        text_content = []
        
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                        
                    # Also extract text from tables
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row:
                                table_text = " ".join([cell for cell in row if cell])
                                if table_text.strip():
                                    text_content.append(table_text)
                                    
                except Exception as e:
                    logger.warning(f"Error extracting from page {page_num}: {e}")
                    continue
        
        return "\n\n".join(text_content)
    
    @staticmethod
    def _extract_with_pypdf2(pdf_bytes: bytes) -> str:
        """Extract text using PyPDF2"""
        text_content = []
        
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                except Exception as e:
                    logger.warning(f"Error extracting from page {page_num}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"PyPDF2 failed to read PDF: {e}")
            
        return "\n\n".join(text_content)
    
    @staticmethod
    def get_pdf_metadata(pdf_bytes: bytes) -> Dict[str, Any]:
        """Get PDF metadata"""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            metadata = pdf_reader.metadata
            
            return {
                'title': getattr(metadata, 'title', ''),
                'author': getattr(metadata, 'author', ''),
                'subject': getattr(metadata, 'subject', ''),
                'creator': getattr(metadata, 'creator', ''),
                'producer': getattr(metadata, 'producer', ''),
                'creation_date': getattr(metadata, 'creation_date', ''),
                'modification_date': getattr(metadata, 'modification_date', ''),
                'page_count': len(pdf_reader.pages)
            }
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return {}

# Function to replace PyMuPDF usage
def process_pdf_alternative(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Process PDF using alternative libraries
    Returns both text content and metadata
    """
    processor = AlternativePDFProcessor()
    
    return {
        'text': processor.extract_text_from_pdf(pdf_bytes),
        'metadata': processor.get_pdf_metadata(pdf_bytes)
    }
