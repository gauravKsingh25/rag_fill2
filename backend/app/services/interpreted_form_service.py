"""
Interpreted Form Service for general purpose form filling
Handles data upload to Pinecone, template analysis, and form generation
"""

import os
import json
import uuid
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import tempfile
import zipfile
from datetime import datetime
import asyncio
import logging
import shutil
from docx import Document
from docx.shared import Inches

from .gemini_service import gemini_service
from .pinecone_service import pinecone_service
from .llm_service import LLMService, DocumentProcessor

logger = logging.getLogger(__name__)

class InterpretedFormService:
    """Service for handling interpreted form filling workflow"""
    
    def __init__(self):
        self.gemini_service = gemini_service
        self.pinecone_service = pinecone_service
        self.doc_processor = DocumentProcessor()
        self.output_dir = Path("filled_templates")
        self.output_dir.mkdir(exist_ok=True)
        
        # Create separate storage for person data
        self.person_storage_dir = Path("local_vector_storage/persons")
        self.person_storage_dir.mkdir(exist_ok=True, parents=True)
    
    def _get_person_storage_file(self, person_id: str) -> Path:
        """Get storage file path for person data"""
        return self.person_storage_dir / f"person_{person_id}_data.json"
    
    async def _store_person_vectors(self, person_id: str, vectors: List[Dict[str, Any]]) -> bool:
        """Store person vectors in separate storage"""
        try:
            storage_file = self._get_person_storage_file(person_id)
            
            # Load existing data if any
            existing_vectors = []
            if storage_file.exists():
                with open(storage_file, 'r', encoding='utf-8') as f:
                    existing_vectors = json.load(f)
            
            # Add new vectors
            existing_vectors.extend(vectors)
            
            # Save updated data
            with open(storage_file, 'w', encoding='utf-8') as f:
                json.dump(existing_vectors, f, indent=2)
            
            logger.info(f"✅ Stored {len(vectors)} vectors for person {person_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store person vectors: {e}")
            return False
    
    async def _search_person_vectors(self, person_id: str, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search vectors for a specific person"""
        try:
            storage_file = self._get_person_storage_file(person_id)
            
            if not storage_file.exists():
                logger.warning(f"❌ No data found for person {person_id}")
                return []
            
            # Load person data
            with open(storage_file, 'r', encoding='utf-8') as f:
                person_vectors = json.load(f)
            
            # Calculate similarity scores
            results = []
            for vector in person_vectors:
                if 'embedding' in vector and 'values' in vector:
                    embedding = vector.get('values', vector.get('embedding', []))
                    if embedding:
                        # Calculate cosine similarity
                        similarity = self._calculate_cosine_similarity(query_embedding, embedding)
                        results.append({
                            'text': vector.get('text', ''),
                            'metadata': vector.get('metadata', {}),
                            'score': similarity
                        })
            
            # Sort by similarity and return top_k
            results.sort(key=lambda x: x['score'], reverse=True)
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Failed to search person vectors: {e}")
            return []
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            
            # Convert to numpy arrays
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Calculate cosine similarity
            dot_product = np.dot(a, b)
            norms = np.linalg.norm(a) * np.linalg.norm(b)
            
            if norms == 0:
                return 0.0
            
            return dot_product / norms
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate similarity: {e}")
            return 0.0
        
    async def upload_person_data(
        self, 
        person_data_file: bytes, 
        filename: str, 
        device_id: str,
        person_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload person data to Pinecone database
        Supports JSON, CSV, TXT, PDF, DOCX formats
        """
        try:
            # Generate unique person ID if not provided
            if not person_id:
                person_id = str(uuid.uuid4())
            
            logger.info(f"🔄 Starting person data upload - device_id: {device_id}, person_id: {person_id}, filename: {filename}")
            
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                tmp_file.write(person_data_file)
                tmp_file_path = tmp_file.name
            
            try:
                # Extract content based on file type
                file_ext = Path(filename).suffix.lower()
                logger.info(f"📁 Processing {file_ext} file: {filename}")
                
                if file_ext == '.json':
                    with open(tmp_file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    # Convert JSON to text chunks for embedding
                    chunks = self._json_to_chunks(data, person_id)
                
                elif file_ext == '.csv':
                    import csv
                    chunks = []
                    with open(tmp_file_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row_idx, row in enumerate(reader):
                            for key, value in row.items():
                                if value and value.strip():
                                    chunk = {
                                        'text': f"{key}: {value}",
                                        'metadata': {
                                            'person_id': person_id,
                                            'device_id': device_id,
                                            'source_file': filename,
                                            'field_name': key,
                                            'field_value': value,
                                            'row_index': row_idx,
                                            'chunk_type': 'personal_data'
                                        }
                                    }
                                    chunks.append(chunk)
                
                elif file_ext in ['.txt', '.pdf', '.docx']:
                    # Extract text and create chunks
                    text_content = self.doc_processor.extract_text(tmp_file_path)
                    chunks = self._text_to_chunks(text_content, person_id, device_id, filename)
                
                else:
                    raise ValueError(f"Unsupported file format: {file_ext}")
                
                logger.info(f"📊 Created {len(chunks)} chunks from {filename}")
                
                # Generate embeddings and store in Pinecone
                vectors = []
                for i, chunk in enumerate(chunks):
                    try:
                        logger.info(f"🔤 Generating embedding for chunk {i+1}/{len(chunks)}: '{chunk['text'][:100]}...'")
                        embedding = await self.gemini_service.get_embedding(chunk['text'])
                        vector = {
                            'id': f"person_{person_id}_{uuid.uuid4()}",
                            'values': embedding,  # For compatibility
                            'embedding': embedding,  # For local search
                            'metadata': chunk['metadata'],
                            'text': chunk['text']  # Store text for search results
                        }
                        vectors.append(vector)
                        logger.info(f"✅ Generated embedding {i+1}/{len(chunks)}")
                    except Exception as e:
                        logger.warning(f"Failed to generate embedding for chunk {i}: {e}")
                        continue
                
                logger.info(f"🎯 Generated {len(vectors)} vectors for upload to person storage")
                
                # Store in separate person storage instead of device storage
                success = await self._store_person_vectors(person_id, vectors)
                
                if success:
                    logger.info(f"✅ Successfully stored {len(vectors)} person data vectors for person {person_id}")
                    return {
                        'success': True,
                        'person_id': person_id,
                        'chunks_processed': len(vectors),
                        'storage_type': 'person_storage',
                        'message': f'Successfully uploaded person data with {len(vectors)} data points'
                    }
                else:
                    raise Exception("Failed to store person vectors")
                    
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"❌ Failed to upload person data: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to upload person data'
            }
    
    async def analyze_template(
        self, 
        template_file: bytes, 
        filename: str, 
        device_id: str
    ) -> Dict[str, Any]:
        """
        Analyze template to identify blank spaces and field requirements
        """
        try:
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
                tmp_file.write(template_file)
                tmp_file_path = tmp_file.name
            
            try:
                # Extract text from template
                template_text = self.doc_processor.extract_text(tmp_file_path)
                
                # Use LLM to analyze template and identify blank fields
                analysis = await self._analyze_template_with_llm(template_text, filename)
                
                # Store template file for later use in form filling
                template_id = str(uuid.uuid4())
                stored_template_path = self.output_dir / f"template_{template_id}_{filename}"
                shutil.copy2(tmp_file_path, stored_template_path)
                
                # Add template path to analysis
                analysis['template_path'] = str(stored_template_path)
                analysis['template_id'] = template_id
                
                return {
                    'success': True,
                    'template_analysis': analysis,
                    'message': f'Successfully analyzed template: {filename}'
                }
                
            finally:
                # Clean up temporary file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"❌ Failed to analyze template: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to analyze template'
            }
    
    async def generate_filled_forms(
        self,
        person_id: str,
        templates: List[Dict[str, Any]],  # List of template analyses
        device_id: str,
        batch_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate filled forms using person data from Pinecone and template analyses
        Supports up to 5 templates at once
        """
        try:
            if len(templates) > 5:
                raise ValueError("Maximum 5 templates allowed per batch")
            
            if not batch_id:
                batch_id = str(uuid.uuid4())
            
            filled_documents = []
            download_links = []
            
            for template_idx, template in enumerate(templates):
                try:
                    # Fill individual template
                    filled_doc = await self._fill_single_template(
                        person_id, 
                        template, 
                        device_id, 
                        batch_id, 
                        template_idx
                    )
                    
                    if filled_doc['success']:
                        filled_documents.append(filled_doc)
                        download_links.append(filled_doc['download_url'])
                    
                except Exception as e:
                    logger.error(f"❌ Failed to fill template {template_idx}: {e}")
                    continue
            
            # Create batch download if multiple documents
            if len(filled_documents) > 1:
                batch_download_url = await self._create_batch_download(
                    filled_documents, 
                    batch_id
                )
                download_links.append(batch_download_url)
            
            return {
                'success': True,
                'batch_id': batch_id,
                'filled_documents': filled_documents,
                'download_links': download_links,
                'total_documents': len(filled_documents),
                'message': f'Successfully generated {len(filled_documents)} filled documents'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to generate filled forms: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate filled forms'
            }
    
    async def _analyze_template_with_llm(
        self, 
        template_text: str, 
        filename: str
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze template and identify fields to fill with enhanced contextual understanding
        """
        prompt = f"""
You are an expert legal document analyzer specializing in affidavits and wills. Analyze this template and identify ALL fillable fields with PRECISE LEGAL CONTEXTUAL UNDERSTANDING.

Template: {filename}
Content: {template_text[:2500]}

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON - no extra text, explanations, or markdown
2. This is a LEGAL AFFIDAVIT - understand legal roles and terminology
3. Identify ALL blank spaces with dots: ............., _____, [FIELD], etc.
4. Different legal roles (testator, witness A, witness B, etc.) need different field IDs

LEGAL CONTEXT PATTERNS TO RECOGNIZE:
- "executed by Shri ............" = testator name
- "son of ............" (after testator context) = testator father name
- "resident of ............" (after testator context) = testator address  
- "A, aged about ............" = witness A age
- "B, aged about ............" = witness B age
- "son of Shri ............" (after witness A) = witness A father name
- "resident of ............" (after witness A) = witness A address
- "executed his will on ............" = will execution date
- "Sub-Registrar ............" = registrar office/name
- "Verified at ............" = verification location

Return this EXACT JSON structure:
{{
  "template_info": {{
    "filename": "{filename}",
    "estimated_fields": 0,
    "template_type": "legal_affidavit"
  }},
  "identified_fields": [
  ]
}}

For each field, add to identified_fields array:
{{
  "field_id": "role_type_number",
  "field_type": "name|date|address|location|age|text",
  "semantic_role": "testator|witness_a|witness_b|father_of_testator|father_of_witness_a|father_of_witness_b|sub_registrar|general",
  "context": "surrounding text with legal terms",
  "description": "specific legal role description",
  "required": true,
  "contextual_keywords": ["legal", "role", "keywords"],
  "placeholder_patterns": ["dots pattern"]
}}

LEGAL ROLE EXAMPLES FOR AFFIDAVITS:
- "executed by Shri ............" → field_id: "testator_name_1", semantic_role: "testator", field_type: "name"
- "son of ............" (testator context) → field_id: "testator_father_name_1", semantic_role: "father_of_testator", field_type: "name"
- "resident of ............" (testator context) → field_id: "testator_address_1", semantic_role: "testator", field_type: "address"
- "A, aged about ............" → field_id: "witness_a_age_1", semantic_role: "witness_a", field_type: "age"
- "B, aged about ............" → field_id: "witness_b_age_1", semantic_role: "witness_b", field_type: "age"

IMPORTANT: 
- Distinguish between testator vs witness A vs witness B details
- Make descriptions SHORT and clear. No quotes in descriptions.
- Each context should get unique field_id based on legal role

Return ONLY the JSON object."""
        
        try:
            response = await self.gemini_service.generate_response(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.1
            )
            
            # Multiple attempts to parse JSON
            for attempt in range(3):
                try:
                    # Clean the response
                    response_text = response.strip()
                    
                    # Remove markdown formatting
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    elif response_text.startswith('```'):
                        response_text = response_text[3:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    response_text = response_text.strip()
                    
                    # Apply different levels of fixing based on attempt
                    if attempt == 0:
                        # First attempt: minimal cleaning
                        cleaned_text = response_text
                    elif attempt == 1:
                        # Second attempt: basic JSON fixing
                        cleaned_text = self._fix_json_formatting(response_text)
                    else:
                        # Third attempt: aggressive fixing
                        cleaned_text = self._aggressive_json_fix(response_text)
                    
                    # Try to parse
                    analysis = json.loads(cleaned_text)
                    
                    # Validate structure
                    if self._validate_analysis_structure(analysis):
                        logger.info(f"✅ JSON parsed successfully on attempt {attempt + 1}")
                        return analysis
                    else:
                        logger.warning(f"⚠️ Invalid structure on attempt {attempt + 1}")
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"❌ JSON parsing attempt {attempt + 1} failed: {e}")
                    if attempt == 2:  # Last attempt
                        logger.error(f"Response text: {response_text[:500]}...")
                
            # If all JSON parsing attempts fail, use fallback
            logger.warning("🔄 Using fallback template analysis")
            return await self._fallback_template_analysis(template_text, filename)
            
        except Exception as e:
            logger.error(f"❌ LLM template analysis failed: {e}")
            return await self._fallback_template_analysis(template_text, filename)

    def _fix_json_formatting(self, json_text: str) -> str:
        """
        Comprehensive JSON formatting fix for LLM responses
        """
        try:
            # Remove any markdown or extra formatting
            json_text = json_text.strip()
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.startswith('```'):
                json_text = json_text[3:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            
            # Fix common issues
            # 1. Remove any text before the first {
            first_brace = json_text.find('{')
            if first_brace > 0:
                json_text = json_text[first_brace:]
            
            # 2. Remove any text after the last }
            last_brace = json_text.rfind('}')
            if last_brace >= 0:
                json_text = json_text[:last_brace + 1]
            
            # 3. Fix unterminated strings
            lines = json_text.split('\n')
            fixed_lines = []
            in_string = False
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Count unescaped quotes
                quote_count = 0
                i = 0
                while i < len(line):
                    if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                        quote_count += 1
                    i += 1
                
                # If odd number of quotes, likely unterminated
                if quote_count % 2 == 1:
                    # Find the last quote and close it
                    if line.endswith(',') or line.endswith('{') or line.endswith('['):
                        line = line[:-1] + '"' + line[-1]
                    else:
                        line = line + '"'
                
                fixed_lines.append(line)
            
            json_text = '\n'.join(fixed_lines)
            
            # 4. Remove trailing commas before closing braces/brackets
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            # 5. Ensure proper structure
            if not json_text.startswith('{'):
                json_text = '{' + json_text
            if not json_text.endswith('}'):
                json_text = json_text + '}'
            
            return json_text
            
        except Exception as e:
            logger.warning(f"JSON fix failed: {e}")
            return json_text

    def _aggressive_json_fix(self, json_text: str) -> str:
        """
        Aggressive JSON fixing for stubborn cases
        """
        try:
            # Remove everything before first { and after last }
            start = json_text.find('{')
            end = json_text.rfind('}')
            if start >= 0 and end >= 0:
                json_text = json_text[start:end+1]
            
            # Replace problematic characters
            json_text = json_text.replace('\n', ' ')
            json_text = json_text.replace('\t', ' ')
            json_text = re.sub(r'\s+', ' ', json_text)
            
            # Fix unescaped quotes in values
            json_text = re.sub(r':\s*"([^"]*)"([^",}]*)"', r': "\1\2"', json_text)
            
            # Remove trailing commas
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            # Ensure proper array/object endings
            json_text = re.sub(r',\s*}', '}', json_text)
            json_text = re.sub(r',\s*]', ']', json_text)
            
            return json_text
            
        except Exception as e:
            logger.warning(f"Aggressive JSON fix failed: {e}")
            return json_text

    def _validate_analysis_structure(self, analysis: dict) -> bool:
        """
        Validate the analysis structure
        """
        try:
            # Check required keys
            if not isinstance(analysis, dict):
                return False
            
            if 'template_info' not in analysis or 'identified_fields' not in analysis:
                return False
            
            template_info = analysis['template_info']
            if not isinstance(template_info, dict):
                return False
            
            identified_fields = analysis['identified_fields']
            if not isinstance(identified_fields, list):
                return False
            
            # Validate each field
            for field in identified_fields:
                if not isinstance(field, dict):
                    return False
                required_keys = ['field_id', 'field_type', 'semantic_role']
                if not all(key in field for key in required_keys):
                    return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Validation failed: {e}")
            return False

    async def _fallback_template_analysis(
        self, 
        template_text: str, 
        filename: str
    ) -> Dict[str, Any]:
        """
        Fallback template analysis using pattern matching when LLM fails
        """
        import re
        
        # Look for common placeholder patterns
        patterns = {
            'underscores': r'_{3,}',  # Three or more underscores
            'brackets': r'\[([^\]]+)\]',  # Text in brackets
            'braces': r'\{([^}]+)\}',  # Text in braces
            'parentheses': r'\(([^)]*blank[^)]*)\)',  # Parentheses with "blank"
        }
        
        identified_fields = []
        field_counter = 0
        
        for pattern_name, pattern in patterns.items():
            matches = re.finditer(pattern, template_text, re.IGNORECASE)
            for match in matches:
                field_counter += 1
                field_id = f"field_{field_counter}"
                
                # Extract context around the match
                start = max(0, match.start() - 50)
                end = min(len(template_text), match.end() + 50)
                context = template_text[start:end].strip()
                
                # Try to guess field type and semantic role based on context
                field_type, semantic_role = self._guess_field_type(context)
                
                # Create contextual field_id
                contextual_field_id = f"{semantic_role}_{field_type}_{field_counter}" if semantic_role != "general" else f"{field_type}_{field_counter}"
                
                identified_fields.append({
                    "field_id": contextual_field_id,
                    "field_type": field_type,
                    "semantic_role": semantic_role,
                    "context": context,
                    "description": f"{semantic_role.title()} {field_type}" if semantic_role != "general" else f"Field requiring {field_type}",
                    "required": True,
                    "contextual_keywords": [semantic_role, field_type],
                    "placeholder_patterns": [match.group(0)]
                })
        
        return {
            "template_info": {
                "filename": filename,
                "estimated_fields": len(identified_fields),
                "template_type": "general_form"
            },
            "identified_fields": identified_fields
        }

    def _guess_field_type(self, context: str) -> tuple[str, str]:
        """
        Guess field type and semantic role based on context
        Returns (field_type, semantic_role)
        """
        context_lower = context.lower()
        
        # Determine semantic role
        semantic_role = "general"
        if any(word in context_lower for word in ['testator', 'deceased', 'deponent']):
            semantic_role = "testator"
        elif any(word in context_lower for word in ['witness', 'attestor', 'attesting']):
            semantic_role = "witness"
        elif any(word in context_lower for word in ['applicant', 'petitioner', 'plaintiff']):
            semantic_role = "applicant"
        elif any(word in context_lower for word in ['father', 'father\'s', 'paternal']):
            semantic_role = "father"
        elif any(word in context_lower for word in ['mother', 'mother\'s', 'maternal']):
            semantic_role = "mother"
        elif any(word in context_lower for word in ['spouse', 'husband', 'wife']):
            semantic_role = "spouse"
        elif any(word in context_lower for word in ['guardian', 'custodian']):
            semantic_role = "guardian"
        elif any(word in context_lower for word in ['beneficiary', 'heir', 'inheritor']):
            semantic_role = "beneficiary"
        
        # Determine field type
        field_type = "text"
        if any(word in context_lower for word in ['age', 'years old', 'aged', 'years']):
            field_type = 'age'
        elif any(word in context_lower for word in ['name', 'full name', 'first name', 'last name']):
            field_type = 'name'
        elif any(word in context_lower for word in ['date', 'day', 'month', 'year', 'birth', 'dob']) and 'age' not in context_lower:
            field_type = 'date'
        elif any(word in context_lower for word in ['address', 'street', 'city', 'state', 'residence']):
            field_type = 'address'
        elif any(word in context_lower for word in ['phone', 'telephone', 'mobile', 'contact']):
            field_type = 'phone'
        elif any(word in context_lower for word in ['email', 'e-mail', 'mail']):
            field_type = 'email'
        elif any(word in context_lower for word in ['signature', 'sign', 'signed']):
            field_type = 'signature'
        elif any(word in context_lower for word in ['number', 'amount', 'value']):
            field_type = 'number'
        
        return field_type, semantic_role

    def _get_suggestions_for_type(self, field_type: str) -> List[str]:
        """
        Get search suggestions based on field type
        """
        suggestions_map = {
            'name': ['full_name', 'first_name', 'last_name', 'legal_name', 'name'],
            'date': ['date', 'birth_date', 'current_date', 'today'],
            'address': ['address', 'home_address', 'mailing_address', 'street_address'],
            'phone': ['phone', 'mobile', 'telephone', 'contact_number'],
            'email': ['email', 'email_address', 'contact_email'],
            'signature': ['signature', 'full_name', 'name'],
            'number': ['age', 'number', 'amount', 'quantity'],
            'text': ['information', 'details', 'description']
        }
        return suggestions_map.get(field_type, ['information', 'details'])

    async def _fill_single_template(
        self,
        person_id: str,
        template: Dict[str, Any],
        device_id: str,
        batch_id: str,
        template_idx: int
    ) -> Dict[str, Any]:
        """
        Fill a single template using person data from Pinecone
        """
        try:
            template_analysis = template['template_analysis']
            template_path = template_analysis.get('template_path')
            filled_fields = {}
            
            # For each identified field, search for relevant data in Pinecone
            for field in template_analysis.get('identified_fields', []):
                field_id = field['field_id']
                field_type = field['field_type']
                semantic_role = field.get('semantic_role', 'general')
                contextual_keywords = field.get('contextual_keywords', [])
                description = field.get('description', '')
                
                # Backward compatibility: if no contextual_keywords, use suggestions
                if not contextual_keywords:
                    suggestions = field.get('suggestions', [])
                    contextual_keywords = suggestions
                
                # Generate contextual search queries
                search_queries = self._generate_contextual_search_queries(
                    field_type, 
                    semantic_role, 
                    contextual_keywords, 
                    description
                )
                
                # Use contextual search if semantic_role is available, otherwise fall back
                if semantic_role != 'general' and hasattr(self, '_search_person_data_contextual'):
                    field_value = await self._search_person_data_contextual(
                        person_id, 
                        search_queries, 
                        device_id,
                        field_type,
                        semantic_role
                    )
                else:
                    # Fallback to original search for compatibility
                    field_value = await self._search_person_data(
                        person_id, 
                        search_queries, 
                        device_id,
                        field_type
                    )
                
                filled_fields[field_id] = {
                    'value': field_value,
                    'field_info': field,
                    'found': bool(field_value)
                }
            
            # Generate filled document based on file type
            filename = f"filled_{batch_id}_{template_idx}_{template_analysis['template_info']['filename']}"
            file_path = self.output_dir / filename
            
            if template_path and Path(template_path).suffix.lower() == '.docx':
                # Handle Word documents properly
                await self._fill_word_document(
                    template_path,
                    file_path,
                    template_analysis,
                    filled_fields
                )
            else:
                # Handle other document types or create new document
                await self._create_filled_document(
                    file_path,
                    template_analysis,
                    filled_fields,
                    template_idx
                )
            
            return {
                'success': True,
                'template_index': template_idx,
                'filename': filename,
                'file_path': str(file_path),
                'download_url': f"/api/download/interpreted/{filename}",
                'filled_fields': filled_fields,
                'fields_found': sum(1 for f in filled_fields.values() if f['found']),
                'total_fields': len(filled_fields)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to fill single template: {e}")
            return {
                'success': False,
                'error': str(e),
                'template_index': template_idx
            }
    
    def _generate_search_queries(
        self, 
        field_type: str, 
        suggestions: List[str], 
        description: str
    ) -> List[str]:
        """
        Generate search queries for finding relevant person data
        """
        queries = []
        
        # Add suggestion-based queries
        for suggestion in suggestions:
            clean_suggestion = suggestion.replace('_', ' ').strip()
            if clean_suggestion:
                queries.append(clean_suggestion)
        
        # Add type-based queries with better coverage
        type_queries = {
            'name': ['name', 'full name', 'first name', 'last name', 'person name', 'applicant name'],
            'address': ['address', 'street address', 'home address', 'residence', 'location', 'plot', 'area'],
            'phone': ['phone number', 'telephone', 'mobile', 'contact number', 'phone'],
            'email': ['email address', 'email', 'e-mail', 'electronic mail'],
            'date': ['date', 'date of birth', 'birth date', 'birthday', 'DOB', 'birth'],
            'signature': ['signature', 'sign', 'signed by'],
            'age': ['age', 'years old'],
            'father': ['father name', 'father', 'parent'],
            'today': ['today date', 'current date', 'date'],
            'text': ['information', 'details', 'data']
        }
        
        # Get queries for this field type
        if field_type.lower() in type_queries:
            queries.extend(type_queries[field_type.lower()])
        
        # Also try to match common field type variations
        for field_variant in ['name', 'address', 'phone', 'email', 'date']:
            if field_variant in field_type.lower():
                queries.extend(type_queries.get(field_variant, []))
        
        # Add description-based queries
        if description:
            desc_words = description.lower().split()
            for word in desc_words:
                if len(word) > 3 and word not in ['the', 'and', 'for', 'with', 'this', 'that']:
                    queries.append(word)
        
        # Remove duplicates and empty queries
        unique_queries = []
        for q in queries:
            if q and q not in unique_queries:
                unique_queries.append(q)
        
        return unique_queries[:10]  # Limit to first 10 queries

    async def _search_person_data(
        self,
        person_id: str,
        search_queries: List[str],
        device_id: str,  # Keep for compatibility but not used for person search
        field_type: str
    ) -> Optional[str]:
        """
        Search for person data using the separate person storage
        """
        try:
            logger.info(f"🔍 Searching person data for {field_type} with queries: {search_queries}")
            best_match = None
            best_score = 0.0
            
            for query in search_queries:
                try:
                    logger.info(f"🔍 Processing query: '{query}'")
                    
                    # Generate embedding for query
                    query_embedding = await self.gemini_service.get_embedding(query)
                    logger.info(f"✅ Generated embedding for query: '{query}'")
                    
                    # Search in person storage
                    results = await self._search_person_vectors(
                        person_id,
                        query_embedding,
                        top_k=5
                    )
                    
                    logger.info(f"📊 Person storage returned {len(results)} results for query '{query}'")
                    
                    # Process results
                    for i, match in enumerate(results):
                        logger.info(f"📋 Result {i+1}: score={match['score']:.3f}, text preview='{match.get('text', '')[:100]}...'")
                        
                        if match['score'] > best_score and match['score'] > 0.1:  # Minimum threshold
                            best_score = match['score']
                            # Extract value from metadata or text
                            if 'field_value' in match['metadata']:
                                best_match = match['metadata']['field_value']
                                logger.info(f"✅ Found field_value in metadata: '{best_match}'")
                            else:
                                # Extract value from text using improved extraction
                                best_match = await self._extract_value_from_text(
                                    match['text'], 
                                    field_type, 
                                    query
                                )
                                logger.info(f"🤖 Extracted value: '{best_match}' for query '{query}'")
                    
                except Exception as e:
                    logger.warning(f"❌ Query '{query}' failed: {e}")
                    continue
            
            # Post-process the value based on field type
            if best_match:
                final_value = self._format_field_value(best_match, field_type)
                logger.info(f"✅ Final formatted value for {field_type}: '{final_value}' (score: {best_score:.3f})")
                return final_value
            else:
                logger.warning(f"❌ No data found for {field_type} with person_id: {person_id}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to search person data: {e}")
            return None

    def _generate_contextual_search_queries(
        self, 
        field_type: str, 
        semantic_role: str,
        contextual_keywords: List[str], 
        description: str
    ) -> List[str]:
        """
        Generate contextual search queries that understand semantic roles
        """
        queries = []
        
        # Role-specific queries based on semantic understanding
        role_specific_queries = {
            'testator': {
                'name': ['testator name', 'deceased name', 'deponent name', 'person making will'],
                'date': ['testator date of birth', 'deceased birth date', 'testator DOB'],
                'address': ['testator address', 'deceased residence', 'testator home'],
                'age': ['testator age', 'deceased age', 'age of testator']
            },
            'witness': {
                'name': ['witness name', 'attesting witness', 'witness full name'],
                'date': ['witness date of birth', 'witness DOB', 'witness birth date'],
                'address': ['witness address', 'witness residence', 'witness home'],
                'age': ['witness age', 'age of witness', 'witness years']
            },
            'applicant': {
                'name': ['applicant name', 'petitioner name', 'application by'],
                'date': ['applicant date of birth', 'applicant DOB'],
                'address': ['applicant address', 'applicant residence'],
                'age': ['applicant age', 'age of applicant']
            },
            'father': {
                'name': ['father name', 'father\'s name', 'paternal name', 'parent name'],
                'date': ['father date of birth', 'father DOB'],
                'address': ['father address', 'paternal address'],
                'age': ['father age', 'paternal age']
            },
            'general': {
                'name': ['name', 'full name', 'person name'],
                'date': ['date of birth', 'birth date', 'DOB'],
                'address': ['address', 'residence', 'home address'],
                'age': ['age', 'years old']
            }
        }
        
        # Get role-specific queries
        if semantic_role in role_specific_queries and field_type in role_specific_queries[semantic_role]:
            queries.extend(role_specific_queries[semantic_role][field_type])
        elif field_type in role_specific_queries['general']:
            # Fallback to general queries
            queries.extend(role_specific_queries['general'][field_type])
        
        # Add contextual keywords
        for keyword in contextual_keywords:
            if keyword and keyword not in queries:
                queries.append(keyword)
                # Combine with field type
                combined = f"{keyword} {field_type}".strip()
                if combined not in queries:
                    queries.append(combined)
        
        # Add basic field type queries as fallback
        basic_queries = {
            'name': ['name', 'full name'],
            'address': ['address', 'residence'],
            'date': ['date', 'birth date'],
            'phone': ['phone', 'mobile'],
            'email': ['email'],
            'age': ['age', 'years'],
            'number': ['number', 'value']
        }
        
        if field_type in basic_queries:
            for query in basic_queries[field_type]:
                if query not in queries:
                    queries.append(query)
        
        # Remove duplicates and limit
        unique_queries = []
        for q in queries:
            if q and q not in unique_queries:
                unique_queries.append(q)
        
        return unique_queries[:8]  # Limit for performance

    async def _search_person_data_contextual(
        self,
        person_id: str,
        search_queries: List[str],
        device_id: str,
        field_type: str,
        semantic_role: str
    ) -> Optional[str]:
        """
        Contextual search that considers semantic roles for better accuracy
        """
        try:
            logger.info(f"🎯 Contextual search for {semantic_role} {field_type} with queries: {search_queries}")
            best_match = None
            best_score = 0.0
            
            for query in search_queries:
                try:
                    logger.info(f"🔍 Processing contextual query: '{query}' for {semantic_role}")
                    
                    # Generate embedding for query
                    query_embedding = await self.gemini_service.get_embedding(query)
                    
                    # Search in person storage
                    results = await self._search_person_vectors(
                        person_id,
                        query_embedding,
                        top_k=5
                    )
                    
                    logger.info(f"📊 Found {len(results)} results for contextual query '{query}'")
                    
                    # Process results with semantic role consideration
                    for i, match in enumerate(results):
                        context_score = match['score']
                        
                        # Boost score if the result text contains role-specific keywords
                        text_content = match.get('text', '').lower()
                        role_boost = 0.0
                        
                        if semantic_role != 'general':
                            role_keywords = {
                                'testator': ['testator', 'deceased', 'deponent'],
                                'witness': ['witness', 'attesting', 'attestor'],
                                'applicant': ['applicant', 'petitioner'],
                                'father': ['father', 'paternal', 'parent']
                            }
                            
                            if semantic_role in role_keywords:
                                for keyword in role_keywords[semantic_role]:
                                    if keyword in text_content:
                                        role_boost = 0.1
                                        break
                        
                        adjusted_score = context_score + role_boost
                        
                        logger.info(f"📋 Result {i+1}: score={context_score:.3f}, adjusted={adjusted_score:.3f}, role={semantic_role}")
                        
                        if adjusted_score > best_score and adjusted_score > 0.1:
                            best_score = adjusted_score
                            
                            # Extract value using improved methods
                            if 'field_value' in match['metadata']:
                                best_match = match['metadata']['field_value']
                                logger.info(f"✅ Found contextual field_value: '{best_match}'")
                            else:
                                best_match = await self._extract_value_from_text(
                                    match['text'], 
                                    field_type, 
                                    query
                                )
                                logger.info(f"🎯 Contextually extracted: '{best_match}' for {semantic_role} {field_type}")
                    
                except Exception as e:
                    logger.warning(f"❌ Contextual query '{query}' failed: {e}")
                    continue
            
            # Format the final value
            if best_match:
                final_value = self._format_field_value(best_match, field_type)
                logger.info(f"✅ Final contextual value for {semantic_role} {field_type}: '{final_value}' (score: {best_score:.3f})")
                return final_value
            else:
                logger.warning(f"❌ No contextual data found for {semantic_role} {field_type} with person_id: {person_id}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed contextual search: {e}")
            return None
    
    async def _extract_value_from_text(
        self, 
        text: str, 
        field_type: str, 
        query: str
    ) -> Optional[str]:
        """
        Use LLM to extract specific value from text
        """
        # Try regex-based extraction first for common patterns
        regex_result = self._extract_with_regex(text, field_type, query)
        if regex_result:
            logger.info(f"🎯 Regex extracted for {field_type}: '{regex_result}'")
            return regex_result
        
        # Fallback to LLM extraction
        prompt = f"""
Extract ONLY the {field_type} information from this text.

Query: "{query}"
Text: {text}

Return ONLY the exact value, no explanation. Examples:
- For name query: "Arun Yadav" (not "Name: Arun Yadav")
- For address query: "Plot No 45, Industrial Area Phase II, Panchkula, Haryana"
- For phone query: "+91-9876543210"
- For email query: "arun@example.com"
- For date query: "25/08/1990"

Extract only the {field_type} value:"""

        try:
            response = await self.gemini_service.generate_response(
                prompt=prompt,
                max_tokens=100,
                temperature=0.0
            )
            
            extracted_value = response.strip()
            # Clean up common LLM artifacts
            extracted_value = extracted_value.replace('"', '').replace("'", '').strip()
            
            if extracted_value and extracted_value.lower() not in ["not found", "none", "n/a", "not available"]:
                logger.info(f"🤖 LLM extracted for {field_type}: '{extracted_value}'")
                return extracted_value
            
        except Exception as e:
            logger.error(f"❌ LLM extraction failed: {e}")
        
        return None

    def _extract_with_regex(self, text: str, field_type: str, query: str) -> Optional[str]:
        """
        Extract values using regex patterns for common field types
        """
        import re
        
        try:
            # Name extraction
            if field_type.lower() in ['name', 'full_name', 'first_name', 'last_name']:
                # Look for "Name: value" pattern (stop at Father or next field)
                name_match = re.search(r'Name:\s*([A-Za-z\s]+?)(?:\s+Father|\s+Address|$|\n)', text, re.IGNORECASE)
                if name_match:
                    return name_match.group(1).strip()
                
                # Look for "Full Name: value" pattern
                name_match = re.search(r'Full\s*Name:\s*([A-Za-z\s]+?)(?:\s+|$|\n)', text, re.IGNORECASE)
                if name_match:
                    return name_match.group(1).strip()
            
            # Address extraction - more precise
            elif field_type.lower() in ['address', 'street_address', 'home_address']:
                # Look for "Address: value" pattern (stop at Age)
                addr_match = re.search(r'Address:\s*(.*?)(?:\s+Age)', text, re.IGNORECASE)
                if addr_match:
                    address = addr_match.group(1).strip()
                    return address
                
                # Fallback pattern for plot/area style addresses
                plot_match = re.search(r'Plot\s+No\s+\d+[^A]+?(?=\s+Age|\s+Phone|\s+Email|$)', text, re.IGNORECASE)
                if plot_match:
                    return plot_match.group().strip()
            
            # Phone extraction
            elif field_type.lower() in ['phone', 'telephone', 'mobile', 'contact']:
                # Look for phone patterns
                phone_match = re.search(r'(?:Phone|Mobile|Contact):\s*([+]?[\d\s\-\(\)]+)', text, re.IGNORECASE)
                if phone_match:
                    return phone_match.group(1).strip()
                
                # Look for standalone phone numbers
                phone_match = re.search(r'[+]?[\d]{10,}', text)
                if phone_match:
                    return phone_match.group().strip()
            
            # Date extraction - more precise
            elif field_type.lower() in ['date', 'birth_date', 'dob', 'date_of_birth']:
                # Look for "Date of Birth: value" pattern
                date_match = re.search(r'Date\s*of\s*Birth:\s*(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})', text, re.IGNORECASE)
                if date_match:
                    return date_match.group(1).strip()
                
                # Look for standalone dates in DD/MM/YYYY format
                date_match = re.search(r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b', text)
                if date_match:
                    return date_match.group(1).strip()
            
            # Age extraction
            elif field_type.lower() in ['age']:
                age_match = re.search(r'Age:\s*(\d+)', text, re.IGNORECASE)
                if age_match:
                    return age_match.group(1).strip()
            
            # Father name extraction
            elif field_type.lower() in ['father', 'father_name', 'parent']:
                father_match = re.search(r'Father\s+Name:\s*([A-Za-z\s]+?)(?:\s+Address|\s+Age|$|\n)', text, re.IGNORECASE)
                if father_match:
                    return father_match.group(1).strip()
            
            # Email extraction
            elif field_type.lower() in ['email', 'e-mail', 'email_address']:
                email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
                if email_match:
                    return email_match.group().strip()
            
        except Exception as e:
            logger.warning(f"❌ Regex extraction failed for {field_type}: {e}")
        
        return None
    
    def _format_field_value(self, value: str, field_type: str) -> str:
        """
        Format field value according to field type
        """
        if not value:
            return ""
        
        value = value.strip()
        
        if field_type == 'date':
            # Try to standardize date format
            try:
                from datetime import datetime
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y%m%d']:
                    try:
                        date_obj = datetime.strptime(value, fmt)
                        return date_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
            except:
                pass
        
        elif field_type == 'phone':
            # Clean phone number
            import re
            digits = re.sub(r'\D', '', value)
            if len(digits) == 10:
                return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
            elif len(digits) == 11 and digits[0] == '1':
                return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        
        elif field_type == 'name':
            # Capitalize names properly
            return value.title()
        
        return value
    
    async def _generate_document_content(
        self,
        template_analysis: Dict[str, Any],
        filled_fields: Dict[str, Any],
        template_idx: int
    ) -> str:
        """
        Generate the final filled document content
        """
        prompt = f"""
You are a professional document formatter. Create a complete, well-formatted document using the template analysis and filled field data provided.

Template Information:
{json.dumps(template_analysis['template_info'], indent=2)}

Identified Fields and Values:
{json.dumps({k: v['value'] for k, v in filled_fields.items()}, indent=2)}

Field Details:
{json.dumps({k: v['field_info'] for k, v in filled_fields.items()}, indent=2)}

Instructions:
1. Create a professional, complete document
2. Replace all identified blank spaces with the appropriate filled values
3. Maintain proper formatting and structure
4. Include all necessary legal language and clauses
5. Ensure the document flows naturally and reads professionally
6. If a field value is missing, use "[FIELD_NAME_TO_BE_FILLED]" as placeholder

Generate the complete filled document:
"""
        
        try:
            response = await self.gemini_service.generate_response(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.2
            )
            
            # Add header with metadata
            header = f"""
Generated Filled Document #{template_idx + 1}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Template: {template_analysis['template_info']['filename']}
Fields filled: {sum(1 for f in filled_fields.values() if f['found'])}/{len(filled_fields)}

{'-' * 80}

"""
            
            return header + response
            
        except Exception as e:
            logger.error(f"❌ Failed to generate document content: {e}")
            # Return fallback content
            return f"""
Generated Filled Document #{template_idx + 1}
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Template: {template_analysis['template_info']['filename']}

ERROR: Could not generate document content due to: {str(e)}

Field Values:
{json.dumps({k: v['value'] for k, v in filled_fields.items()}, indent=2)}
"""
    
    async def _create_batch_download(
        self,
        filled_documents: List[Dict[str, Any]],
        batch_id: str
    ) -> str:
        """
        Create a zip file containing all filled documents
        """
        try:
            zip_filename = f"batch_{batch_id}_filled_documents.zip"
            zip_path = self.output_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for doc in filled_documents:
                    if doc['success']:
                        zipf.write(doc['file_path'], doc['filename'])
            
            return f"/api/download/interpreted/{zip_filename}"
            
        except Exception as e:
            logger.error(f"❌ Failed to create batch download: {e}")
            return ""
    
    def _json_to_chunks(self, data: Dict[str, Any], person_id: str) -> List[Dict[str, Any]]:
        """
        Convert JSON data to text chunks for embedding
        """
        chunks = []
        
        def process_value(key: str, value: Any, prefix: str = ""):
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    process_value(sub_key, sub_value, full_key)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    process_value(f"{key}[{i}]", item, prefix)
            else:
                # Create chunk for this key-value pair
                chunk = {
                    'text': f"{full_key}: {str(value)}",
                    'metadata': {
                        'person_id': person_id,
                        'field_name': full_key,
                        'field_value': str(value),
                        'chunk_type': 'personal_data'
                    }
                }
                chunks.append(chunk)
        
        for key, value in data.items():
            process_value(key, value)
        
        return chunks
    
    def _text_to_chunks(
        self, 
        text: str, 
        person_id: str, 
        device_id: str, 
        filename: str
    ) -> List[Dict[str, Any]]:
        """
        Convert text to chunks for embedding
        """
        chunks = []
        
        # Split text into sentences/lines
        lines = text.split('\n')
        current_chunk = ""
        chunk_size = 500  # characters
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if len(current_chunk) + len(line) > chunk_size and current_chunk:
                # Save current chunk
                chunk = {
                    'text': current_chunk.strip(),
                    'metadata': {
                        'person_id': person_id,
                        'device_id': device_id,
                        'source_file': filename,
                        'chunk_type': 'personal_data'
                    }
                }
                chunks.append(chunk)
                current_chunk = line
            else:
                current_chunk += f" {line}"
        
        # Add final chunk
        if current_chunk.strip():
            chunk = {
                'text': current_chunk.strip(),
                'metadata': {
                    'person_id': person_id,
                    'device_id': device_id,
                    'source_file': filename,
                    'chunk_type': 'personal_data'
                }
            }
            chunks.append(chunk)
        
        return chunks

    async def _fill_word_document(
        self,
        template_path: str,
        output_path: Path,
        template_analysis: Dict[str, Any],
        filled_fields: Dict[str, Any]
    ):
        """
        Fill a Word document template by replacing placeholders with field-specific intelligent matching
        """
        try:
            # Copy the original template to output location
            shutil.copy2(template_path, output_path)
            
            # Open the document
            doc = Document(str(output_path))
            
            logger.info(f"🔄 Filling Word document with {len(filled_fields)} fields")
            
            # Extract all text to analyze patterns
            all_text = self._extract_all_text_from_doc(doc)
            
            # Position-based intelligent replacement mapping
            field_replacements = {}
            
            # Step 1: Find all placeholders in document order
            import re
            placeholder_matches = list(re.finditer(r'\.{5,}', all_text))
            
            logger.info(f"🔄 Found {len(placeholder_matches)} placeholders in document order")
            
            # Step 2: Create a priority-ordered list of fields to fill
            field_priority_list = []
            for field_id, field_data in filled_fields.items():
                field_info = field_data['field_info']
                field_value = field_data['value']
                
                # Only process fields that have actual meaningful data
                if not field_value or field_value.startswith('[') or 'TO_BE_FILLED' in str(field_value):
                    logger.info(f"⏭️ Skipping field {field_id} - no meaningful data found")
                    continue
                
                priority = self._calculate_field_priority(field_info)
                field_priority_list.append({
                    'field_id': field_id,
                    'field_data': field_data,
                    'priority': priority,
                    'semantic_role': field_info.get('semantic_role', 'general'),
                    'field_type': field_info.get('field_type', 'text')
                })
            
            # Sort by priority (highest first)
            field_priority_list.sort(key=lambda x: x['priority'], reverse=True)
            
            # Step 3: Assign placeholders based on document structure and priority
            assigned_placeholders = set()
            successful_assignments = 0
            position_to_field = {}  # Maps placeholder position to field data
            
            for field_entry in field_priority_list:
                field_id = field_entry['field_id']
                field_value = field_entry['field_data']['value']
                semantic_role = field_entry['semantic_role']
                field_type = field_entry['field_type']
                
                logger.info(f"🎯 Assigning placeholder for {field_id} (role: {semantic_role}, type: {field_type}, value: '{field_value}')")
                
                # Find the best placeholder for this field based on context
                best_placeholder_idx = None
                best_score = 0
                
                for i, match in enumerate(placeholder_matches):
                    if i in assigned_placeholders:
                        continue  # Already used
                    
                    # Analyze context around this placeholder
                    start = max(0, match.start() - 100)
                    end = min(len(all_text), match.end() + 100)
                    context = all_text[start:end].lower()
                    
                    # Score this placeholder for the current field
                    score = self._score_placeholder_for_field(context, semantic_role, field_type, i)
                    
                    if score > best_score:
                        best_score = score
                        best_placeholder_idx = i
                
                # Assign the best placeholder
                if best_placeholder_idx is not None:
                    position_to_field[best_placeholder_idx] = {
                        'value': field_value,
                        'field_id': field_id,
                        'pattern': placeholder_matches[best_placeholder_idx].group(),
                        'score': best_score
                    }
                    assigned_placeholders.add(best_placeholder_idx)
                    successful_assignments += 1
                    logger.info(f"✅ Assigned placeholder #{best_placeholder_idx+1} '{placeholder_matches[best_placeholder_idx].group()[:20]}...' to {field_id} -> '{field_value}' (score: {best_score})")
                else:
                    logger.warning(f"⚠️ No suitable placeholder found for {field_id}")
            
            logger.info(f"🔄 Position-based assignment: {successful_assignments} placeholders assigned out of {len(field_priority_list)} fields")
            
            # Step 4: Apply replacements using sequential position-based approach
            replacement_count = 0
            
            # Process each placeholder position in document order
            for position_idx in sorted(position_to_field.keys()):
                field_data = position_to_field[position_idx]
                pattern = field_data['pattern']
                value = field_data['value']
                field_id = field_data['field_id']
                
                # Apply replacement to paragraphs
                for paragraph in doc.paragraphs:
                    original_text = paragraph.text
                    if pattern in original_text:
                        new_text = original_text.replace(pattern, str(value), 1)  # Replace only first occurrence
                        if new_text != original_text:
                            paragraph.clear()
                            paragraph.add_run(new_text)
                            replacement_count += 1
                            logger.info(f"📝 Position {position_idx+1}: Replaced '{pattern}' with '{value}' (field: {field_id})")
                            break  # Move to next position after replacing
                
                # Apply replacement to tables
                replaced_in_table = False
                for table in doc.tables:
                    if replaced_in_table:
                        break
                    for row in table.rows:
                        if replaced_in_table:
                            break
                        for cell in row.cells:
                            if replaced_in_table:
                                break
                            for paragraph in cell.paragraphs:
                                original_text = paragraph.text
                                if pattern in original_text:
                                    new_text = original_text.replace(pattern, str(value), 1)
                                    if new_text != original_text:
                                        paragraph.clear()
                                        paragraph.add_run(new_text)
                                        replacement_count += 1
                                        logger.info(f"📝 Position {position_idx+1}: Replaced '{pattern}' with '{value}' in table (field: {field_id})")
                                        replaced_in_table = True
                                        break
            
            # Save the document
            doc.save(str(output_path))
            logger.info(f"✅ Document saved with {replacement_count} total replacements made")
            
        except Exception as e:
            logger.error(f"❌ Failed to fill Word document: {e}")
            # Fallback to creating a new document
            await self._create_filled_document(output_path, template_analysis, filled_fields, 0)

    def _find_field_specific_placeholders(
        self, 
        text: str, 
        field_type: str, 
        field_info: Dict[str, Any], 
        field_value: str
    ) -> List[str]:
        """
        Find placeholders that are specific to a particular field type
        """
        import re
        placeholders = []
        
        # Get field suggestions and context
        suggestions = field_info.get('suggestions', [])
        context = field_info.get('context', '').lower()
        description = field_info.get('description', '').lower()
        
        # Create keyword sets for different field types
        field_keywords = {
            'name': ['name', 'applicant', 'person', 'individual', 'deponent'],
            'address': ['address', 'residence', 'location', 'plot', 'area', 'street'],
            'date': ['date', 'birth', 'dob', 'born', 'day', 'month', 'year'],
            'phone': ['phone', 'mobile', 'telephone', 'contact', 'number'],
            'email': ['email', 'mail', 'electronic'],
            'age': ['age', 'years', 'old'],
            'father': ['father', 'parent', 'guardian'],
            'signature': ['signature', 'sign', 'signed']
        }
        
        # Get relevant keywords for this field type
        relevant_keywords = []
        if field_type in field_keywords:
            relevant_keywords.extend(field_keywords[field_type])
        
        # Add suggestion keywords
        for suggestion in suggestions:
            relevant_keywords.extend(suggestion.lower().split())
        
        # Remove duplicates
        relevant_keywords = list(set(relevant_keywords))
        
        logger.info(f"� Looking for {field_type} placeholders with keywords: {relevant_keywords}")
        
        # Find placeholders with field-specific patterns
        patterns = [
            r'_{3,}',  # Multiple underscores
            r'\[([^\]]*)\]',  # Square brackets
            r'\{([^}]*)\}',  # Curly braces
            r'\.{3,}',  # Multiple dots
            r'-{3,}',  # Multiple dashes
            r'\([^)]*\)',  # Parentheses
            r'\b35\b',  # Specific number 35 (common placeholder in your documents)
            r'\b\d{2}\b\.{3,}',  # Numbers followed by dots
            r'\d{2}\.{2,}',  # Numbers with multiple dots
            r'\b\d{1,2}\s*\.{2,}',  # Numbers with dots and optional spaces
            r'3535\.{2,}',  # Specific pattern like 3535....
            r'\b35\.{2,}'  # 35 followed by dots
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                placeholder_text = match.group(0)
                placeholder_context = text[max(0, match.start()-50):match.end()+50].lower()
                
                # Check if this placeholder is relevant to the field type
                is_relevant = False
                
                # Method 1: Check if any relevant keywords appear near the placeholder
                for keyword in relevant_keywords:
                    if keyword in placeholder_context:
                        is_relevant = True
                        logger.info(f"✅ Found relevant placeholder '{placeholder_text}' (keyword: '{keyword}' in context)")
                        break
                
                # Enhanced contextual matching for legal documents
                field_semantic_role = field_info.get('semantic_role', 'general')
                
                if not is_relevant:
                    # For testator names - look for "executed by Shri" pattern
                    if (field_type == 'name' and field_semantic_role == 'testator' and 
                        any(term in placeholder_context for term in ['executed by shri', 'testator shri'])):
                        is_relevant = True
                        logger.info(f"✅ Found testator name placeholder '{placeholder_text}' by legal context")
                    
                    # For testator father names - look for "son of" after testator context
                    elif (field_type == 'name' and field_semantic_role in ['father_of_testator', 'father'] and 
                          any(term in placeholder_context for term in ['shri', 'son of']) and
                          any(term in placeholder_context for term in ['executed', 'will', 'testator'])):
                        is_relevant = True
                        logger.info(f"✅ Found testator father name placeholder '{placeholder_text}' by legal context")
                    
                    # For testator address - look for "resident of" after testator context
                    elif (field_type == 'address' and field_semantic_role == 'testator' and 
                          any(term in placeholder_context for term in ['resident of']) and
                          any(term in placeholder_context for term in ['will', 'executed', 'testator'])):
                        is_relevant = True
                        logger.info(f"✅ Found testator address placeholder '{placeholder_text}' by legal context")
                    
                    # For witness A details - look for "A, aged about"
                    elif (field_semantic_role == 'witness_a' and 
                          any(term in placeholder_context for term in ['a, aged about', 'affidavit of a'])):
                        is_relevant = True
                        logger.info(f"✅ Found witness A placeholder '{placeholder_text}' by legal context")
                    
                    # For witness B details - look for "B, aged about"
                    elif (field_semantic_role == 'witness_b' and 
                          any(term in placeholder_context for term in ['b, aged about', 'and b, aged'])):
                        is_relevant = True
                        logger.info(f"✅ Found witness B placeholder '{placeholder_text}' by legal context")
                    
                    # For will execution dates - look for "executed his will on" or "will on"
                    elif (field_type == 'date' and 
                          any(term in placeholder_context for term in ['executed his will on', 'will on', 'executed on'])):
                        is_relevant = True
                        logger.info(f"✅ Found will execution date placeholder '{placeholder_text}' by legal context")
                    
                    # For sub-registrar - look for "Sub-Registrar"
                    elif (field_semantic_role == 'sub_registrar' and 
                          any(term in placeholder_context for term in ['sub-registrar', 'before the sub'])):
                        is_relevant = True
                        logger.info(f"✅ Found sub-registrar placeholder '{placeholder_text}' by legal context")
                    
                    # For verification location - look for "Verified at"
                    elif (field_type in ['location', 'text'] and 
                          any(term in placeholder_context for term in ['verified at'])):
                        is_relevant = True
                        logger.info(f"✅ Found verification location placeholder '{placeholder_text}' by legal context")
                
                # Method 3: General position matching
                if not is_relevant and field_type == 'name':
                    if re.search(r'\b(name|applicant|deponent|shri)\s*[:\-]?\s*' + re.escape(placeholder_text), placeholder_context, re.IGNORECASE):
                        is_relevant = True
                        logger.info(f"✅ Found name placeholder '{placeholder_text}' by general position")
                
                elif not is_relevant and field_type == 'date':
                    if re.search(r'\b(date|born|birth|day|on)\s*[:\-]?\s*' + re.escape(placeholder_text), placeholder_context, re.IGNORECASE):
                        is_relevant = True
                        logger.info(f"✅ Found date placeholder '{placeholder_text}' by general position")
                
                elif not is_relevant and field_type == 'address':
                    # Look for address-like positions
                    if re.search(r'\b(address|residence|plot)\s*[:\-]?\s*' + re.escape(placeholder_text), placeholder_context, re.IGNORECASE):
                        is_relevant = True
                        logger.info(f"✅ Found address placeholder '{placeholder_text}' by position")
                
                if is_relevant and len(placeholder_text) < 50:  # Reasonable length
                    placeholders.append(placeholder_text)
        
        # If no specific placeholders found, use a more intelligent approach
        if not placeholders:
            logger.warning(f"⚠️ No specific placeholders found for {field_type}, using general patterns")
            
            # For the document format you showed, try to find "35" patterns contextually
            if field_type in ['name', 'date', 'address', 'age']:
                # Look for "35" patterns near relevant keywords
                context_patterns = {
                    'name': [r'(Shri\s+35)', r'(by\s+Shri\s+35)', r'(deponents?\s+35)', r'(A,\s*aged\s*about\s*35)', r'(B,\s*aged\s*about\s*35)'],
                    'age': [r'(aged\s+about\s+35)', r'(aged\s+35)'],
                    'date': [r'(on\s+35)', r'(executed\s+.*\s+on\s+35)', r'(day\s+of\s+35)'],
                    'address': [r'(resident\s+of\s+35)', r'(of\s+35\.+)']
                }
                
                if field_type in context_patterns:
                    for pattern in context_patterns[field_type]:
                        matches = re.findall(pattern, text, re.IGNORECASE)
                        if matches:
                            # Extract just the "35" part
                            placeholders.extend(['35'])
                            logger.info(f"✅ Found contextual {field_type} placeholder: 35")
                            break
            
            # If still no placeholders, try general patterns but limit to first occurrence
            if not placeholders:
                general_patterns = re.findall(r'_{3,}', text)
                if general_patterns:
                    placeholders.extend(general_patterns[:1])  # Take only the first one to avoid duplicates
        
        return list(set(placeholders))  # Remove duplicates

    def _calculate_field_priority(self, field_info: Dict[str, Any]) -> int:
        """
        Calculate priority for field assignment to resolve conflicts
        Higher priority fields get first choice of placeholders
        """
        priority = 0
        field_type = field_info.get('field_type', '').lower()
        semantic_role = field_info.get('semantic_role', 'general')
        field_id = field_info.get('field_id', '')
        
        # Priority based on semantic role importance
        role_priorities = {
            'testator': 100,  # Highest priority - main subject
            'father_of_testator': 90,
            'witness_a': 80,
            'father_of_witness_a': 70, 
            'witness_b': 60,
            'father_of_witness_b': 50,
            'sub_registrar': 40,
            'general': 30
        }
        
        priority += role_priorities.get(semantic_role, 20)
        
        # Additional priority based on field type importance
        type_priorities = {
            'name': 20,
            'address': 15,
            'date': 10,
            'age': 8,
            'location': 5,
            'text': 1
        }
        
        priority += type_priorities.get(field_type, 1)
        
        # Boost priority for certain key field patterns
        if 'testator_name' in field_id:
            priority += 50  # Testator name is most important
        elif 'execution_date' in field_id:
            priority += 30  # Will execution dates are important
        elif '_1' in field_id:  # First occurrence of field type gets priority
            priority += 10
        
        return priority

    def _score_placeholder_for_field(self, context: str, semantic_role: str, field_type: str, position: int) -> float:
        """
        Score how well a placeholder matches a field based on context and position
        Higher score = better match
        """
        score = 0.0
        
        # Base score based on position (earlier positions get slight preference for key fields)
        if semantic_role == 'testator' and field_type == 'name':
            score += max(0, 10 - position * 0.5)  # Testator name should be early
        elif semantic_role == 'sub_registrar':
            score += max(0, 15 - position * 2)  # Sub-registrar should be first
        
        # Context-based scoring
        context_keywords = {
            'sub_registrar': {
                'keywords': ['sub-registrar', 'before the sub', 'registrar'],
                'weight': 10
            },
            'testator': {
                'keywords': ['executed by shri', 'testator', 'will executed by', 'matter of registration'],
                'weight': 8
            },
            'father_of_testator': {
                'keywords': ['son of', 'daughter of'] + (['executed', 'testator', 'will'] if position < 10 else []),
                'weight': 7
            },
            'witness_a': {
                'keywords': ['affidavit of a', 'a, aged about', 'aged about'],
                'weight': 6
            },
            'witness_b': {
                'keywords': ['and b, aged', 'b, aged about'],
                'weight': 6
            },
            'father_of_witness_a': {
                'keywords': ['son of shri'] + (['affidavit', 'witness'] if position < 15 else []),
                'weight': 5
            },
            'father_of_witness_b': {
                'keywords': ['son of shri'] + (['and b', 'witness'] if position > 5 else []),
                'weight': 5
            },
            'general': {
                'keywords': ['executed on', 'will on', 'verified at', 'day of'],
                'weight': 3
            }
        }
        
        # Apply context scoring
        if semantic_role in context_keywords:
            keywords = context_keywords[semantic_role]['keywords']
            weight = context_keywords[semantic_role]['weight']
            
            for keyword in keywords:
                if keyword in context:
                    score += weight
                    break  # Don't double-count
        
        # Field type specific scoring
        type_context_matches = {
            'name': ['shri', 'name', 'son of', 'daughter of'],
            'address': ['resident of', 'address', 'plot', 'area'],
            'age': ['aged about', 'aged', 'years'],
            'date': ['on', 'executed', 'day of', 'verified'],
            'location': ['at', 'sub-registrar', 'verified at']
        }
        
        if field_type in type_context_matches:
            for keyword in type_context_matches[field_type]:
                if keyword in context:
                    score += 2
                    break
        
        # Position-based role scoring
        position_expectations = {
            'sub_registrar': (0, 2),  # Should be in first 2 positions
            'testator': (1, 5),  # Should be in positions 1-5
            'father_of_testator': (2, 6),  # Should be after testator
            'witness_a': (4, 10),  # Should be in middle section
            'witness_b': (7, 15),  # Should be after witness A
            'general': (10, 18)  # Can be anywhere, but later is fine
        }
        
        if semantic_role in position_expectations:
            expected_start, expected_end = position_expectations[semantic_role]
            if expected_start <= position <= expected_end:
                score += 5  # Bonus for being in expected position range
            elif position < expected_start:
                score -= abs(position - expected_start)  # Penalty for being too early
            else:
                score -= abs(position - expected_end) * 0.5  # Smaller penalty for being too late
        
        return score

    def _extract_all_text_from_doc(self, doc: Document) -> str:
        """
        Extract all text from a Word document
        """
        all_text = ""
        
        # Extract from paragraphs
        for paragraph in doc.paragraphs:
            all_text += paragraph.text + "\n"
        
        # Extract from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        all_text += paragraph.text + " "
        
        return all_text

    def _find_placeholders_in_text(self, text: str, field_type: str = '') -> List[str]:
        """
        Find potential placeholders in text using pattern matching
        """
        placeholders = []
        
        # Common placeholder patterns
        patterns = [
            r'_{3,}',  # Multiple underscores (3 or more)
            r'\[([^\]]*)\]',  # Text in square brackets
            r'\{([^}]*)\}',  # Text in curly braces
            r'\([^)]*blank[^)]*\)',  # Text with "blank" in parentheses
            r'\([^)]*fill[^)]*\)',  # Text with "fill" in parentheses
            r'<<[^>]*>>',  # Text in double angle brackets
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ''
                
                # Filter out overly long matches (probably not placeholders)
                if len(match) < 100:
                    placeholders.append(match)
        
        return list(set(placeholders))  # Remove duplicates

    async def _create_filled_document(
        self,
        output_path: Path,
        template_analysis: Dict[str, Any],
        filled_fields: Dict[str, Any],
        template_idx: int
    ):
        """
        Create a new filled document when template modification fails
        """
        try:
            # Create a new Word document
            doc = Document()
            
            # Add title
            title = doc.add_heading(f"Filled Document #{template_idx + 1}", 0)
            
            # Add metadata
            metadata_para = doc.add_paragraph()
            metadata_para.add_run("Generated on: ").bold = True
            metadata_para.add_run(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            metadata_para.add_run("\nTemplate: ").bold = True
            metadata_para.add_run(template_analysis['template_info']['filename'])
            metadata_para.add_run(f"\nFields filled: ").bold = True
            metadata_para.add_run(f"{sum(1 for f in filled_fields.values() if f['found'])}/{len(filled_fields)}")
            
            # Add separator
            doc.add_paragraph("_" * 80)
            
            # Generate document content using LLM
            document_content = await self._generate_document_content(
                template_analysis,
                filled_fields,
                template_idx
            )
            
            # Add the generated content
            doc.add_paragraph(document_content)
            
            # Save the document
            doc.save(str(output_path))
            
        except Exception as e:
            logger.error(f"❌ Failed to create filled document: {e}")
            # Ultimate fallback - save as text file
            with open(output_path.with_suffix('.txt'), 'w', encoding='utf-8') as f:
                f.write(f"Error creating document: {e}\n\n")
                f.write(json.dumps(filled_fields, indent=2))

    async def debug_stored_data(self, device_id: str, person_id: str = None) -> Dict[str, Any]:
        """
        Debug method to check what data is stored for a device/person
        """
        try:
            result = {
                'device_data': {},
                'person_data': {},
                'success': True
            }
            
            # Check device storage (original functionality)
            storage_file = Path("local_vector_storage") / f"device_{device_id}_vectors.json"
            if storage_file.exists():
                with open(storage_file, 'r', encoding='utf-8') as f:
                    device_data = json.load(f)
                
                result['device_data'] = {
                    'total_vectors': len(device_data),
                    'first_5_samples': device_data[:5]
                }
                logger.info(f"📊 Found {len(device_data)} device vectors for {device_id}")
            
            # Check person storage (new functionality)
            if person_id:
                person_storage_file = self._get_person_storage_file(person_id)
                if person_storage_file.exists():
                    with open(person_storage_file, 'r', encoding='utf-8') as f:
                        person_data = json.load(f)
                    
                    result['person_data'] = {
                        'person_id': person_id,
                        'total_vectors': len(person_data),
                        'first_5_samples': person_data[:5]
                    }
                    logger.info(f"👤 Found {len(person_data)} person vectors for {person_id}")
                    
                    # Show sample field values
                    for i, vector in enumerate(person_data[:5]):
                        metadata = vector.get('metadata', {})
                        text = vector.get('text', '')[:100]
                        field_value = metadata.get('field_value', 'N/A')
                        logger.info(f"🔍 Person Vector {i+1}: {metadata.get('field_name', 'N/A')} = {field_value}")
                else:
                    result['person_data'] = {
                        'person_id': person_id,
                        'total_vectors': 0,
                        'message': f'No person data found for {person_id}'
                    }
            else:
                # List all available person_ids
                person_files = list(self.person_storage_dir.glob("person_*_data.json"))
                available_persons = [f.stem.replace('person_', '').replace('_data', '') for f in person_files]
                result['person_data'] = {
                    'available_person_ids': available_persons,
                    'total_persons': len(available_persons)
                }
                logger.info(f"👥 Found {len(available_persons)} persons: {available_persons}")
            
            return result
                
        except Exception as e:
            logger.error(f"❌ Failed to debug stored data: {e}")
            return {'success': False, 'error': str(e)}

# Global service instance
interpreted_form_service = InterpretedFormService()
