import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import logging
import re
import json
import hashlib
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        # SECURITY FIX: Use environment variable instead of hardcoded API key
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.available = False
        
        # Debug logging to check environment variable loading
        if self.api_key:
            logger.info(f"✅ Google API key loaded: {self.api_key[:8]}...{self.api_key[-4:] if len(self.api_key) > 8 else '***'}")
        else:
            logger.warning("❌ Google API key not found in environment variables")
            logger.info("📝 Checking environment variables: GOOGLE_API_KEY and GEMINI_API_KEY")
        
        if self.api_key and self.api_key != "dummy_key_for_testing":
            try:
                genai.configure(api_key=self.api_key)
                self.available = True
                logger.info("✅ Google Gemini API configured successfully")
            except Exception as e:
                logger.warning(f"❌ Failed to configure Google Gemini API: {e}")
                logger.info("📝 Gemini service will operate in fallback mode")
        else:
            logger.warning("❌ Google API key not configured")
            logger.info("📝 Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable")
            logger.info("📝 Gemini service will operate in fallback mode")
            
        self.embedding_model = "models/embedding-001"
        self.generation_model = "gemini-1.5-flash"
    
    def _generate_fallback_embedding(self, text: str) -> List[float]:
        """Generate a simple hash-based embedding as fallback"""
        try:
            # Create a deterministic embedding based on text hash
            text_hash = hashlib.md5(text.encode()).hexdigest()
            
            # Convert hash to a 1024-dimensional vector (to match Pinecone index)
            embedding_dim = 1024
            seed = int(text_hash[:8], 16)  # Use first 8 characters as seed
            np.random.seed(seed)
            
            # Generate normalized random vector
            embedding = np.random.normal(0, 1, embedding_dim)
            embedding = embedding / np.linalg.norm(embedding)  # Normalize
            
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Failed to generate fallback embedding: {e}")
            # Return zero vector as last resort
            return [0.0] * 1024
    
    def _pad_or_truncate_embedding(self, embedding: List[float], target_dim: int = 1024) -> List[float]:
        """Pad or truncate embedding to match target dimension"""
        try:
            if len(embedding) == target_dim:
                return embedding
            elif len(embedding) < target_dim:
                # Pad with zeros
                padding = [0.0] * (target_dim - len(embedding))
                return embedding + padding
            else:
                # Truncate to target dimension
                return embedding[:target_dim]
        except Exception as e:
            logger.error(f"❌ Failed to pad/truncate embedding: {e}")
            return [0.0] * target_dim
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embeddings using Gemini or fallback"""
        try:
            if not self.available:
                # Fallback: Generate a simple hash-based embedding
                logger.warning("📝 Using fallback embedding (Google API not available)")
                return self._generate_fallback_embedding(text)
            
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            
            # Ensure the embedding is 1024-dimensional to match Pinecone index
            embedding = result['embedding']
            return self._pad_or_truncate_embedding(embedding, 1024)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            # Fallback on error
            logger.warning("📝 Falling back to simple embedding")
            return self._generate_fallback_embedding(text)
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            embeddings = []
            for text in texts:
                embedding = await self.get_embedding(text)
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Failed to generate batch embeddings: {e}")
            raise
    
    async def generate_response(
        self, 
        prompt: str, 
        context: List[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.05  # ENHANCED: Much lower for factual accuracy in document filling
    ) -> str:
        """Generate response using Gemini with enhanced accuracy and fact-based approach"""
        try:
            if not self.available:
                # Fallback response when API is not available
                logger.warning("📝 Using fallback response (Google API not available)")
                if context:
                    return f"I have access to {len(context)} document chunks, but I cannot generate detailed responses without the Google Gemini API. Please configure the GOOGLE_API_KEY in your .env file."
                else:
                    return "I cannot generate responses without the Google Gemini API. Please configure the GOOGLE_API_KEY in your .env file."
            
            model = genai.GenerativeModel(self.generation_model)
            
            # Build the full prompt for clean, simple responses
            if context:
                # When context is provided separately (legacy mode)
                context_text = "\n\n".join(context)
                full_prompt = f"""Answer the user's question using only the information provided in the documents below. Give a clear, direct answer.

