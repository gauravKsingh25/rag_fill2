"""
Test script to demonstrate enhanced content filtering for template processing.
This shows how the system now ignores TOC, headers, footers and focuses on main content.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gemini_service import GeminiService

def test_content_filtering():
    """Test the enhanced content filtering functionality"""
    
    # Sample template content with TOC, headers, footers, and main content
    sample_template = """
CONFIDENTIAL

ABC Medical Devices Inc.
Device Master File Template
Page 1 of 10

Table of Contents

1. Introduction ........................ 3
2. Device Information .................. 4
   2.1 Generic Name .................... 4
   2.2 Model Number .................... 5
   2.3 Manufacturer .................... 5
3. Technical Specifications ............ 6
4. Documentation ...................... 7
   4.1 Document Number ................. 7
   4.2 Date ........................... 7
5. Approval ........................... 8
   5.1 Signature ...................... 8

Page 2
Header: Device Master File
Footer: Confidential - Draft v1.2

Section 1: Introduction
This document contains the device master file information.

Section 2: Device Information

Generic name: [To be filled]

Manufacturer: [MISSING]

Model No.: _____________

Document No.: 

Serial Number: {serial_number}

Date: __/__/____

Technical Specifications:
- Type: <device_type>
- Version: [Enter version]

Approval Section:

Signature: ________________

By: [Authorized Person]

Date: __/__/____

Footer: Page 3 - Confidential
Copyright © 2024 ABC Medical Devices Inc.
"""

    # Initialize the service
    gemini_service = GeminiService()
    
    print("🔍 TESTING CONTENT FILTERING")
    print("=" * 50)
    
    # Test the filtering
    filtered_content = gemini_service._filter_template_content(sample_template)
    
    print("📄 ORIGINAL CONTENT:")
    print("-" * 30)
    print(sample_template)
    print()
    
    print("✅ FILTERED CONTENT (TOC, headers, footers removed):")
    print("-" * 30)
    print(filtered_content)
    print()
    
    # Count what was filtered out
    original_lines = sample_template.split('\n')
    filtered_lines = filtered_content.split('\n')
    
    print("📊 FILTERING STATISTICS:")
    print(f"Original lines: {len(original_lines)}")
    print(f"Filtered lines: {len(filtered_lines)}")
    print(f"Removed lines: {len(original_lines) - len(filtered_lines)}")
    print()
    
    # Test field extraction on filtered content
    print("🎯 FIELD EXTRACTION TEST:")
    print("-" * 30)
    
    # Manually extract colon fields from filtered content for testing
    lines = filtered_content.split('\n')
    found_fields = []
    
    for line_num, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped.endswith(':') and len(line_stripped) > 3:
            # Simple field extraction for demo
            field_name = line_stripped[:-1].strip()
            if len(field_name) > 2:
                found_fields.append(field_name)
    
    print("Fields found after filtering:")
    for field in found_fields:
        print(f"  ✅ {field}")
    
    print()
    print("🚫 CONTENT THAT SHOULD BE IGNORED:")
    print("- Table of Contents entries")
    print("- Page headers/footers")
    print("- Copyright notices")
    print("- Page numbers")
    print("- Company headers")
    print()
    
    print("✅ CONTENT THAT SHOULD BE PROCESSED:")
    print("- Generic name:")
    print("- Manufacturer:")
    print("- Model No.:")
    print("- Document No.:")
    print("- Date:")
    print("- Signature:")
    print("- [MISSING] markers")
    print("- Underline fields")
    print("- Placeholder brackets")

if __name__ == "__main__":
    test_content_filtering()
