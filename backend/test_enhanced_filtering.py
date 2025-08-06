"""
Enhanced test script to verify content filtering with your specific TOC format.
This tests the exact table of contents structure you showed in the image.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gemini_service import GeminiService

def test_your_toc_format():
    """Test filtering with your exact TOC format"""
    
    # Sample template matching your TOC image format
    sample_template = """
ABC Medical Device Company
Device Master File
Document Control No: DMF-2024-001

Table of Contents

S. No.    Contents                                           Page No.
1         Executive Summary                                      
1.1       Introduction & Description of medical device          
1.2       Sterilization of device                              
1.3       Risk Management plan, Risk Analysis, Evaluation and control documents
1.4       Clinical Evidence and evaluation                      
1.5       Regulatory status of the similar device in India     
1.6       Design examination certificate, Declaration of conformity, Mark of conformity certificate, Design certificate (If Applicable)
2         Device Description and product specification          
2.1       Device Description & Information of device           
2.2       Product Specification                                
2.3       Reference to the predicate or previous generations of device
3         Labelling                                            
4         Design and Manufacturing information                  
4.1       Device Design                                        
5         Essential Principles Checklist                       
6         Risk analysis and control summary                    
7         Verification and validation of the medical device    
7.1       General                                              
7.2       Biocompatibility                                     
7.3       Medicinal Substances                                 
7.4       Biological Safety                                    
7.5       Sterilization                                        
7.6       Software verification and validation                 
7.7       Annual Studies                                       

Header: Device Master File - Confidential
Page 1 of 25

SECTION 1: EXECUTIVE SUMMARY

1.1 Introduction & Description of medical device

Generic name: [To be filled]

Common name: _______________

Manufacturer: [MISSING]

Address: 
_________________________
_________________________

Model No.: ____________

Serial Number: {serial_number}

Document No.: ___________

Date: __/__/____

1.2 Device Classification

Class: [Enter class]

Rule Applied: ___________

Risk Category: [HIGH/MEDIUM/LOW]

1.3 Intended Use

Intended use: [To be filled with detailed description]

Indications for use: 
[MISSING - Please provide]

Target patient population: _______________

SECTION 2: DEVICE SPECIFICATION

2.1 Technical Specifications

Operating voltage: _______ V

Operating frequency: _____ Hz

Power consumption: ______ W

Dimensions: L: ____ x W: ____ x H: ____ mm

Weight: _______ kg

Materials used: [List all materials]

2.2 Performance Specifications

Accuracy: ±_____ %

Measurement range: _____ to _____

Response time: _____ seconds

SECTION 3: REGULATORY INFORMATION

3.1 Regulatory Status

FDA Status: [APPROVED/PENDING/NOT APPLICABLE]

CE Mark: [YES/NO]

ISO Standards: [List applicable standards]

FOOTER: Confidential Document - Company Proprietary
"""

    print("🔍 TESTING YOUR SPECIFIC TOC FORMAT")
    print("=" * 60)
    
    # Initialize the service
    gemini_service = GeminiService()
    
    # Test the filtering
    filtered_content = gemini_service._filter_template_content(sample_template)
    
    print("📄 ORIGINAL CONTENT (first 20 lines):")
    print("-" * 40)
    original_lines = sample_template.split('\n')
    for i, line in enumerate(original_lines[:20]):
        print(f"{i+1:2}: {line}")
    print("... (truncated)")
    print()
    
    print("✅ FILTERED CONTENT:")
    print("-" * 40)
    filtered_lines = filtered_content.split('\n')
    for i, line in enumerate(filtered_lines):
        if line.strip():  # Only show non-empty lines
            print(f"{i+1:2}: {line}")
    print()
    
    # Analyze what was filtered out
    print("🧹 FILTERING ANALYSIS:")
    print("-" * 40)
    
    removed_content = []
    for line in original_lines:
        if line.strip() and line.strip() not in [l.strip() for l in filtered_lines]:
            removed_content.append(line.strip())
    
    print("🚫 REMOVED (should be ignored):")
    for line in removed_content[:15]:  # Show first 15 removed lines
        print(f"   ✓ {line}")
    if len(removed_content) > 15:
        print(f"   ... and {len(removed_content) - 15} more lines")
    print()
    
    # Find fillable fields in filtered content
    print("🎯 FILLABLE FIELDS FOUND:")
    print("-" * 40)
    
    fillable_patterns = [
        r'.*:\s*\[.*\]',  # "Field: [To be filled]"
        r'.*:\s*\[MISSING.*\]',  # "Field: [MISSING]"
        r'.*:\s*_+',  # "Field: ______"
        r'.*:\s*\{.*\}',  # "Field: {placeholder}"
        r'.*:\s*__/__/____',  # Date fields
        r'.*:\s*\[.*/.*/.*\]',  # Choice fields [YES/NO]
    ]
    
    found_fields = []
    for line in filtered_lines:
        line_stripped = line.strip()
        field_found = False
        for pattern in fillable_patterns:
            if re.search(pattern, line_stripped):
                found_fields.append(line_stripped)
                field_found = True
                break
        # Also check for simple colon fields
        if not field_found and ':' in line_stripped and any(marker in line_stripped.lower() for marker in ['[', '_', '{', 'missing', 'to be filled']):
            found_fields.append(line_stripped)
    
    # Remove duplicates
    found_fields = list(set(found_fields))
    
    for field in found_fields:
        print(f"   ✅ {field}")
    
    print()
    print("📊 STATISTICS:")
    print(f"   Original lines: {len(original_lines)}")
    print(f"   Filtered lines: {len(filtered_lines)}")
    print(f"   Removed lines: {len(original_lines) - len(filtered_lines)}")
    print(f"   Fillable fields found: {len(found_fields)}")
    print()
    
    # Test specific TOC entries that should be removed
    print("🔍 SPECIFIC TOC TESTS:")
    print("-" * 40)
    
    toc_entries_to_check = [
        "Table of Contents",
        "S. No.    Contents                                           Page No.",
        "1         Executive Summary",
        "1.1       Introduction & Description of medical device",
        "7.7       Annual Studies",
        "FOOTER: Confidential Document",
        "Header: Device Master File",
        "Page 1 of 25"
    ]
    
    for entry in toc_entries_to_check:
        if any(entry.strip() in line for line in filtered_lines):
            print(f"   ❌ FAILED: '{entry}' should be removed but is present")
        else:
            print(f"   ✅ PASSED: '{entry}' correctly removed")
    
    print()
    
    # Test that important content is preserved
    important_content = [
        "Generic name: [To be filled]",
        "Manufacturer: [MISSING]",
        "Model No.: ____________",
        "Operating voltage: _______ V",
        "FDA Status: [APPROVED/PENDING/NOT APPLICABLE]"
    ]
    
    print("🎯 IMPORTANT CONTENT PRESERVATION:")
    print("-" * 40)
    
    for content in important_content:
        if any(content in line for line in filtered_lines):
            print(f"   ✅ PRESERVED: '{content}'")
        else:
            print(f"   ❌ MISSING: '{content}' should be preserved")

if __name__ == "__main__":
    import re
    test_your_toc_format()