DOCUMENTS:
{context_text}

QUESTION: {prompt}

INSTRUCTIONS:
1. Provide a direct, helpful answer using only the information in the documents
2. Write in plain, simple language 
3. If the information isn't available, simply say "I don't have that information in the documents"
4. Don't include chunk numbers, confidence scores, or technical citations
5. Focus on being helpful and clear

ANSWER:"""
            else:
                # When context is already included in the prompt (preferred mode)
                full_prompt = prompt
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,  # Very low temperature for factual accuracy
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Failed to generate response: {e}")
            # Fallback response on error
            return "I encountered an error generating the response. Please check the logs and ensure the Google API key is properly configured."
    
    def _filter_template_content(self, template_content: str) -> str:
        """Filter out table of contents, headers, footers, and other unwanted sections"""
        try:
            lines = template_content.split('\n')
            filtered_lines = []
            skip_section = False
            in_main_content = False
            
            # Patterns to identify sections to skip
            toc_patterns = [
                # Common TOC headers
                r'table\s+of\s+contents',
                r'contents',
                r'index',
                r'table\s+des\s+mati[eè]res',  # French TOC
                r's\.\s*no\.\s*contents\s*page\s*no',  # Table headers like your image
                r's\.\s*no\.',  # Serial number column header
                r'page\s*no\.',  # Page number column header
                
                # TOC entry patterns with dots/leaders
                r'^\d+\.\s*.+\.\.\.\.\s*\d+$',  # "1. Section Name ........ 5"
                r'^\d+\.\d+\s*.+\.\.\.\.\s*\d+$',  # "1.1 Subsection ........ 5"
                r'^[A-Z\s]+\s+\.\.\.\.\s*\d+$',  # "SECTION NAME ........ 5"
                r'^\w+.*\.{3,}\s*\d+\s*$',  # "Section name.........5"
                
                # TOC entries with tabs or spaces to page numbers
                r'^\d+\.\s*.+\s+\d+\s*$',  # "1. Section Name    5"
                r'^\d+\.\d+\s*.+\s+\d+\s*$',  # "1.1 Subsection    5"
                r'^[A-Z][A-Za-z\s]+\s+\d+\s*$',  # "Section Name    5"
                
                # Your specific TOC format from image
                r'^\d+\s+[A-Za-z\s,&\-().]+\s*$',  # "1   Executive Summary"
                r'^\d+\.\d+\s+[A-Za-z\s,&\-().]+\s*$',  # "1.1 Introduction & Description"
                r'^\d+\s+[A-Za-z\s,&\-().]+$',  # TOC entries without page numbers
                r'^\d+\.\d+\s+[A-Za-z\s,&\-().]+$',  # Sub-entries without page numbers
                
                # TOC table structure patterns
                r'^\|\s*\d+\s*\|.*\|.*\|$',  # Table format "|1|content|page|"
                r'^\s*\|\s*\d+\s*\|',  # Start of table row with number
                r'\|\s*\d+\s*\|$',  # End of table row with page number
                
                # Page number references
                r'page\s+\d+',
                r'^\s*\d+\s*$',  # Standalone page numbers
                r'^\s*-\s*\d+\s*-\s*$',  # Page numbers like "- 5 -"
                
                # Common TOC continuation patterns
                r'\.{3,}',  # Three or more dots (leaders)
                r'^_{3,}$',   # Three or more underscores ALONE on a line (not after colons)
                r'-{3,}',   # Three or more dashes
                
                # Section references
                r'see\s+section\s+\d+',
                r'section\s+\d+\.\d+',
                
                # Specific entries from your TOC image
                r'executive\s+summary',
                r'introduction\s*&\s*description\s*of\s*medical\s*device',
                r'sterilization\s*of\s*device',
                r'risk\s*management\s*plan',
                r'clinical\s*evidence\s*and\s*evaluation',
                r'regulatory\s*status',
                r'design\s*examination\s*certificate',
                r'device\s*description\s*and\s*product\s*specification',
                r'design\s*and\s*manufacturing\s*information',
                r'essential\s*principles\s*checklist',
                r'verification\s*and\s*validation',
                r'biocompatibility',
                r'medicinal\s*substances',
                r'biological\s*safety',
                r'software\s*verification',
                r'annual\s*studies',
            ]
            
            header_footer_patterns = [
                # Common headers/footers
                r'header',
                r'footer',
                r'page\s+\d+\s+of\s+\d+',
                r'^\s*\d+\s*$',  # Page numbers alone
                r'^\s*-\s*\d+\s*-\s*$',  # Page numbers like "- 5 -"
                
                # Document metadata
                r'confidential',
                r'proprietary',
                r'draft',
                r'revision\s+\d+',
                r'version\s+\d+',
                r'©\s*\d{4}',  # Copyright
                r'copyright',
                
                # Company/document info often in headers/footers
                r'^\s*[A-Z][A-Za-z\s]+\s+(Inc|Corp|LLC|Ltd)\.?\s*$',
                r'document\s+control',
                r'effective\s+date',
                r'review\s+date',
            ]
            
            # Content start indicators (marks beginning of main content)
            content_start_patterns = [
                r'device\s+master\s+file',
                r'section\s+\d+',
                r'introduction',
                r'background',
                r'purpose',
                r'scope',
                r'general\s+information',
                r'device\s+information',
                r'product\s+information',
                r'generic\s+name',        # Start when we see actual fields
                r'manufacturer',          # Start when we see actual fields
                r'model\s+no',           # Start when we see actual fields
                r'document\s+no',        # Start when we see actual fields
            ]
            
            for i, line in enumerate(lines):
                line_lower = line.lower().strip()
                original_line = line.strip()
                
                # Skip empty lines initially
                if not line_lower:
                    if in_main_content:
                        filtered_lines.append(original_line)
                    continue
                
                # Check if we should start including content
                if not in_main_content:
                    for pattern in content_start_patterns:
                        if re.search(pattern, line_lower):
                            in_main_content = True
                            break
                
                # Skip table of contents
                is_toc_line = False
                for pattern in toc_patterns:
                    if re.search(pattern, line_lower):
                        is_toc_line = True
                        break
                
                # Skip headers and footers
                is_header_footer = False
                for pattern in header_footer_patterns:
                    if re.search(pattern, line_lower):
                        is_header_footer = True
                        break
                
                # Skip lines that look like TOC entries (number dots text dots number)
                if re.match(r'^\s*\d+\.?\s*.+\s*\.{3,}\s*\d+\s*$', original_line):
                    is_toc_line = True
                
                # Additional TOC pattern checks
                if re.match(r'^\s*\d+\.\d+\s*.+\s+\d+\s*$', original_line):  # "1.1 Section   5"
                    is_toc_line = True
                
                if re.match(r'^\s*[A-Z][A-Za-z\s]+\s+\d+\s*$', original_line):  # "SECTION NAME   5"
                    is_toc_line = True
                
                # Skip very short lines that are likely formatting, but preserve lines with field indicators
                if len(original_line) < 3:
                    if not any(c in original_line for c in ':[]{}'):
                        if not in_main_content:
                            continue
                
                # Always include lines that have fillable field patterns, even if not in main content yet
                has_fillable_pattern = any([
                    ':' in original_line and any(marker in original_line for marker in ['[', '_', '{', 'MISSING']),
                    re.search(r'.*:\s*_+', original_line),  # Field with underscores
                    re.search(r'.*:\s*\[.*\]', original_line),  # Field with brackets
                    re.search(r'.*:\s*\{.*\}', original_line),  # Field with braces
                    '__/__/____' in original_line,  # Date fields
                ])
                
                if has_fillable_pattern and not is_toc_line and not is_header_footer:
                    filtered_lines.append(original_line)
                    in_main_content = True  # Start main content when we see fillable fields
                    continue
                
                # Include line if it's not in a section to skip
                if in_main_content and not is_toc_line and not is_header_footer:
                    filtered_lines.append(original_line)
            
            filtered_content = '\n'.join(filtered_lines)
            
            # Log the filtering results
            original_lines = len(lines)
            filtered_line_count = len(filtered_lines)
            logger.info(f"📝 Content filtering: {original_lines} → {filtered_line_count} lines (removed {original_lines - filtered_line_count} lines)")
            
            return filtered_content
            
        except Exception as e:
            logger.error(f"❌ Failed to filter template content: {e}")
            return template_content  # Return original if filtering fails

    async def extract_template_fields(self, template_content: str) -> List[str]:
        """Extract placeholder fields from template content, focusing on main content only"""
        try:
            # First filter out unwanted sections
            filtered_content = self._filter_template_content(template_content)
            
            prompt = f"""Analyze the following document template and extract ONLY the placeholder fields that need to be filled.

