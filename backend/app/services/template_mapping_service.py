"""
Template Mapping Service - Explicit field mapping for deterministic document filling
Based on the detailed breakdown provided by the AI for solving field confusion issues.
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FieldType(Enum):
    """Supported field types for validation"""
    TEXT = "text"
    INTEGER = "integer" 
    DATE = "date"
    CURRENCY = "currency"
    ADDRESS = "address"
    NAME = "name"

@dataclass
class FieldMapping:
    """Represents a single field mapping in a template"""
    template_location: str  # Description of where field appears in template
    json_key: str          # Key in the input JSON
    field_type: FieldType  # Expected type for validation
    required: bool = True  # Whether field is required
    default_value: str = "" # Default if missing
    format_pattern: Optional[str] = None  # Optional formatting pattern

@dataclass
class TemplateConfig:
    """Configuration for a specific template"""
    template_name: str
    template_description: str
    field_mappings: List[FieldMapping]
    validation_rules: Dict[str, Any]

class TemplateMappingService:
    """
    Service for explicit template field mapping and deterministic document filling.
    Implements the approach from the AI breakdown to solve field confusion issues.
    """
    
    def __init__(self):
        self.template_configs: Dict[str, TemplateConfig] = {}
        self._load_template_configurations()
    
    def _load_template_configurations(self):
        """Load template configurations for supported templates"""
        
        # Sales Tax Affidavit Configuration
        sales_tax_config = TemplateConfig(
            template_name="sales_tax_affidavit",
            template_description="Sales Tax Affidavit Template",
            field_mappings=[
                FieldMapping("BEFORE THE HONBLE MEMBER-TRIBUNAL", "tribunal_member", FieldType.TEXT),
                FieldMapping("Ref: In the case of", "firm_name", FieldType.TEXT),
                FieldMapping("Assessment Year", "assessment_year", FieldType.TEXT),
                FieldMapping("Affidavit of Mr.", "deponent_name", FieldType.NAME),
                FieldMapping("S/o Mr.", "deponent_father_name", FieldType.NAME),
                FieldMapping("aged about ... years", "deponent_age", FieldType.INTEGER),
                FieldMapping("R/o ...", "deponent_address", FieldType.ADDRESS),
                FieldMapping("(a) Admitted turn over Rs.", "admitted_turnover", FieldType.CURRENCY),
                FieldMapping("(b) Assessed turn over Rs.", "assessed_turnover", FieldType.CURRENCY),
                FieldMapping("(c) Disputed turn over Rs.", "disputed_turnover", FieldType.CURRENCY),
                FieldMapping("(d) Disputed tax Rs.", "disputed_tax", FieldType.CURRENCY),
                FieldMapping("Prayer/Appeal request", "appeal_request", FieldType.TEXT, required=False)
            ],
            validation_rules={
                "deponent_age": {"min": 18, "max": 120},
                "tribunal_member": {"allowed_values": ["Panchkula", "Delhi", "Mumbai", "Kolkata"]}
            }
        )
        
        # Bond and Bail Bond Configuration  
        bond_bail_config = TemplateConfig(
            template_name="bond_and_bail",
            template_description="Bond and Bail Bond Under Criminal Procedure Code",
            field_mappings=[
                FieldMapping("I (name)", "accused_name", FieldType.NAME),
                FieldMapping("of (address)", "accused_address", FieldType.ADDRESS),
                FieldMapping("District Magistrate of", "magistrate_name", FieldType.TEXT),
                FieldMapping("to answer to the charge of", "charge_details", FieldType.TEXT),
                FieldMapping("Court name", "court_name", FieldType.TEXT),
                FieldMapping("Appearance day", "appearance_day", FieldType.INTEGER),
                FieldMapping("Appearance month", "appearance_month", FieldType.TEXT),
                FieldMapping("Appearance year", "appearance_year", FieldType.INTEGER),
                FieldMapping("Forfeiture amount", "forfeiture_amount", FieldType.CURRENCY),
                FieldMapping("Surety name", "surety_name", FieldType.NAME, required=False),
                FieldMapping("Surety address", "surety_address", FieldType.ADDRESS, required=False),
                FieldMapping("Surety court", "surety_court", FieldType.TEXT, required=False),
                FieldMapping("Surety appearance day", "surety_day", FieldType.INTEGER, required=False),
                FieldMapping("Surety appearance month", "surety_month", FieldType.TEXT, required=False),
                FieldMapping("Surety appearance year", "surety_year", FieldType.INTEGER, required=False),
                FieldMapping("Surety forfeiture amount", "surety_forfeiture_amount", FieldType.CURRENCY, required=False)
            ],
            validation_rules={
                "appearance_day": {"min": 1, "max": 31},
                "appearance_year": {"min": 2020, "max": 2030},
                "forfeiture_amount": {"min": 1000}
            }
        )
        
        # Income Tax Return Extension Affidavit Configuration
        income_tax_config = TemplateConfig(
            template_name="income_tax_extension", 
            template_description="Affidavit for Extending Time to File IT Return",
            field_mappings=[
                FieldMapping("BEFORE THE INCOME TAX OFFICER", "income_tax_officer", FieldType.TEXT),
                FieldMapping("In the matter of", "company_name", FieldType.TEXT),
                FieldMapping("Deponent name", "deponent_name", FieldType.NAME),
                FieldMapping("Deponent father name", "deponent_father_name", FieldType.NAME),
                FieldMapping("Deponent age", "deponent_age", FieldType.INTEGER),
                FieldMapping("Deponent address", "deponent_address", FieldType.ADDRESS),
                FieldMapping("Original due date", "due_date_original", FieldType.DATE),
                FieldMapping("Notice date", "notice_date", FieldType.DATE),
                FieldMapping("Notice section", "notice_section", FieldType.TEXT),
                FieldMapping("Accounts closed date", "accounts_closed_date", FieldType.DATE),
                FieldMapping("Extension applied till", "extension_applied_till", FieldType.DATE),
                FieldMapping("Form number", "form_no", FieldType.TEXT),
                FieldMapping("Form filed date", "form_filed_date", FieldType.DATE),
                FieldMapping("Receipt number", "receipt_no", FieldType.TEXT),
                FieldMapping("Return filed date", "return_filed_date", FieldType.DATE),
                FieldMapping("Officer verbal order date", "officer_verbal_order_date", FieldType.DATE)
            ],
            validation_rules={
                "deponent_age": {"min": 18, "max": 120},
                "form_no": {"pattern": r"^[A-Z0-9\-]+$"}
            }
        )
        
        # Store configurations
        self.template_configs = {
            "sales_tax_affidavit": sales_tax_config,
            "bond_and_bail": bond_bail_config, 
            "income_tax_extension": income_tax_config
        }
        
        logger.info(f"Loaded {len(self.template_configs)} template configurations")
    
    def get_template_config(self, template_name: str) -> Optional[TemplateConfig]:
        """Get configuration for a specific template"""
        return self.template_configs.get(template_name)
    
    def detect_template_type(self, template_content: str) -> Optional[str]:
        """
        Detect template type based on content analysis
        Returns the template name if detected, None otherwise
        """
        content_lower = template_content.lower()
        
        # Detection patterns for each template type
        detection_patterns = {
            "sales_tax_affidavit": [
                "sales tax", "assessment year", "admitted turn over", "disputed tax"
            ],
            "bond_and_bail": [
                "bond and bail", "criminal procedure code", "magistrate", "forfeiture"
            ],
            "income_tax_extension": [
                "income tax officer", "extending time", "return", "due date"
            ]
        }
        
        # Score each template type
        scores = {}
        for template_type, patterns in detection_patterns.items():
            score = sum(1 for pattern in patterns if pattern in content_lower)
            scores[template_type] = score
        
        # Return template with highest score (minimum 2 matches required)
        best_match = max(scores.items(), key=lambda x: x[1])
        if best_match[1] >= 2:
            return best_match[0]
        
        return None
    
    def validate_field_value(self, field_mapping: FieldMapping, value: Any, 
                           validation_rules: Dict[str, Any]) -> Tuple[bool, str, Any]:
        """
        Validate a field value against its expected type and rules
        Returns (is_valid, error_message, formatted_value)
        """
        try:
            # Handle None/empty values
            if value is None or value == "":
                if field_mapping.required:
                    return False, f"Required field '{field_mapping.json_key}' is missing", None
                return True, "", field_mapping.default_value
            
            # Type-specific validation
            if field_mapping.field_type == FieldType.INTEGER:
                if isinstance(value, str):
                    value = int(value)
                elif not isinstance(value, int):
                    return False, f"Field '{field_mapping.json_key}' must be an integer", None
                
                # Check range if specified
                rules = validation_rules.get(field_mapping.json_key, {})
                if "min" in rules and value < rules["min"]:
                    return False, f"Field '{field_mapping.json_key}' must be >= {rules['min']}", None
                if "max" in rules and value > rules["max"]:
                    return False, f"Field '{field_mapping.json_key}' must be <= {rules['max']}", None
                    
            elif field_mapping.field_type == FieldType.TEXT:
                value = str(value)
                
                # Check allowed values if specified
                rules = validation_rules.get(field_mapping.json_key, {})
                if "allowed_values" in rules and value not in rules["allowed_values"]:
                    return False, f"Field '{field_mapping.json_key}' must be one of {rules['allowed_values']}", None
                
                # Check pattern if specified
                if "pattern" in rules:
                    if not re.match(rules["pattern"], value):
                        return False, f"Field '{field_mapping.json_key}' does not match required pattern", None
                        
            elif field_mapping.field_type in [FieldType.NAME, FieldType.ADDRESS]:
                value = str(value).strip()
                if not value:
                    return False, f"Field '{field_mapping.json_key}' cannot be empty", None
                    
            elif field_mapping.field_type == FieldType.CURRENCY:
                # Ensure currency is properly formatted
                value = str(value)
                if not re.match(r'^[\d,]+$', value.replace(' ', '')):
                    return False, f"Field '{field_mapping.json_key}' must be a valid currency amount", None
                    
            elif field_mapping.field_type == FieldType.DATE:
                # Accept various date formats
                value = str(value)
                if not value:
                    return False, f"Field '{field_mapping.json_key}' requires a date", None
            
            return True, "", value
            
        except (ValueError, TypeError) as e:
            return False, f"Validation error for '{field_mapping.json_key}': {str(e)}", None
    
    def validate_input_data(self, template_name: str, input_data: Dict[str, Any]) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Validate input data against template configuration
        Returns (is_valid, error_messages, validated_data)
        """
        config = self.get_template_config(template_name)
        if not config:
            return False, [f"Unknown template: {template_name}"], {}
        
        errors = []
        validated_data = {}
        
        for field_mapping in config.field_mappings:
            value = input_data.get(field_mapping.json_key)
            is_valid, error_msg, formatted_value = self.validate_field_value(
                field_mapping, value, config.validation_rules
            )
            
            if not is_valid:
                errors.append(error_msg)
            else:
                validated_data[field_mapping.json_key] = formatted_value
        
        return len(errors) == 0, errors, validated_data
    
    def create_replacement_mapping(self, template_name: str, validated_data: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        Create replacement mapping for document filling
        Returns list of (template_location, json_key, formatted_value) tuples
        """
        config = self.get_template_config(template_name)
        if not config:
            return []
        
        replacements = []
        for field_mapping in config.field_mappings:
            value = validated_data.get(field_mapping.json_key, field_mapping.default_value)
            if value:
                replacements.append((
                    field_mapping.template_location,
                    field_mapping.json_key, 
                    str(value)
                ))
        
        return replacements
    
    def get_available_templates(self) -> List[Dict[str, str]]:
        """Get list of available template configurations"""
        return [
            {
                "name": config.template_name,
                "description": config.template_description,
                "field_count": len(config.field_mappings)
            }
            for config in self.template_configs.values()
        ]
    
    def export_template_config(self, template_name: str) -> Optional[Dict[str, Any]]:
        """Export template configuration as JSON for external use"""
        config = self.get_template_config(template_name)
        if not config:
            return None
        
        return {
            "template_name": config.template_name,
            "template_description": config.template_description,
            "field_mappings": [
                {
                    "template_location": fm.template_location,
                    "json_key": fm.json_key,
                    "field_type": fm.field_type.value,
                    "required": fm.required,
                    "default_value": fm.default_value
                }
                for fm in config.field_mappings
            ],
            "validation_rules": config.validation_rules
        }
