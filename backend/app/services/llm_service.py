import asyncio
from typing import Dict, List, Any
import google.generativeai as genai
import os
from pathlib import Path
import json
import tempfile

class DocumentProcessor:
    """Basic document processor for text extraction"""
    
    def extract_text(self, file_path: str) -> str:
        """Extract text from various file formats"""
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif file_ext == '.pdf':
                # Basic PDF text extraction
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = []
                        for page in reader.pages:
                            text.append(page.extract_text())
                        return '\n'.join(text)
                except Exception as e:
                    print(f"PDF extraction failed: {e}")
                    return ""
            
            elif file_ext == '.docx':
                try:
                    from docx import Document
                    doc = Document(file_path)
                    text = []
                    for paragraph in doc.paragraphs:
                        text.append(paragraph.text)
                    return '\n'.join(text)
                except Exception as e:
                    print(f"DOCX extraction failed: {e}")
                    return ""
            
            else:
                return ""
                
        except Exception as e:
            print(f"Text extraction failed: {e}")
            return ""

class LLMService:
    def __init__(self):
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            self.model = None
            print("Warning: GEMINI_API_KEY not found. Using mock responses.")

    async def interpret_form_content(self, content: str, form_type: str, template_fields: List[Dict]) -> Dict[str, str]:
        """
        Use LLM to interpret content and extract field values for a specific form type
        """
        if not self.model:
            return self._get_mock_interpretation(form_type)

        # Create field descriptions for the prompt
        field_descriptions = []
        for field in template_fields:
            field_descriptions.append(f"- {field['name']}: {field.get('description', 'No description')}")

        prompt = f"""
You are an expert legal document analyzer. Analyze the following content and extract information for a {form_type} form.

Content to analyze:
{content}

Extract values for these fields:
{chr(10).join(field_descriptions)}

Instructions:
1. Extract exact information from the content where available
2. If information is not explicitly stated, leave the field empty
3. For dates, use YYYY-MM-DD format
4. For addresses, include full address details
5. Be precise and accurate

Return the extracted information as a JSON object with field names as keys and extracted values as values.
Only return the JSON object, no additional text.

Example format:
{{
    "field_name_1": "extracted_value_1",
    "field_name_2": "extracted_value_2",
    "field_name_3": ""
}}
"""

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            
            # Parse the JSON response
            response_text = response.text.strip()
            
            # Clean up the response to extract JSON
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                extracted_fields = json.loads(response_text)
                return extracted_fields
            except json.JSONDecodeError:
                print(f"Failed to parse LLM response as JSON: {response_text}")
                return self._get_mock_interpretation(form_type)
                
        except Exception as e:
            print(f"Error calling LLM service: {e}")
            return self._get_mock_interpretation(form_type)

    def _get_mock_interpretation(self, form_type: str) -> Dict[str, str]:
        """
        Provide mock interpretations for development/testing
        """
        mock_data = {
            "affidavit": {
                "affiant_name": "John Doe",
                "affiant_address": "123 Main Street, Anytown, ST 12345",
                "statement": "I hereby affirm that the information provided is true and accurate to the best of my knowledge.",
                "date": "2024-08-28",
                "state": "California",
                "county": "Los Angeles"
            },
            "will": {
                "testator_name": "Jane Smith",
                "testator_address": "456 Oak Avenue, Somewhere, ST 67890",
                "executor_name": "Robert Smith",
                "executor_address": "789 Pine Street, Elsewhere, ST 11111",
                "beneficiaries": "My spouse John Smith (50%), My children Mary Smith and James Smith (25% each)",
                "assets_distribution": "All real estate to spouse, personal property divided equally among children",
                "date": "2024-08-28",
                "witness1_name": "Alice Johnson",
                "witness2_name": "Bob Wilson"
            },
            "power_of_attorney": {
                "principal_name": "Mary Johnson",
                "principal_address": "321 Elm Street, Hometown, ST 22222",
                "agent_name": "David Johnson",
                "agent_address": "654 Maple Drive, Newtown, ST 33333",
                "powers_granted": "Full authority to manage financial affairs, make healthcare decisions, and handle legal matters",
                "effective_date": "2024-08-28",
                "durability_clause": "This power of attorney shall remain effective even if I become incapacitated"
            },
            "contract": {
                "party1_name": "ABC Corporation",
                "party1_address": "100 Business Blvd, Corporate City, ST 44444",
                "party2_name": "XYZ Services LLC",
                "party2_address": "200 Service Street, Service Town, ST 55555",
                "contract_subject": "Provision of consulting services for software development project",
                "terms_conditions": "Monthly deliverables, 30-day payment terms, confidentiality requirements",
                "consideration": "$50,000 total contract value",
                "effective_date": "2024-09-01",
                "termination_date": "2024-12-31"
            },
            "general": {
                "full_name": "Sample Person",
                "date_of_birth": "1990-01-01",
                "address": "123 Sample Street, Sample City, ST 12345",
                "phone_number": "(555) 123-4567",
                "email": "sample@example.com",
                "description": "General purpose form for sample documentation"
            }
        }
        
        return mock_data.get(form_type, {})

    async def enhance_document_content(self, form_type: str, fields: Dict[str, str]) -> str:
        """
        Use LLM to enhance and format the document content
        """
        if not self.model:
            return f"Enhanced {form_type} document with provided fields (mock mode)"

        prompt = f"""
You are a legal document expert. Create a professional, legally formatted {form_type} document using the provided field values.

Field values:
{json.dumps(fields, indent=2)}

Requirements:
1. Use proper legal formatting and language
2. Include all necessary clauses and provisions
3. Ensure the document is complete and professional
4. Use standard legal terminology
5. Include proper signature blocks and witness lines where appropriate

Generate a complete, professional {form_type} document.
"""

        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
        except Exception as e:
            print(f"Error enhancing document: {e}")
            return f"Enhanced {form_type} document with provided fields (error in LLM service)"

    async def validate_form_completeness(self, form_type: str, fields: List[Dict]) -> Dict[str, Any]:
        """
        Validate if all required fields are properly filled
        """
        missing_required = []
        validation_issues = []
        
        for field in fields:
            if field.get('required', False) and not field.get('value', '').strip():
                missing_required.append(field['name'])
            
            # Basic validation based on field type
            field_value = field.get('value', '').strip()
            if field_value:
                if field.get('type') == 'date':
                    # Basic date format validation
                    try:
                        from datetime import datetime
                        datetime.strptime(field_value, '%Y-%m-%d')
                    except ValueError:
                        validation_issues.append(f"{field['name']}: Invalid date format, use YYYY-MM-DD")
                
                elif field.get('type') == 'email' and '@' not in field_value:
                    validation_issues.append(f"{field['name']}: Invalid email format")

        return {
            "is_valid": len(missing_required) == 0 and len(validation_issues) == 0,
            "missing_required_fields": missing_required,
            "validation_issues": validation_issues
        }
