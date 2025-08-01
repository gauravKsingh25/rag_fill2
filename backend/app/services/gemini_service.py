import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import logging
import re
import json
import hashlib
import numpy as np
import asyncio
import time
from functools import wraps

logger = logging.getLogger(__name__)

# Simple in-memory cache
_cache = {}
_api_call_count = 0  # Track API calls

# Global semaphore for throttling concurrent API calls
_api_semaphore = asyncio.Semaphore(2)  # Max 2 concurrent API calls
_last_api_call_time = 0
_min_delay_between_calls = 1.0  # Minimum 1 second between calls

def rate_limit_retry(max_retries=3, base_delay=1):
    """Decorator for rate limiting with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            global _api_call_count, _last_api_call_time
            
            # Acquire semaphore to limit concurrent calls
            async with _api_semaphore:
                # Enforce minimum delay between calls
                current_time = time.time()
                time_since_last_call = current_time - _last_api_call_time
                if time_since_last_call < _min_delay_between_calls:
                    delay = _min_delay_between_calls - time_since_last_call
                    logger.debug(f"⏱️ Throttling: waiting {delay:.2f}s between API calls")
                    await asyncio.sleep(delay)
                
                for attempt in range(max_retries + 1):
                    try:
                        _api_call_count += 1
                        _last_api_call_time = time.time()
                        logger.info(f"🌐 API Call #{_api_call_count}: {func.__name__}")
                        return await func(*args, **kwargs)
                    except Exception as e:
                        error_str = str(e)
                        if "429" in error_str or "quota" in error_str.lower():
                            if attempt < max_retries:
                                # Extract retry delay from error message
                                retry_delay = base_delay * (2 ** attempt)
                                try:
                                    # Try to extract suggested delay from error
                                    delay_match = re.search(r'retry_delay.*?seconds[^:]*:\s*(\d+)', error_str)
                                    if delay_match:
                                        retry_delay = max(retry_delay, int(delay_match.group(1)))
                                except:
                                    pass
                                
                                logger.warning(f"Rate limit hit, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries + 1})")
                                await asyncio.sleep(retry_delay)
                                continue
                        raise e
                raise Exception(f"Max retries ({max_retries}) exceeded")
        return wrapper
    return decorator
    return decorator

class GeminiService:
    def __init__(self):
        self.api_key = "AIzaSyCEYOkQN5xmbpmZB8TFiXP07HUGZoEI7Zo"
        self.available = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.available = True
                logger.info("✅ Google Gemini API configured successfully")
            except Exception as e:
                logger.warning(f"❌ Failed to configure Google Gemini API: {e}")
                logger.info("📝 Gemini service will operate in fallback mode")
        else:
            logger.info("📝 Google API key not configured - using fallback mode")
            
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
        """Extract placeholder fields from template content with enhanced detection"""
        try:
            if not self.available:
                # Enhanced fallback: extract manually using comprehensive regex
                import re
                patterns = [
                    r'\{([^}]+)\}',          # {field}
                    r'\[([^\]]+)\]',         # [field] 
                    r'<([^>]+)>',            # <field>
                    r'([A-Za-z][A-Za-z\s]+):\s*_{3,}',  # Field: ___
                    r'([A-Za-z][A-Za-z\s]+)\s+_{3,}',   # Field ___
                    r'([A-Za-z][A-Za-z\s]+):\s*\.{3,}', # Field: ...
                    r'([A-Za-z][A-Za-z\s]+):\s*$',      # Field: (at end of line)
                ]
                
                fields = set()
                for pattern in patterns:
                    matches = re.findall(pattern, template_content, re.MULTILINE | re.IGNORECASE)
                    for match in matches:
                        if isinstance(match, tuple):
                            field_name = match[0] if match[0] else match
                        else:
                            field_name = match
                        
                        # Clean field name
                        field_name = field_name.strip(' :._-[]{}()<>')
                        field_name = re.sub(r'\s+', ' ', field_name)
                        
                        if len(field_name) > 2 and field_name.lower() not in ['text', 'data', 'info', 'value']:
                            fields.add(field_name)
                
                return list(fields)

            prompt = f"""Analyze the following document template and extract all placeholder fields that need to be filled.
