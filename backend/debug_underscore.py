"""
Debug version to trace exactly what happens to underscore fields
"""

import sys
import os
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gemini_service import GeminiService

def debug_underscore_fields():
    """Debug what happens to underscore fields specifically"""
    
    # Simple test with just the underscore fields
    simple_template = """
Device Master File

Generic name: [To be filled]

Model No.: ____________

Operating voltage: _______ V

Manufacturer: [MISSING]

Date: __/__/____

Address: 
_________________________
_________________________
"""

    print("🔍 DEBUGGING UNDERSCORE FIELDS")
    print("=" * 50)
    
    gemini_service = GeminiService()
    
    # Test line by line what gets filtered
    lines = simple_template.split('\n')
    print("📄 LINE BY LINE ANALYSIS:")
    print("-" * 30)
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if line_stripped:
            # Check if it has underscore pattern
            has_underscore = '____' in line_stripped
            has_colon = ':' in line_stripped
            
            print(f"Line {i+1:2}: '{line_stripped}'")
            print(f"         Has underscore: {has_underscore}")
            print(f"         Has colon: {has_colon}")
            
            # Test pattern matching
            underscore_pattern = r'.*:\s*_+'
            matches_pattern = re.search(underscore_pattern, line_stripped)
            print(f"         Matches underscore pattern: {matches_pattern is not None}")
            print()
    
    # Now test the full filtering
    filtered_content = gemini_service._filter_template_content(simple_template)
    
    print("✅ FILTERED RESULT:")
    print("-" * 30)
    filtered_lines = filtered_content.split('\n')
    for line in filtered_lines:
        if line.strip():
            print(f"   {line}")
    
    print()
    print("🎯 MISSING FIELDS CHECK:")
    print("-" * 30)
    
    target_fields = [
        "Model No.: ____________",
        "Operating voltage: _______ V"
    ]
    
    for field in target_fields:
        found = any(field in line for line in filtered_lines)
        print(f"   {'✅' if found else '❌'} {field}")

if __name__ == "__main__":
    debug_underscore_fields()
