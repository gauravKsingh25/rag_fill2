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
        temperature: float = 0.7
    ) -> str:
        """Generate response using Gemini with optional context"""
        try:
            if not self.available:
                # Fallback response when API is not available
                logger.warning("📝 Using fallback response (Google API not available)")
                if context:
                    return f"I have access to {len(context)} documents, but I cannot generate detailed responses without the Google Gemini API. Please configure the GOOGLE_API_KEY in your .env file."
                else:
                    return "I cannot generate responses without the Google Gemini API. Please configure the GOOGLE_API_KEY in your .env file."
            
            model = genai.GenerativeModel(self.generation_model)
            
            # Build the full prompt with context
            full_prompt = prompt
            if context:
                context_text = "\n\n".join(context)
                full_prompt = f"""Context information:
{context_text}

User question: {prompt}

Please provide a helpful and accurate response based on the context provided. If the context doesn't contain enough information to answer the question, please say so."""
            
            response = model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"❌ Failed to generate response: {e}")
            # Fallback response on error
            return "I encountered an error generating the response. Please check the logs and ensure the Google API key is properly configured."
    
    async def extract_template_fields(self, template_content: str) -> List[str]:
        """Extract placeholder fields from template content"""
        try:
            prompt = f"""Analyze the following document template and extract all placeholder fields that need to be filled.
Look for these patterns:
1. {{field_name}}, [field_name], <field_name> - standard placeholder formats
2. [Missing] - blanks that need to be filled
3. Lines ending with ":" followed by blank space - form fields like "Generic name:", "Model Name:"

Template content:
{template_content}

Return only a JSON list of field names. For [Missing], use "Missing_X" where X is the occurrence number.
For fields ending with ":", use the text before the colon.
Example: ["Missing_1", "Missing_2", "Generic name", "Model Name"]"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(prompt)
            
            # Parse the response to extract field names
            import json
            try:
                fields = json.loads(response.text)
                return fields if isinstance(fields, list) else []
            except json.JSONDecodeError:
                # Fallback: extract manually using regex
                import re
                fields = set()
                
                # Pattern 1: Standard placeholders {field}, [field], <field>
                standard_patterns = [
                    r'\{([^}]+)\}',  # {field}
                    r'\[([^\]]+)\]',  # [field] 
                    r'<([^>]+)>',    # <field>
                ]
                
                for pattern in standard_patterns:
                    matches = re.findall(pattern, template_content)
                    fields.update(matches)
                
                # Pattern 2: [Missing] occurrences
                missing_count = len(re.findall(r'\[Missing\]', template_content, re.IGNORECASE))
                for i in range(1, missing_count + 1):
                    fields.add(f"Missing_{i}")
                
                # Pattern 3: Fields ending with ":" (form fields)
                # Look for lines that end with ":" and are likely field labels
                lines = template_content.split('\n')
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
            
            prompt = f"""Generate exactly 3 targeted search questions to find information for filling the template field "{field_name}".

Field Type: {field_type}
Context from template: {field_context}

The questions should be specific and likely to find relevant information in a document database.
Focus on different ways this information might be expressed in technical documents.

Field-specific guidance:
- For names: Ask about "generic name", "device name", "product name"
- For numbers: Ask about "document number", "model number", "serial number", "reference number"
- For dates: Ask about "date", "when", "time"
- For manufacturers: Ask about "manufacturer", "company", "made by"
- For models: Ask about "model", "version", "type"
- For signatures: Ask about "signed by", "authorized by", "approved by"

Examples for "Document No":
- What is the document number?
- Find document identification number
- What is the reference number?

Examples for "Generic Name":
- What is the generic name of the device?
- What is the product name?
- What type of device is this?

Examples for "Manufacturer":
- Who is the manufacturer?
- What company makes this device?
- Who manufactured this product?

Return only a JSON list with exactly 3 questions: ["question1", "question2", "question3"]"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=300,
                    temperature=0.2,  # Lower temperature for more consistent questions
                )
            )
            
            try:
                import json
                questions = json.loads(response.text)
                if isinstance(questions, list) and len(questions) >= 2:
                    return questions[:3]  # Ensure max 3 questions
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
                
                if len(questions) >= 2:
                    return questions[:3]
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
                f"What type of device is this?"
            ]
        elif field_type == "company_name" or field_type == "manufacturer":
            questions = [
                f"Who is the manufacturer?",
                f"What company makes this device?",
                f"Who manufactured this product?"
            ]
        elif field_type == "document_number":
            questions = [
                f"What is the document number?",
                f"Find document identification number",
                f"What is the reference number?"
            ]
        elif field_type == "model_number" or field_type == "model":
            questions = [
                f"What is the model number?",
                f"Find model information",
                f"What are the device models?"
            ]
        elif field_type == "serial_number":
            questions = [
                f"What is the serial number?",
                f"Find serial information",
                f"What is the device serial?"
            ]
        elif field_type == "date":
            questions = [
                f"What is the date?",
                f"When was this created?",
                f"Find date information"
            ]
        elif field_type == "signature":
            questions = [
                f"Who signed this?",
                f"Find signature information",
                f"Who authorized this?"
            ]
        elif field_type == "address":
            questions = [
                f"What is the address?",
                f"Find location information",
                f"Where is this located?"
            ]
        else:
            # Generic questions
            questions = [
                f"What is the {field_name}?",
                f"Find {field_name} information",
                f"Find information about {field_name}"
            ]
        
        return questions[:3]
    
    async def fill_template_field_enhanced(
        self, 
        field_name: str,
        field_context: str,
        context_docs: List[str],
        questions: List[str],
        device_id: str
    ) -> Optional[str]:
        """Enhanced template field filling with better context analysis"""
        try:
            if not self.available:
                # Enhanced fallback when API is not available
                return self._fallback_field_extraction(field_name, field_context, context_docs)
            
            context_text = "\n\n".join(context_docs[:3])  # Limit context size
            questions_text = "\n".join([f"- {q}" for q in questions])
            
            # Classify field type for specialized handling
            field_type = self._classify_field_type(field_name, field_context)
            
            # Create specialized instructions based on field type
            field_instructions = self._get_field_instructions(field_type, field_name)
            
            prompt = f"""You are filling a template field with information from document context.

Field to fill: "{field_name}"
Field type: {field_type}
Template context: {field_context}

{field_instructions}

Search questions used: 
{questions_text}

Document context:
{context_text}

Device: {device_id}

General Instructions:
1. Analyze the document context carefully
2. Find the most relevant information for the field "{field_name}"
3. Extract ONLY the specific value that should fill this field
4. Return just the value, no explanations or extra text
5. If you cannot find relevant information, return "NOT_FOUND"
6. Be precise and concise - avoid full sentences unless the field requires it

Value to fill:"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=150,
                    temperature=0.05,  # Very low temperature for precise extraction
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