FOCUS ONLY ON:
1. Fields ending with ":" that need answers - like "Generic name:", "Model Name:", "Document No:"
2. [Missing] or similar placeholder markers that need to be filled
3. Underlines _____ that represent blank fields

IGNORE:
- Table of contents entries
- Headers and footers
- Page numbers
- Section titles that don't need filling
- Navigation elements

Template content:
{filtered_content}

Return only a JSON list of field names. For fields ending with ":", use the text before the colon.
Example: ["Generic name", "Model Name", "Document No", "Missing_1"]"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(prompt)
            
            # Parse the response to extract field names
            try:
                fields = json.loads(response.text)
                return fields if isinstance(fields, list) else []
            except json.JSONDecodeError:
                # Fallback: extract manually using regex
                fields = set()
                
                # Pattern 1: Standard placeholders {field}, [field], <field>
                standard_patterns = [
                    r'\{([^}]+)\}',  # {field}
                    r'\[([^\]]+)\]',  # [field] 
                    r'<([^>]+)>',    # <field>
                ]
                
                for pattern in standard_patterns:
                    matches = re.findall(pattern, filtered_content)
                    fields.update(matches)
                
                # Pattern 2: [Missing] occurrences
                missing_count = len(re.findall(r'\[Missing\]', filtered_content, re.IGNORECASE))
                for i in range(1, missing_count + 1):
                    fields.add(f"Missing_{i}")
                
                # Pattern 3: Fields ending with ":" (form fields)
                # Look for lines that end with ":" and are likely field labels
                lines = filtered_content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.endswith(':') and len(line) > 1:
                        # Extract the field name (remove numbers, special chars at start)
                        field_name = re.sub(r'^[\d\.\)\s]+', '', line[:-1]).strip()
                        if field_name and len(field_name) > 2:  # Avoid single letters
                            fields.add(field_name)
                
                return list(fields)
            
        except Exception as e:
            logger.error(f"❌ Failed to extract template fields: {e}")
            return []
    
    async def generate_field_questions(self, field_name: str, field_context: str) -> List[str]:
        """Generate targeted questions for a specific field to improve search"""
        try:
            if not self.available:
                # Enhanced fallback questions when API is not available
                return self._generate_fallback_questions(field_name, field_context)
            
            # Analyze field name to generate better questions
            field_type = self._classify_field_type(field_name, field_context)
            
            prompt = f"""Generate exactly 5 targeted search questions to find comprehensive information for filling the template field "{field_name}".

Field Type: {field_type}
Context from template: {field_context}

The questions should be specific, comprehensive, and likely to find ALL relevant information in a document database.
Focus on different ways this information might be expressed in technical documents.
Generate questions that will capture variations, synonyms, and related information.

Field-specific guidance:
- For names: Ask about "generic name", "device name", "product name", "title", "designation"
- For numbers: Ask about "document number", "model number", "serial number", "reference number", "ID", "code"
- For dates: Ask about "date", "when", "time", "created", "issued", "approved"
- For manufacturers: Ask about "manufacturer", "company", "made by", "producer", "supplier"
- For models: Ask about "model", "version", "type", "variant", "series"
- For signatures: Ask about "signed by", "authorized by", "approved by", "responsible person"

Examples for "Document No":
- What is the document number?
- Find document identification number
- What is the reference number?
- What is the document ID or code?
- Find document reference information

Examples for "Generic Name":
- What is the generic name of the device?
- What is the product name?
- What type of device is this?
- What is the device designation?
- Find product identification information

Examples for "Manufacturer":
- Who is the manufacturer?
- What company makes this device?
- Who manufactured this product?
- Find manufacturer information
- What company produced this device?

Return only a JSON list with exactly 5 comprehensive questions: ["question1", "question2", "question3", "question4", "question5"]"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=400,
                    temperature=0.3,  # Slightly higher for more variety in questions
                )
            )
            
            try:
                import json
                questions = json.loads(response.text)
                if isinstance(questions, list) and len(questions) >= 3:
                    return questions[:5]  # Ensure max 5 questions
                else:
                    return self._generate_fallback_questions(field_name, field_context)
            except json.JSONDecodeError:
                # Fallback: extract questions manually
                lines = response.text.split('\n')
                questions = []
                for line in lines:
                    line = line.strip(' -"\'[]')
                    if line and '?' in line and len(line) > 10:
                        questions.append(line)
                
                if len(questions) >= 3:
                    return questions[:5]
                else:
                    return self._generate_fallback_questions(field_name, field_context)
                
        except Exception as e:
            logger.error(f"❌ Failed to generate questions for field {field_name}: {e}")
            return self._generate_fallback_questions(field_name, field_context)
    
    def _classify_field_type(self, field_name: str, context: str) -> str:
        """Classify the type of field to generate better questions"""
        field_lower = field_name.lower()
        context_lower = context.lower()
        
        # Classification based on field name
        if any(term in field_lower for term in ['name', 'title']):
            if 'generic' in field_lower or 'product' in field_lower:
                return "product_name"
            elif 'company' in field_lower or 'manufacturer' in field_lower:
                return "company_name"
            else:
                return "general_name"
        elif any(term in field_lower for term in ['no', 'number', '#', 'num']):
            if 'document' in field_lower or 'doc' in field_lower:
                return "document_number"
            elif 'model' in field_lower:
                return "model_number"
            elif 'serial' in field_lower:
                return "serial_number"
            else:
                return "general_number"
        elif any(term in field_lower for term in ['date', 'time', 'when']):
            return "date"
        elif any(term in field_lower for term in ['manufacturer', 'company', 'maker']):
            return "manufacturer"
        elif any(term in field_lower for term in ['model', 'version', 'type']):
            return "model"
        elif any(term in field_lower for term in ['signature', 'signed', 'by']):
            return "signature"
        elif any(term in field_lower for term in ['address', 'location']):
            return "address"
        elif any(term in field_lower for term in ['phone', 'tel', 'mobile']):
            return "phone"
        elif any(term in field_lower for term in ['email', 'mail']):
            return "email"
        else:
            return "general"
    
    def _generate_fallback_questions(self, field_name: str, field_context: str) -> List[str]:
        """Generate fallback questions when AI is not available"""
        field_type = self._classify_field_type(field_name, field_context)
        field_lower = field_name.lower()
        
        questions = []
        
        # Generate questions based on field type
        if field_type == "product_name":
            questions = [
                f"What is the generic name of the device?",
                f"What is the product name?",
                f"What type of device is this?",
                f"What is the device designation?",
                f"Find product identification information"
            ]
        elif field_type == "company_name" or field_type == "manufacturer":
            questions = [
                f"Who is the manufacturer?",
                f"What company makes this device?",
                f"Who manufactured this product?",
                f"Find manufacturer information",
                f"What company produced this device?"
            ]
        elif field_type == "document_number":
            questions = [
                f"What is the document number?",
                f"Find document identification number",
                f"What is the reference number?",
                f"What is the document ID or code?",
                f"Find document reference information"
            ]
        elif field_type == "model_number" or field_type == "model":
            questions = [
                f"What is the model number?",
                f"Find model information",
                f"What are the device models?",
                f"What is the model designation?",
                f"Find product model details"
            ]
        elif field_type == "serial_number":
            questions = [
                f"What is the serial number?",
                f"Find serial information",
                f"What is the device serial?",
                f"Find serial identification",
                f"What is the unit serial number?"
            ]
        elif field_type == "date":
            questions = [
                f"What is the date?",
                f"When was this created?",
                f"Find date information",
                f"What is the creation date?",
                f"When was this issued or approved?"
            ]
        elif field_type == "signature":
            questions = [
                f"Who signed this?",
                f"Find signature information",
                f"Who authorized this?",
                f"Who approved this document?",
                f"Find responsible person information"
            ]
        elif field_type == "address":
            questions = [
                f"What is the address?",
                f"Find location information",
                f"Where is this located?",
                f"What is the company address?",
                f"Find address details"
            ]
        else:
            # Generic questions
            questions = [
                f"What is the {field_name}?",
                f"Find {field_name} information",
                f"Find information about {field_name}",
                f"What are the details for {field_name}?",
                f"Find {field_name} specifications or data"
            ]
        
        return questions[:5]  # Return up to 5 questions
    
    async def fill_template_field_enhanced(
        self, 
        field_name: str,
        field_context: str,
        context_docs: List[str],
        questions: List[str],
        device_id: str
    ) -> Optional[str]:
        """Enhanced template field filling with comprehensive context analysis and extreme accuracy"""
        try:
            if not self.available:
                # Enhanced fallback when API is not available
                return self._fallback_field_extraction(field_name, field_context, context_docs)
            
            # ENHANCED: Use more context documents for comprehensive analysis
            context_text = "\n\n".join(context_docs[:15])  # Increased from 8 to 15 for maximum coverage
            questions_text = "\n".join([f"- {q}" for q in questions])
            
            # Classify field type for specialized handling
            field_type = self._classify_field_type(field_name, field_context)
            
            # Create specialized instructions based on field type
            field_instructions = self._get_field_instructions(field_type, field_name)
            
            prompt = f"""You are an expert document analysis system specialized in extracting precise, factual information for template filling. Your task is to find the EXACT information for the field "{field_name}" from the comprehensive document context provided.