Look for ALL types of patterns including:
- {{field_name}}, [field_name], <field_name>
- Field Name: _______ (underscores)
- Field Name: ....... (dots)
- Field Name: (at end of line)
- Field Name _______ (spaces before underscores)
- Checkbox fields with labels
- Form fields with blanks to fill

Template content:
{template_content}

Focus on extracting the actual field names (what type of information is needed), not the placeholder symbols.
Return a comprehensive JSON list of field names. Examples: ["Document Number", "Brand Name", "Model Number", "Date", "Signature"]

Important: Include ALL fields that appear to need filling, even if they use different placeholder formats."""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=500,
                    temperature=0.1,
                )
            )
            
            # Parse the response to extract field names
            import json
            try:
                fields = json.loads(response.text)
                return fields if isinstance(fields, list) else []
            except json.JSONDecodeError:
                # Enhanced fallback: extract manually with better patterns
                import re
                
                # Try to extract from the response text
                field_lines = response.text.split('\n')
                fields = []
                
                for line in field_lines:
                    # Look for quoted field names
                    quoted_fields = re.findall(r'"([^"]+)"', line)
                    fields.extend(quoted_fields)
                    
                    # Look for listed items
                    if re.match(r'^\s*[-*•]\s*', line):
                        item = re.sub(r'^\s*[-*•]\s*', '', line).strip()
                        if item and len(item) > 2:
                            fields.append(item)
                
                if not fields:
                    # Ultimate fallback: use comprehensive regex on original content
                    patterns = [
                        r'\{([^}]+)\}',          # {field}
                        r'\[([^\]]+)\]',         # [field] 
                        r'<([^>]+)>',            # <field>
                        r'([A-Za-z][A-Za-z\s]+):\s*_{3,}',  # Field: ___
                        r'([A-Za-z][A-ZaZ\s]+)\s+_{3,}',   # Field ___
                        r'([A-Za-z][A-Za-z\s]+):\s*\.{3,}', # Field: ...
                    ]
                    
                    field_set = set()
                    for pattern in patterns:
                        matches = re.findall(pattern, template_content, re.MULTILINE | re.IGNORECASE)
                        for match in matches:
                            if isinstance(match, tuple):
                                field_name = match[0] if match[0] else match
                            else:
                                field_name = match
                            
                            # Clean field name
                            field_name = field_name.strip(' :._-[]{}()<>')
                            field_name = re.sub(r'\s+', ' ', field_name)
                            
                            if len(field_name) > 2:
                                field_set.add(field_name)
                    
                    fields = list(field_set)
                
                return fields
            
        except Exception as e:
            logger.error(f"❌ Failed to extract template fields: {e}")
            # Final fallback
            import re
            patterns = [
                r'\{([^}]+)\}',
                r'\[([^\]]+)\]',
                r'<([^>]+)>',
                r'([A-Za-z][A-Za-z\s]+):\s*_{3,}',
                r'([A-Za-z][A-ZaZ\s]+)\s+_{3,}',
            ]
            
            fields = set()
            for pattern in patterns:
                matches = re.findall(pattern, template_content, re.MULTILINE)
                fields.update(matches)
            
            return list(fields)
    
    async def generate_field_questions(self, field_name: str, field_context: str) -> List[str]:
        """Generate targeted questions for a specific field to improve search"""
        try:
            if not self.available:
                # Enhanced fallback questions when API is not available
                base_questions = [
                    f"What is the {field_name}?",
                    f"Find {field_name} information",
                    f"{field_name} details",
                    f"Get {field_name} value",
                    f"Search for {field_name}"
                ]
                return base_questions[:3]
            
            prompt = f"""Generate 4-6 targeted search questions to find information for filling the template field "{field_name}".

Context from template: {field_context}

The questions should be specific and likely to find relevant information in a document database.
Focus on different ways this information might be expressed in technical documents.

Consider these question types:
1. Direct questions about the field
2. Questions about related terminology
3. Questions about document identification
4. Questions about specifications or details

Examples for "Document No.":
- What is the document number?
- Find document identification number
- What is the DMF document number?
- Document reference number
- File identification code

Examples for "Brand Name":
- What is the brand name?
- Which company manufactures this?
- Product brand information
- Manufacturer name

