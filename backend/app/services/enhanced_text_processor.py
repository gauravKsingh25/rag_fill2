"""
Enhanced Text Processor for OCR Quality Improvement
Specifically designed to clean and improve OCR text from Google Vision for better chunking
"""

import re
import logging
import unicodedata
from typing import List, Dict, Any, Tuple
from collections import Counter
import string

logger = logging.getLogger(__name__)

class EnhancedTextProcessor:
    """Advanced text processor for improving OCR quality and chunk content"""
    
    def __init__(self):
        self.min_chunk_quality = 0.6  # Minimum quality threshold
        self.gibberish_patterns = self._build_gibberish_patterns()
        self.encoding_fixes = self._build_encoding_fixes()
        self.medical_terms = self._build_medical_vocabulary()
        
    def _build_gibberish_patterns(self) -> List[str]:
        """Build patterns that indicate gibberish text"""
        return [
            # Common OCR misreadings
            r'[Il1]{3,}',  # Multiple l, I, 1 in sequence
            r'[oO0]{3,}',  # Multiple o, O, 0 in sequence  
            r'[S5$]{3,}',  # Multiple S, 5, $ in sequence
            r'[B8]{3,}',   # Multiple B, 8 in sequence
            r'[G6]{3,}',   # Multiple G, 6 in sequence
            r'[Z2]{3,}',   # Multiple Z, 2 in sequence
            
            # Excessive punctuation
            r'[.,;:!?]{4,}',  # Multiple punctuation
            r'[-_=]{5,}',     # Long dash/underscore sequences
            r'[(){}[\]]{3,}', # Multiple brackets
            
            # Random character sequences
            r'[A-Za-z]{1}[^A-Za-z\s]{1}[A-Za-z]{1}[^A-Za-z\s]{1}', # Alternating letters/symbols
            r'\b[A-Za-z]{1,2}[0-9]{1,2}[A-Za-z]{1,2}\b',  # Mixed letter-number-letter
            
            # OCR artifacts
            r'[^\w\s.,;:!?()&@#$%^*+=|\\/<>[\]{}"\'`~-]{3,}',  # Special character sequences
        ]
    
    def _build_encoding_fixes(self) -> Dict[str, str]:
        """Comprehensive encoding fixes for OCR artifacts"""
        return {
            # Quote fixes - using proper string literals
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark  
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u201e': '"',  # Double low-9 quotation mark
            '\u201a': ',',  # Single low-9 quotation mark
            
            # Dash fixes
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2015': '--', # Horizontal bar
            
            # Ellipsis fixes
            '\u2026': '...', # Horizontal ellipsis
            '\u2030': '...', # Per mille sign
            
            # Currency and symbols
            '\u20ac': 'EUR', # Euro sign
            '\u00a3': 'GBP', # Pound sign
            '\u00a5': 'YEN', # Yen sign
            '\u2122': 'TM',  # Trade mark sign
            '\u00ae': '(R)', # Registered sign
            '\u00a9': '(C)', # Copyright sign
            '\u00b0': ' degrees', # Degree sign
            
            # Mathematical symbols
            '\u2212': '-',   # Minus sign
            '\u00d7': 'x',   # Multiplication sign
            '\u00f7': '/',   # Division sign
            '\u2264': '<=',  # Less-than or equal to
            '\u2265': '>=',  # Greater-than or equal to
            '\u2260': '!=',  # Not equal to
            '\u00b1': '+/-', # Plus-minus sign
            '\u221a': 'sqrt', # Square root
            '\u2192': '->',  # Rightwards arrow
            '\u2190': '<-',  # Leftwards arrow
            
            # Fractions
            '\u00bd': '1/2', # Vulgar fraction one half
            '\u2153': '1/3', # Vulgar fraction one third
            '\u00bc': '1/4', # Vulgar fraction one quarter
            '\u00be': '3/4', # Vulgar fraction three quarters
            '\u2155': '1/5', # Vulgar fraction one fifth
            '\u2159': '1/6', # Vulgar fraction one sixth
            '\u215b': '1/8', # Vulgar fraction one eighth
            
            # Remove obvious garbage
            '\ufffd': '',    # Replacement character
            '\u00a0': ' ',   # Non-breaking space
            '\u2000': ' ',   # En quad
            '\u2001': ' ',   # Em quad
            '\u2002': ' ',   # En space
            '\u2003': ' ',   # Em space
            '\u2004': ' ',   # Three-per-em space
            '\u2005': ' ',   # Four-per-em space
            '\u2006': ' ',   # Six-per-em space
            '\u2007': ' ',   # Figure space
            '\u2008': ' ',   # Punctuation space
            '\u2009': ' ',   # Thin space
            '\u200a': ' ',   # Hair space
            '\u200b': '',    # Zero width space
        }
    
    def _build_medical_vocabulary(self) -> set:
        """Build vocabulary of important medical/technical terms"""
        return {
            # Medical device terms
            'device', 'medical', 'equipment', 'instrument', 'apparatus',
            'monitor', 'sensor', 'probe', 'catheter', 'implant', 'scanner',
            'analyzer', 'detector', 'reader', 'controller', 'pump', 'valve',
            
            # Medical procedures/conditions
            'diagnosis', 'treatment', 'therapy', 'procedure', 'surgery',
            'examination', 'test', 'screening', 'monitoring', 'assessment',
            'patient', 'clinical', 'hospital', 'clinic', 'laboratory',
            
            # Technical terms
            'specification', 'requirement', 'parameter', 'configuration',
            'calibration', 'maintenance', 'operation', 'manual', 'guide',
            'instruction', 'warning', 'caution', 'notice', 'safety',
            
            # Measurements and units
            'voltage', 'current', 'frequency', 'temperature', 'pressure',
            'flow', 'volume', 'weight', 'height', 'diameter', 'length',
            'mm', 'cm', 'inch', 'volt', 'amp', 'watt', 'hertz', 'celsius',
            
            # Common form fields
            'name', 'model', 'serial', 'number', 'date', 'version',
            'manufacturer', 'supplier', 'contact', 'address', 'phone',
            'email', 'description', 'notes', 'comments', 'status',
        }
    
    def clean_ocr_text(self, text: str) -> str:
        """Comprehensive OCR text cleaning"""
        try:
            if not text or not text.strip():
                return ""
            
            original_length = len(text)
            logger.debug(f"🧹 Starting OCR text cleaning for {original_length} characters")
            
            # Step 1: Unicode normalization
            text = unicodedata.normalize('NFKD', text)
            
            # Step 2: Fix encoding issues
            for old, new in self.encoding_fixes.items():
                text = text.replace(old, new)
            
            # Step 3: Remove obvious OCR artifacts
            # Remove repeated patterns that are likely OCR errors
            text = re.sub(r'(.)\1{4,}', r'\1\1', text)  # Reduce excessive repetition
            
            # Step 4: Clean up spacing and layout
            # Fix line breaks and spacing
            text = re.sub(r'\r\n', '\n', text)  # Normalize line endings
            text = re.sub(r'\r', '\n', text)
            text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
            text = re.sub(r'\n[ \t]+', '\n', text)  # Remove leading whitespace
            text = re.sub(r'[ \t]+\n', '\n', text)  # Remove trailing whitespace
            text = re.sub(r'\n{3,}', '\n\n', text)  # Limit consecutive newlines
            
            # Step 5: Fix common OCR misreadings
            # Common letter confusions
            text = self._fix_common_ocr_errors(text)
            
            # Step 6: Remove lines that are likely garbage
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if self._is_line_valid(line):
                    cleaned_lines.append(line)
                else:
                    logger.debug(f"🗑️ Removing invalid line: {line[:50]}...")
            
            # Step 7: Rejoin and final cleanup
            text = '\n'.join(cleaned_lines)
            text = text.strip()
            
            # Step 8: Remove isolated artifacts
            text = re.sub(r'\b[^\w\s.,;:!?()-]{1,2}\b', ' ', text)  # Isolated symbols
            text = re.sub(r'\s+', ' ', text)  # Clean up spaces again
            
            cleaned_length = len(text)
            reduction_pct = ((original_length - cleaned_length) / original_length * 100) if original_length > 0 else 0
            
            logger.debug(f"✅ OCR cleaning complete: {original_length} → {cleaned_length} chars ({reduction_pct:.1f}% reduction)")
            
            return text
            
        except Exception as e:
            logger.warning(f"⚠️ OCR text cleaning failed: {e}")
            return text  # Return original if cleaning fails
    
    def _fix_common_ocr_errors(self, text: str) -> str:
        """Fix common OCR character misreadings"""
        
        # Common OCR substitutions in medical/technical contexts
        ocr_fixes = {
            # Number/letter confusions (context-sensitive)
            r'\b0(?=\w)': 'O',  # 0 at start of word -> O
            r'\b1(?=[a-z])': 'l',  # 1 before lowercase -> l
            r'\bS(?=\d)': '5',  # S before digit -> 5
            r'\bG(?=\d)': '6',  # G before digit -> 6
            r'\bZ(?=\d)': '2',  # Z before digit -> 2
            r'\bB(?=\d)': '8',  # B before digit -> 8
            
            # Common word fixes
            r'\btlle\b': 'the',
            r'\bwlth\b': 'with',
            r'\bfrom\b': 'from',
            r'\btllis\b': 'this',
            r'\bwllen\b': 'when',
            r'\bwllere\b': 'where',
            r'\bpatlem\b': 'patient',
            r'\bdevlce\b': 'device',
            r'\bmedicaI\b': 'medical',
            r'\bequlpment\b': 'equipment',
        }
        
        for pattern, replacement in ocr_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _is_line_valid(self, line: str) -> bool:
        """Check if a line is valid and not garbage"""
        if not line or len(line.strip()) < 2:
            return False
        
        # Check for gibberish patterns
        for pattern in self.gibberish_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return False
        
        # Check character composition
        alpha_chars = sum(1 for c in line if c.isalpha())
        total_chars = len(line)
        
        if total_chars > 0:
            alpha_ratio = alpha_chars / total_chars
            
            # Lines should have reasonable amount of letters
            if alpha_ratio < 0.3 and total_chars > 10:  # Too few letters for long lines
                return False
            
            # Check for excessive special characters
            special_chars = sum(1 for c in line if not c.isalnum() and c not in ' .,;:!?()-')
            if special_chars / total_chars > 0.5:  # Too many special chars
                return False
        
        # Check if line contains meaningful words
        words = re.findall(r'\b[a-zA-Z]{2,}\b', line)
        if len(words) == 0 and len(line) > 5:  # No real words in non-trivial line
            return False
        
        # Allow lines with medical/technical terms
        line_lower = line.lower()
        if any(term in line_lower for term in self.medical_terms):
            return True
        
        # Check for reasonable word structure
        if words:
            avg_word_length = sum(len(word) for word in words) / len(words)
            if avg_word_length < 1.5 or avg_word_length > 20:  # Unreasonable word lengths
                return False
        
        return True
    
    def assess_chunk_quality(self, chunk_text: str) -> float:
        """Assess the quality of a text chunk (0.0 to 1.0)"""
        try:
            if not chunk_text or not chunk_text.strip():
                return 0.0
            
            quality_score = 1.0
            text_length = len(chunk_text)
            
            # Factor 1: Encoding artifact detection (enhanced)
            artifact_count = 0
            for pattern in self.gibberish_patterns:
                artifact_count += len(re.findall(pattern, chunk_text, re.IGNORECASE))
            
            if artifact_count > 0:
                artifact_penalty = min(0.4, artifact_count * 0.1)
                quality_score -= artifact_penalty
                logger.debug(f"📉 Quality penalty for {artifact_count} artifacts: -{artifact_penalty:.2f}")
            
            # Factor 2: Character composition
            alpha_chars = sum(1 for c in chunk_text if c.isalpha())
            digit_chars = sum(1 for c in chunk_text if c.isdigit())
            space_chars = sum(1 for c in chunk_text if c.isspace())
            punct_chars = sum(1 for c in chunk_text if c in string.punctuation)
            other_chars = text_length - alpha_chars - digit_chars - space_chars - punct_chars
            
            if text_length > 0:
                alpha_ratio = alpha_chars / text_length
                other_ratio = other_chars / text_length
                
                # Good text should be mostly alphabetic
                if alpha_ratio < 0.4:
                    quality_score -= 0.2
                    logger.debug(f"📉 Quality penalty for low alpha ratio: {alpha_ratio:.2f}")
                
                # Too many unrecognized characters is bad
                if other_ratio > 0.1:
                    quality_score -= 0.3
                    logger.debug(f"📉 Quality penalty for unknown chars: {other_ratio:.2f}")
            
            # Factor 3: Word structure analysis
            words = re.findall(r'\b[a-zA-Z]{2,}\b', chunk_text)
            if words:
                avg_word_length = sum(len(word) for word in words) / len(words)
                
                # Reasonable word lengths (2-15 characters)
                if avg_word_length < 2 or avg_word_length > 15:
                    quality_score -= 0.15
                    logger.debug(f"📉 Quality penalty for word length: {avg_word_length:.1f}")
                
                # Check for dictionary-like words vs gibberish
                common_patterns = sum(1 for word in words if len(word) >= 3)
                if len(words) > 0:
                    pattern_ratio = common_patterns / len(words)
                    if pattern_ratio < 0.6:
                        quality_score -= 0.1
                        logger.debug(f"📉 Quality penalty for pattern ratio: {pattern_ratio:.2f}")
            
            # Factor 4: Sentence structure
            sentences = re.split(r'[.!?]+', chunk_text)
            meaningful_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
            
            if meaningful_sentences:
                avg_sentence_length = sum(len(s.split()) for s in meaningful_sentences) / len(meaningful_sentences)
                
                # Reasonable sentence lengths (3-30 words)
                if avg_sentence_length < 3 or avg_sentence_length > 30:
                    quality_score -= 0.1
                    logger.debug(f"📉 Quality penalty for sentence length: {avg_sentence_length:.1f}")
            
            # Factor 5: Medical/technical content bonus
            chunk_lower = chunk_text.lower()
            technical_terms_found = sum(1 for term in self.medical_terms if term in chunk_lower)
            if technical_terms_found > 0:
                bonus = min(0.1, technical_terms_found * 0.02)
                quality_score += bonus
                logger.debug(f"📈 Quality bonus for technical terms: +{bonus:.2f}")
            
            # Factor 6: Form field detection bonus
            if re.search(r'[A-Za-z\s]+:\s*(?:\w|$)', chunk_text):
                quality_score += 0.05
                logger.debug("📈 Quality bonus for form fields: +0.05")
            
            # Factor 7: Structured data bonus
            if '[TABLE DATA]' in chunk_text or '|' in chunk_text:
                quality_score += 0.05
                logger.debug("📈 Quality bonus for structured data: +0.05")
            
            final_score = max(0.0, min(1.0, quality_score))
            logger.debug(f"📊 Final chunk quality score: {final_score:.2f}")
            
            return final_score
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to assess chunk quality: {e}")
            return 0.5  # Default to medium quality
    
    def should_include_chunk(self, chunk_text: str, min_quality: float = None) -> bool:
        """Determine if a chunk should be included based on quality with CSV awareness"""
        if min_quality is None:
            min_quality = self.min_chunk_quality
            
        # Special handling for CSV content
        if self._is_csv_content(chunk_text):
            # More lenient for CSV records but stricter for completeness
            if "[CSV_RECORD_" in chunk_text:
                # Person records need higher completeness
                field_count = chunk_text.count(':')
                filled_fields = len([line for line in chunk_text.split('\n') 
                                   if ':' in line and not any(empty in line for empty in ['[EMPTY_FIELD]', '[NEEDS_FILLING]'])])
                
                if field_count > 0:
                    completeness = filled_fields / field_count
                    if completeness < 0.3:  # Less than 30% filled
                        logger.info(f"🚫 Excluding incomplete CSV record (completeness: {completeness:.2f}): {chunk_text[:100]}...")
                        return False
                
            # Use standard quality for other CSV content
            quality = self.assess_chunk_quality(chunk_text)
            
            # Lower threshold for CSV content but ensure minimum standards
            csv_threshold = max(0.5, min_quality - 0.1)  # 10% more lenient
            include = quality >= csv_threshold
        else:
            # Standard processing for non-CSV content
            quality = self.assess_chunk_quality(chunk_text)
            include = quality >= min_quality
        
        if not include:
            logger.info(f"🚫 Excluding low-quality chunk (score: {quality:.2f}): {chunk_text[:100]}...")
        else:
            logger.debug(f"✅ Including chunk (score: {quality:.2f})")
            
        return include

    def _is_csv_content(self, text: str) -> bool:
        """Enhanced CSV content detection"""
        csv_indicators = [
            "[CSV_HEADER]", "[CSV_RECORD_", "[COLUMN_", "[PERSON_RECORD_",
            "Dataset contains", "records with", "columns",
            "Complete Person Data Record", "[AVAILABLE_DATA]", "[RECORD_STATUS]"
        ]
        return any(indicator in text for indicator in csv_indicators)

    def enhance_chunk_content(self, chunk_text: str) -> str:
        """Enhance chunk content for better embedding and search with CSV awareness"""
        try:
            # Clean the text first
            enhanced_text = self.clean_ocr_text(chunk_text)
            
            # Special enhancement for CSV content
            if self._is_csv_content(enhanced_text):
                enhanced_text = self._enhance_csv_chunk_content(enhanced_text)
            
            # Add context markers for better search
            # Detect and mark form fields
            enhanced_text = re.sub(
                r'^([A-Za-z][A-Za-z\s]*):(\s*)(.*?)$',
                r'\1: \3',  # Clean up field formatting
                enhanced_text,
                flags=re.MULTILINE
            )
            
            # Enhance table data formatting
            if '[TABLE DATA]' in enhanced_text:
                # Clean up table formatting
                enhanced_text = re.sub(r'\s*\|\s*', ' | ', enhanced_text)
                enhanced_text = re.sub(r'\|\s*\|', '|', enhanced_text)
            
            # Add spacing around important punctuation
            enhanced_text = re.sub(r'([.!?])([A-Z])', r'\1 \2', enhanced_text)
            
            # Final cleanup
            enhanced_text = re.sub(r'\s+', ' ', enhanced_text)
            enhanced_text = enhanced_text.strip()
            
            return enhanced_text
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to enhance chunk content: {e}")
            return chunk_text

    def _enhance_csv_chunk_content(self, chunk_text: str) -> str:
        """Enhance CSV chunk content specifically for better template filling"""
        try:
            enhanced = chunk_text
            
            # Standardize field-value formatting
            lines = enhanced.split('\n')
            enhanced_lines = []
            
            for line in lines:
                if ':' in line and not line.startswith('['):
                    field, value = line.split(':', 1)
                    field = field.strip()
                    value = value.strip()
                    
                    # Standardize field names for better matching
                    standardized_field = self._standardize_field_name(field)
                    
                    # Enhance value formatting
                    if value in ['[EMPTY_FIELD]', '[NEEDS_FILLING]', '']:
                        enhanced_line = f"{standardized_field}: [TEMPLATE_FIELD_EMPTY]"
                    else:
                        # Clean and format the value
                        cleaned_value = self.clean_ocr_text(value)
                        enhanced_line = f"{standardized_field}: {cleaned_value}"
                    
                    enhanced_lines.append(enhanced_line)
                else:
                    enhanced_lines.append(line)
            
            enhanced = '\n'.join(enhanced_lines)
            
            # Add template filling hints
            if '[CSV_RECORD_' in enhanced:
                enhanced += '\n[TEMPLATE_READY] This record is ready for template filling and form population.'
            
            return enhanced
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to enhance CSV chunk content: {e}")
            return chunk_text

    def _standardize_field_name(self, field_name: str) -> str:
        """Standardize field names for better template matching"""
        try:
            field_lower = field_name.lower().strip()
            
            # Common field name mappings
            field_mappings = {
                'device name': 'Device Name',
                'device_name': 'Device Name',
                'product name': 'Device Name',
                'equipment name': 'Device Name',
                
                'model': 'Model Number',
                'model number': 'Model Number',
                'model_number': 'Model Number',
                'model no': 'Model Number',
                
                'serial': 'Serial Number',
                'serial number': 'Serial Number',
                'serial_number': 'Serial Number',
                'serial no': 'Serial Number',
                
                'manufacturer': 'Manufacturer',
                'company': 'Manufacturer',
                'vendor': 'Manufacturer',
                'supplier': 'Manufacturer',
                
                'part number': 'Part Number',
                'part_number': 'Part Number',
                'part no': 'Part Number',
                'catalog number': 'Part Number',
                
                'version': 'Version',
                'revision': 'Version',
                'software version': 'Version',
                
                'date': 'Date',
                'manufacturing date': 'Manufacturing Date',
                'production date': 'Manufacturing Date',
                
                'description': 'Description',
                'details': 'Description',
                'notes': 'Description',
                'comments': 'Description'
            }
            
            return field_mappings.get(field_lower, field_name.title())
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to standardize field name: {e}")
            return field_name

# Create global instance
enhanced_text_processor = EnhancedTextProcessor()


# Create global instance
enhanced_text_processor = EnhancedTextProcessor()