Field to fill: "{field_name}"
Field type: {field_type}
Template context: {field_context}

{field_instructions}

COMPREHENSIVE SEARCH QUESTIONS USED (these guided the document retrieval):
{questions_text}

COMPREHENSIVE DOCUMENT CONTEXT - ANALYZE ALL SECTIONS THOROUGHLY:
{context_text}

Device ID: {device_id}

CRITICAL ANALYSIS INSTRUCTIONS FOR MAXIMUM ACCURACY:
1. 🔍 EXHAUSTIVELY examine ALL document contexts - information could be anywhere
2. 🎯 Look for EXACT MATCHES first, then closely related information
3. 📊 Cross-reference information across multiple document sections
4. ✅ Prioritize the MOST SPECIFIC and DETAILED information available
5. 🔄 If multiple sources contain the same field, use the most authoritative/detailed version
6. ⚖️ If conflicting information exists, use the most recent or official source
7. 📝 Extract ONLY the specific value that should fill this field - no extra text
8. 🚫 Return ONLY the field value - no explanations, prefixes, or additional context
9. ❌ If you cannot find relevant information after thorough analysis, return "NOT_FOUND"
10. 🎯 Be extremely precise and concise - extract the exact data needed

FIELD-SPECIFIC EXTRACTION RULES:
- For NAME fields: Extract only the name itself (e.g., "Pulse Oximeter" not "Generic name: Pulse Oximeter")
- For NUMBER fields: Extract only the number/code (e.g., "OPO-101" not "Model No: OPO-101")
- For DATE fields: Extract only the date (e.g., "03/15/2024" not "Date: 03/15/2024")
- For COMPANY fields: Extract only the company name (e.g., "ACME Corp" not "Manufacturer: ACME Corp")