Return only a JSON list of questions: ["question1", "question2", "question3", "question4"]"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=400,
                    temperature=0.3,
                )
            )
            
            try:
                import json
                questions = json.loads(response.text)
                if isinstance(questions, list) and len(questions) > 0:
                    return questions[:6]  # Limit to 6 questions
                else:
                    return [f"What is the {field_name}?", f"Find {field_name} information"]
            except json.JSONDecodeError:
                # Fallback: extract questions manually
                lines = response.text.split('\n')
                questions = []
                for line in lines:
                    # Clean up the line
                    line = line.strip(' -"\'[]{}()')
                    if line and '?' in line and len(line) > 10:
                        questions.append(line)
                
                return questions[:6] if questions else [f"What is the {field_name}?", f"Find {field_name} information"]
                
        except Exception as e:
            logger.error(f"❌ Failed to generate questions for field {field_name}: {e}")
            return [
                f"What is the {field_name}?",
                f"Find {field_name} information",
                f"{field_name} details"
            ]
    
    @rate_limit_retry(max_retries=3, base_delay=2)
    async def generate_questions_batch(self, field_infos: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate questions for multiple fields in a single API call"""
        try:
            if not self.available:
                # Fallback: generate basic questions for all fields
                result = {}
                for field_info in field_infos:
                    field_name = field_info['field_name']
                    result[field_name] = [
                        f"What is the {field_name}?",
                        f"Find {field_name} information",
                        f"{field_name} details"
                    ]
                return result
            
            # Check cache first
            cache_key = f"questions_batch_{hashlib.md5(str(field_infos).encode()).hexdigest()}"
            if cache_key in _cache:
                logger.info("📋 Using cached questions batch")
                return _cache[cache_key]
            
            # Build batch prompt for all fields
            fields_text = ""
            for i, field_info in enumerate(field_infos, 1):
                field_name = field_info['field_name']
                field_context = field_info.get('context', '')[:100]  # Limit context length
                fields_text += f"{i}. Field: \"{field_name}\"\n   Context: {field_context}\n\n"
            
            prompt = f"""Generate 3-4 targeted search questions for each of the following template fields.
The questions should help find relevant information in a document database.

Fields to analyze:
{fields_text}

For each field, create questions that:
1. Ask directly about the field
2. Use related terminology
3. Consider document identification patterns
4. Think about technical specifications

Return a JSON object where each field name maps to an array of questions:
{{
  "field_name_1": ["question1", "question2", "question3"],
  "field_name_2": ["question1", "question2", "question3"],
  ...
}}

Focus on practical questions that would find relevant content in medical device documentation."""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=800,
                    temperature=0.2,
                )
            )
            
            try:
                result = json.loads(response.text)
                if isinstance(result, dict):
                    # Cache the result
                    _cache[cache_key] = result
                    logger.info(f"✅ Generated questions for {len(result)} fields in batch")
                    return result
                else:
                    raise ValueError("Invalid response format")
            except (json.JSONDecodeError, ValueError):
                # Fallback: generate basic questions
                logger.warning("📝 Using fallback question generation")
                result = {}
                for field_info in field_infos:
                    field_name = field_info['field_name']
                    result[field_name] = [
                        f"What is the {field_name}?",
                        f"Find {field_name} information",
                        f"{field_name} details"
                    ]
                return result
                
        except Exception as e:
            logger.error(f"❌ Failed to generate questions batch: {e}")
            # Final fallback
            result = {}
            for field_info in field_infos:
                field_name = field_info['field_name']
                result[field_name] = [
                    f"What is the {field_name}?",
                    f"Find {field_name} information"
                ]
            return result
    
    @rate_limit_retry(max_retries=3, base_delay=2)
    async def fill_template_fields_batch(
        self, 
        fields_data: List[Dict[str, Any]], 
        device_id: str
    ) -> Dict[str, Optional[str]]:
        """Fill multiple template fields in a single API call"""
        try:
            if not self.available:
                # Simple fallback when API is not available
                result = {}
                for field_data in fields_data:
                    field_name = field_data['field_name']
                    context_docs = field_data.get('context_docs', [])
                    
                    # Simple keyword matching fallback
                    for doc in context_docs:
                        if field_name.lower() in doc.lower():
                            lines = doc.split('\n')
                            for line in lines:
                                if field_name.lower() in line.lower():
                                    parts = line.split(':')
                                    if len(parts) > 1:
                                        result[field_name] = parts[1].strip()
                                        break
                            if field_name in result:
                                break
                    
                    if field_name not in result:
                        result[field_name] = None
                
                return result
            
            # Check cache first
            cache_key = f"fill_batch_{hashlib.md5(str(fields_data).encode()).hexdigest()}"
            if cache_key in _cache:
                logger.info("📋 Using cached fill results")
                return _cache[cache_key]
            
            # Build batch prompt for all fields
            fields_text = ""
            context_summary = ""
            
            for i, field_data in enumerate(fields_data, 1):
                field_name = field_data['field_name']
                field_context = field_data.get('field_context', '')[:50]
                questions = field_data.get('questions', [])
                
                fields_text += f"{i}. Field: \"{field_name}\"\n"
                fields_text += f"   Context: {field_context}\n"
                fields_text += f"   Questions: {', '.join(questions[:2])}\n\n"
                
                # Add relevant context docs
                context_docs = field_data.get('context_docs', [])
                if context_docs:
                    context_summary += f"Context for {field_name}:\n"
                    context_summary += "\n".join(context_docs[:2])  # Top 2 docs per field
                    context_summary += "\n\n"
            
            prompt = f"""You are filling multiple template fields with information from document context.

FIELDS TO FILL:
{fields_text}

DOCUMENT CONTEXT:
{context_summary}

INSTRUCTIONS:
1. For each field, find the most relevant information from the document context
2. Extract ONLY the specific value that should fill each field
3. Return just the value, no explanations or prefixes
4. If information is not found for a field, use "NOT_FOUND"

EXAMPLES:
- For "Document No.": return "PLL/DMF/001" not "The document number is PLL/DMF/001"
- For "Brand Name": return "Dr. Odin" not "Brand: Dr. Odin"
- For "Model No.": return "OPO101, OPO102" not "Models: OPO101, OPO102"

Return a JSON object mapping field names to their values:
{{
  "field_name_1": "extracted_value_1",
  "field_name_2": "extracted_value_2",
  "field_name_3": "NOT_FOUND"
}}

Device: {device_id}"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=500,
                    temperature=0.1,
                )
            )
            
            try:
                result = json.loads(response.text)
                if isinstance(result, dict):
                    # Convert "NOT_FOUND" to None and clean up values
                    cleaned_result = {}
                    for field_name, value in result.items():
                        if value == "NOT_FOUND" or not value:
                            cleaned_result[field_name] = None
                        else:
                            # Clean up common prefixes
                            cleaned_value = str(value).strip()
                            for prefix in [f"{field_name}:", f"{field_name}", "Value:", "Answer:"]:
                                if cleaned_value.lower().startswith(prefix.lower()):
                                    cleaned_value = cleaned_value[len(prefix):].strip(' :')
                                    break
                            cleaned_result[field_name] = cleaned_value if cleaned_value else None
                    
                    # Cache the result
                    _cache[cache_key] = cleaned_result
                    filled_count = sum(1 for v in cleaned_result.values() if v is not None)
                    logger.info(f"✅ Filled {filled_count}/{len(fields_data)} fields in batch")
                    return cleaned_result
                else:
                    raise ValueError("Invalid response format")
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"📝 Failed to parse batch response: {e}")
                # Fallback to individual processing
                result = {}
                for field_data in fields_data:
                    result[field_data['field_name']] = None
                return result
                
        except Exception as e:
            logger.error(f"❌ Failed to fill fields batch: {e}")
            # Return empty results
            return {field_data['field_name']: None for field_data in fields_data}
    
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
                # Simple fallback when API is not available
                for doc in context_docs:
                    # Simple keyword matching
                    if field_name.lower() in doc.lower():
                        # Try to extract value after the field name
                        lines = doc.split('\n')
                        for line in lines:
                            if field_name.lower() in line.lower():
                                # Extract value after colon or similar patterns
                                parts = line.split(':')
                                if len(parts) > 1:
                                    return parts[1].strip()
                return None
            
            context_text = "\n\n".join(context_docs[:3])  # Limit context size
            questions_text = "\n".join([f"- {q}" for q in questions])
            
            prompt = f"""You are filling a template field with information from document context.

Field to fill: "{field_name}"
Template context: {field_context}

Search questions used: 
{questions_text}

Document context:
{context_text}

Device: {device_id}

Instructions:
1. Analyze the document context carefully
2. Find the most relevant information for the field "{field_name}"
3. Extract ONLY the specific value that should fill this field
4. Return just the value, no explanations or extra text
5. If you cannot find relevant information, return "NOT_FOUND"

Examples:
- For "Document No.": return "PLL/DMF/001" not "The document number is PLL/DMF/001"
- For "Brand Name": return "Dr. Odin" not "Brand: Dr. Odin"  
- For "Model No.": return "OPO101, OPO102" not "Models: OPO101, OPO102"

Value to fill:"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=100,
                    temperature=0.1,  # Very low temperature for precise extraction
                )
            )
            
            result = response.text.strip()
            
            # Clean up common prefixes that might be included
            prefixes_to_remove = [
                f"{field_name}:",
                f"{field_name}",
                "Value:",
                "Answer:",
                "Result:",
            ]
            
            for prefix in prefixes_to_remove:
                if result.lower().startswith(prefix.lower()):
                    result = result[len(prefix):].strip(' :')
                    break
            
            return None if result == "NOT_FOUND" or not result else result
            
        except Exception as e:
            logger.error(f"❌ Failed to fill template field {field_name}: {e}")
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
    
    def get_api_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        global _api_call_count
        return {
            "total_api_calls": _api_call_count,
            "cache_size": len(_cache),
            "service_available": self.available
        }
    
    def reset_api_counter(self):
        """Reset API call counter (for testing)"""
        global _api_call_count
        _api_call_count = 0
    
    # ===== ENHANCED PARALLEL PROCESSING METHODS =====
    
    async def process_template_fields_parallel(
        self, 
        field_infos: List[Dict[str, Any]], 
        device_id: str,
        max_batch_size: int = 12,
        max_concurrent_batches: int = 2
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process template fields with intelligent parallel processing and batching
        
        Args:
            field_infos: List of field info dictionaries
            device_id: Device identifier
            max_batch_size: Maximum fields per API call (default 12 for better token usage)
            max_concurrent_batches: Maximum concurrent API calls (default 2 to respect rate limits)
        
        Returns:
            Dictionary mapping field names to {questions: List[str], value: Optional[str]}
        """
        try:
            logger.info(f"🚀 Starting parallel processing for {len(field_infos)} fields")
            
            # Step 1: Generate questions for ALL fields in one optimized call
            logger.info("📝 Generating questions for all fields in single batch...")
            questions_map = await self.generate_questions_batch(field_infos)
            
            # Step 2: Prepare field data with context
            logger.info("🔍 Gathering context for all fields...")
            fields_with_context = await self._gather_context_parallel(
                field_infos, questions_map, device_id
            )
            
            # Step 3: Process field filling in optimized parallel batches
            logger.info(f"⚡ Processing field filling in parallel batches (max {max_concurrent_batches} concurrent)...")
            filled_values = await self._fill_fields_parallel_batches(
                fields_with_context, device_id, max_batch_size, max_concurrent_batches
            )
            
            # Step 4: Combine results
            results = {}
            for field_info in field_infos:
                field_name = field_info['field_name']
                results[field_name] = {
                    'questions': questions_map.get(field_name, []),
                    'value': filled_values.get(field_name)
                }
            
            logger.info(f"✅ Parallel processing completed: {len(results)} fields processed")
            return results
            
        except Exception as e:
            logger.error(f"❌ Parallel processing failed: {e}")
            raise
    
    async def _gather_context_parallel(
        self, 
        field_infos: List[Dict[str, Any]], 
        questions_map: Dict[str, List[str]], 
        device_id: str
    ) -> List[Dict[str, Any]]:
        """Gather context for fields in parallel with throttling"""
        
        # Import here to avoid circular imports
        from app.services.pinecone_service import pinecone_service
        
        async def get_context_for_field(field_info):
            field_name = field_info['field_name']
            questions = questions_map.get(field_name, [f"What is the {field_name}?"])
            
            # Search with multiple questions but limit to prevent overload
            all_results = []
            for question in questions[:2]:  # Limit to 2 questions per field
                try:
                    query_embedding = await self.get_embedding(question)
                    search_results = await pinecone_service.search_vectors(
                        query_vector=query_embedding,
                        device_id=device_id,
                        top_k=2  # Reduced to 2 for faster processing
                    )
                    all_results.extend(search_results)
                except Exception as e:
                    logger.warning(f"⚠️ Context search failed for '{question}': {e}")
            
            # Deduplicate and get top results
            unique_docs = {}
            for result in all_results:
                if result.content not in unique_docs:
                    unique_docs[result.content] = result.score
            
            sorted_docs = sorted(unique_docs.items(), key=lambda x: x[1], reverse=True)
            context_docs = [content for content, score in sorted_docs[:2]]  # Top 2 per field
            
            return {
                'field_name': field_name,
                'field_context': field_info.get('context', ''),
                'questions': questions,
                'context_docs': context_docs
            }
        
        # Process context gathering with concurrency limit
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent context searches
        
        async def throttled_context_search(field_info):
            async with semaphore:
                return await get_context_for_field(field_info)
        
        tasks = [throttled_context_search(field_info) for field_info in field_infos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"❌ Context gathering failed for field {field_infos[i]['field_name']}: {result}")
                # Add fallback data
                field_info = field_infos[i]
                valid_results.append({
                    'field_name': field_info['field_name'],
                    'field_context': field_info.get('context', ''),
                    'questions': [f"What is the {field_info['field_name']}?"],
                    'context_docs': []
                })
            else:
                valid_results.append(result)
        
        return valid_results
    
    async def _fill_fields_parallel_batches(
        self, 
        fields_with_context: List[Dict[str, Any]], 
        device_id: str,
        max_batch_size: int,
        max_concurrent_batches: int
    ) -> Dict[str, Optional[str]]:
        """Fill fields in parallel batches with intelligent throttling"""
        
        # Split fields into optimized batches
        batches = []
        for i in range(0, len(fields_with_context), max_batch_size):
            batch = fields_with_context[i:i + max_batch_size]
            batches.append(batch)
        
        logger.info(f"📦 Created {len(batches)} batches (max size: {max_batch_size})")
        
        # Process batches with concurrency control
        semaphore = asyncio.Semaphore(max_concurrent_batches)
        
        async def process_batch_with_throttle(batch_data):
            batch, batch_idx = batch_data
            async with semaphore:
                logger.info(f"🔄 Processing batch {batch_idx + 1}/{len(batches)}")
                try:
                    # Add delay between batches to prevent rate limit clustering
                    if batch_idx > 0:
                        await asyncio.sleep(0.5)  # 500ms delay between batches
                    
                    result = await self.fill_template_fields_batch(batch, device_id)
                    logger.info(f"✅ Batch {batch_idx + 1} completed: {len(result)} fields filled")
                    return result
                except Exception as e:
                    logger.error(f"❌ Batch {batch_idx + 1} failed: {e}")
                    # Return empty dict for failed batch
                    return {}
        
        # Execute batches in parallel with throttling
        batch_tasks = [
            process_batch_with_throttle((batch, idx)) 
            for idx, batch in enumerate(batches)
        ]
        
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        
        # Combine all batch results
        combined_results = {}
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(f"❌ Batch {i + 1} returned exception: {result}")
            elif isinstance(result, dict):
                combined_results.update(result)
        
        return combined_results
    
    def configure_parallel_processing(
        self, 
        max_concurrent_api_calls: int = 2,
        min_delay_between_calls: float = 1.0,
        max_batch_size: int = 12
    ):
        """
        Configure parallel processing parameters
        
        Args:
            max_concurrent_api_calls: Maximum concurrent API calls (default 2)
            min_delay_between_calls: Minimum delay between API calls in seconds (default 1.0)
            max_batch_size: Maximum fields per batch API call (default 12)
        """
        global _api_semaphore, _min_delay_between_calls
        
        _api_semaphore = asyncio.Semaphore(max_concurrent_api_calls)
        _min_delay_between_calls = min_delay_between_calls
        
        logger.info(f"🔧 Configured parallel processing:")
        logger.info(f"   • Max concurrent calls: {max_concurrent_api_calls}")
        logger.info(f"   • Min delay between calls: {min_delay_between_calls}s")
        logger.info(f"   • Max batch size: {max_batch_size}")

# Global instance
gemini_service = GeminiService()
