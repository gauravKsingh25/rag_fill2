import os
import google.generativeai as genai
from typing import List, Dict, Any, Optional
import logging
import re
import json
import hashlib
import numpy as np

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self):
        self.api_key = "AIzaSyA5ibwM9k5ee3GCAUlsU5tDlsSTX6U6VoY"
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
        """Extract placeholder fields from template content"""
        try:
            prompt = f"""Analyze the following document template and extract all placeholder fields that need to be filled.
Look for patterns like {{field_name}}, [field_name], <field_name>, or similar placeholder formats.

Template content:
{template_content}

Return only a JSON list of field names without the placeholder markers. For example: ["name", "date", "amount"]"""

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
                patterns = [
                    r'\{([^}]+)\}',  # {field}
                    r'\[([^\]]+)\]',  # [field] 
                    r'<([^>]+)>',    # <field>
                ]
                
                fields = set()
                for pattern in patterns:
                    matches = re.findall(pattern, template_content)
                    fields.update(matches)
                
                return list(fields)
            
        except Exception as e:
            logger.error(f"❌ Failed to extract template fields: {e}")
            return []
    
    async def generate_field_questions(self, field_name: str, field_context: str) -> List[str]:
        """Generate targeted questions for a specific field to improve search"""
        try:
            if not self.available:
                # Fallback questions when API is not available
                return [
                    f"What is the {field_name}?",
                    f"Find {field_name} information",
                    f"{field_name} details"
                ]
            
            prompt = f"""Generate 3-5 targeted search questions to find information for filling the template field "{field_name}".

Context from template: {field_context}

The questions should be specific and likely to find relevant information in a document database.
Focus on different ways this information might be expressed in technical documents.

Examples for "Document No.":
- What is the document number?
- Find document identification number
- What is the DMF document number?
- Document reference number

Return only a JSON list of questions: ["question1", "question2", "question3"]"""

            model = genai.GenerativeModel(self.generation_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=300,
                    temperature=0.3,
                )
            )
            
            try:
                import json
                questions = json.loads(response.text)
                return questions if isinstance(questions, list) else [f"What is the {field_name}?"]
            except json.JSONDecodeError:
                # Fallback: extract questions manually
                lines = response.text.split('\n')
                questions = []
                for line in lines:
                    line = line.strip(' -"\'')
                    if line and '?' in line:
                        questions.append(line)
                
                return questions[:5] if questions else [f"What is the {field_name}?"]
                
        except Exception as e:
            logger.error(f"❌ Failed to generate questions for field {field_name}: {e}")
            return [
                f"What is the {field_name}?",
                f"Find {field_name} information",
                f"{field_name} details"
            ]
    
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

# Global instance
gemini_service = GeminiService()