IMPORTANT: This is for critical document filling - accuracy is paramount. Analyze thoroughly but respond with only the precise value needed.

EXTRACTED VALUE (based on comprehensive analysis):"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=200,
                    temperature=0.01,  # ENHANCED: Extremely low temperature for maximum precision in document filling
                )
            )
            
            result = response.text.strip()
            
            # Clean up the result based on field type
            result = self._clean_field_result(result, field_type, field_name)
            
            return None if result == "NOT_FOUND" or not result else result
            
        except Exception as e:
            logger.error(f"❌ Failed to fill template field {field_name}: {e}")
            return self._fallback_field_extraction(field_name, field_context, context_docs)
    
    def _get_field_instructions(self, field_type: str, field_name: str) -> str:
        """Get specialized instructions for different field types"""
        instructions = {
            "product_name": """
Special handling for product/device names:
- Look for "generic name", "device name", "product name"
- Return just the name without "generic name:" prefix
- Example: For "Generic name: Pulse Oximeter", return "Pulse Oximeter"
            """,
            "company_name": """
Special handling for company/manufacturer names:
- Look for manufacturer, company name, or "made by"
- Return just the company name
- Example: For "Manufactured by: ACME Corp", return "ACME Corp"
            """,
            "manufacturer": """
Special handling for manufacturer information:
- Look for manufacturer, company name, or "made by"
- Return just the company name
- Example: For "Manufactured by: ACME Corp", return "ACME Corp"
            """,
            "document_number": """
Special handling for document numbers:
- Look for document number, reference number, document ID
- Return just the number/code
- Example: For "Document No: PLL/DMF/001", return "PLL/DMF/001"
            """,
            "model_number": """
Special handling for model numbers:
- Look for model number, model name, device model
- Return just the model identifier
- Example: For "Model: OPO101, OPO102", return "OPO101, OPO102"
            """,
            "serial_number": """
Special handling for serial numbers:
- Look for serial number, device serial
- Return just the serial identifier
- Example: For "Serial: ABC123", return "ABC123"
            """,
            "date": """
Special handling for dates:
- Look for dates in various formats
- Return in MM/DD/YYYY or DD/MM/YYYY format if possible
- Example: For "Created on March 15, 2024", return "03/15/2024"
            """,
            "signature": """
Special handling for signature fields:
- Look for names of people who signed or authorized
- Return just the person's name
- Example: For "Approved by Dr. John Smith", return "Dr. John Smith"
            """,
            "address": """
Special handling for addresses:
- Look for complete address information
- Return the full address
- Example: Return "123 Main St, City, State 12345"
            """,
            "general": f"""
General field handling for "{field_name}":
- Look for information directly related to "{field_name}"
- Extract only the specific value needed
- Avoid including field labels in the response
            """
        }
        
        return instructions.get(field_type, instructions["general"])
    
    def _clean_field_result(self, result: str, field_type: str, field_name: str) -> str:
        """Clean up the extracted field result based on field type"""
        try:
            if not result or result == "NOT_FOUND":
                return result
            
            # Remove common prefixes that might be included
            prefixes_to_remove = [
                f"{field_name}:",
                f"{field_name}",
                "Value:",
                "Answer:",
                "Result:",
                "Generic name:",
                "Model No.:",
                "Model Name:",
                "Document No.:",
                "Serial No.:",
                "Manufacturer:",
                "Company:",
                "Date:",
                "Signature:",
                "Address:",
            ]
            
            for prefix in prefixes_to_remove:
                if result.lower().startswith(prefix.lower()):
                    result = result[len(prefix):].strip(' :')
                    break
            
            # Field-type specific cleaning
            if field_type == "date":
                # Try to standardize date format
                import re
                date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', result)
                if date_match:
                    result = f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}"
            
            elif field_type in ["document_number", "model_number", "serial_number"]:
                # Clean up number fields - remove extra spaces and common words
                result = re.sub(r'\b(number|no\.?|#)\b', '', result, flags=re.IGNORECASE).strip()
                result = re.sub(r'\s+', ' ', result).strip()
            
            elif field_type in ["product_name", "company_name", "manufacturer"]:
                # Title case for names
                if not result.isupper() and len(result) > 3:
                    result = result.title()
            
            return result.strip()
            
        except Exception as e:
            logger.error(f"❌ Failed to clean field result: {e}")
            return result
    
    def _fallback_field_extraction(self, field_name: str, field_context: str, context_docs: List[str]) -> Optional[str]:
        """Enhanced fallback field extraction when AI is not available"""
        try:
            field_name_lower = field_name.lower()
            
            for doc in context_docs:
                doc_lower = doc.lower()
                lines = doc.split('\n')
                
                # Strategy 1: Look for exact field name matches
                for line in lines:
                    line_lower = line.lower()
                    
                    # Look for "field_name: value" patterns
                    if field_name_lower in line_lower and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            # Check if field name is before the colon
                            before_colon = parts[0].strip().lower()
                            if field_name_lower in before_colon:
                                value = ':'.join(parts[1:]).strip()
                                if value and len(value) > 0:
                                    return value
                
                # Strategy 2: Look for common patterns based on field type
                if any(term in field_name_lower for term in ['generic', 'name', 'device']):
                    # Look for device/product names
                    for line in lines:
                        if any(term in line.lower() for term in ['generic name', 'device name', 'product name']):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                return parts[1].strip()
                
                elif any(term in field_name_lower for term in ['document', 'no', 'number']):
                    # Look for document numbers
                    for line in lines:
                        if any(term in line.lower() for term in ['document no', 'doc no', 'reference']):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                return parts[1].strip()
                
                elif any(term in field_name_lower for term in ['manufacturer', 'company']):
                    # Look for manufacturer info
                    for line in lines:
                        if any(term in line.lower() for term in ['manufacturer', 'company', 'made by']):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                return parts[1].strip()
                
                elif any(term in field_name_lower for term in ['model']):
                    # Look for model info
                    for line in lines:
                        if any(term in line.lower() for term in ['model', 'version']):
                            parts = line.split(':')
                            if len(parts) >= 2:
                                return parts[1].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed in fallback field extraction: {e}")
            return None
    
    async def fill_template_field(
        self, 
        field_name: str, 
        context_docs: List[str],
        additional_context: str = ""
    ) -> Optional[str]:
        """Fill a specific template field using context documents"""
        try:
            context_text = "\n\n".join(context_docs)
            
            prompt = f"""Based on the following context documents, find information to fill the template field "{field_name}".

Context documents:
{context_text}

{additional_context}

Field to fill: {field_name}

Please provide only the value that should be inserted for this field. If you cannot find relevant information in the context, respond with "NOT_FOUND"."""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=200,
                    temperature=0.1,  # Lower temperature for more precise extraction
                )
            )
            
            result = response.text.strip()
            return None if result == "NOT_FOUND" else result
            
        except Exception as e:
            logger.error(f"❌ Failed to fill template field {field_name}: {e}")
            return None

# Global instance
gemini_service = GeminiService()
