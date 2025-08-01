#!/usr/bin/env python3
"""
Focused test to analyze and fix the quote escaping issue in paragraph data.

The main issue is that the string contains an apostrophe in "First Republic Bank's"
which breaks the Python literal parsing because it's not properly escaped.
"""

import ast
import re
from typing import Any

def analyze_quote_issue():
    """Analyze the specific quote issue and demonstrate solutions."""
    
    # The problematic string from the logs
    problematic_string = """[{'text': 'JPMorgan Chase did not assume First Republic Bank's deposits or any other liabilities of First Republic Bank.', 'bullet_style': 'bullet', 'indent_level': 0}]"""
    
    print("🔍 ANALYZING QUOTE ISSUE")
    print("=" * 50)
    print(f"Problematic string: {repr(problematic_string)}")
    print()
    
    # Count quotes
    single_quotes = problematic_string.count("'")
    double_quotes = problematic_string.count('"')
    print(f"Single quotes count: {single_quotes}")
    print(f"Double quotes count: {double_quotes}")
    print(f"Single quotes should be even for valid Python literal: {'✅' if single_quotes % 2 == 0 else '❌'}")
    print()
    
    # Show the specific problem
    print("🔎 PROBLEM ANALYSIS:")
    print("The issue is in: \"First Republic Bank's deposits\"")
    print("The apostrophe in \"Bank's\" is not escaped, breaking the string literal")
    print()
    
    # Test the original string
    print("🧪 TESTING ORIGINAL STRING:")
    try:
        result = ast.literal_eval(problematic_string)
        print("✅ Original string parsed successfully")
    except Exception as e:
        print(f"❌ Original string failed: {e}")
    print()
    
    # Solution 1: Escape the apostrophe
    print("🔧 SOLUTION 1: Escape the apostrophe")
    fixed_string_1 = problematic_string.replace("Bank's", "Bank\\'s")
    print(f"Fixed string: {repr(fixed_string_1)}")
    try:
        result1 = ast.literal_eval(fixed_string_1)
        print("✅ Solution 1 works!")
        print(f"Result: {result1}")
    except Exception as e:
        print(f"❌ Solution 1 failed: {e}")
    print()
    
    # Solution 2: Use double quotes for the text content
    print("🔧 SOLUTION 2: Use double quotes for text content")
    fixed_string_2 = """[{"text": "JPMorgan Chase did not assume First Republic Bank's deposits or any other liabilities of First Republic Bank.", "bullet_style": "bullet", "indent_level": 0}]"""
    print(f"Fixed string: {repr(fixed_string_2)}")
    try:
        result2 = ast.literal_eval(fixed_string_2)
        print("✅ Solution 2 works!")
        print(f"Result: {result2}")
    except Exception as e:
        print(f"❌ Solution 2 failed: {e}")
    print()
    
    # Solution 3: Automatic quote escaping function
    print("🔧 SOLUTION 3: Automatic quote escaping")
    def fix_quotes_in_string(text: str) -> str:
        """Fix unescaped quotes in a Python literal string."""
        # Strategy: Find text values and escape apostrophes within them
        # This is a simple regex-based approach
        
        def escape_apostrophes_in_match(match):
            content = match.group(1)
            # Escape apostrophes that aren't already escaped
            content = re.sub(r"(?<!\\)'", "\\'", content)
            return f"'{content}'"
        
        # Find 'text': '...' patterns and fix apostrophes in the value
        fixed = re.sub(r"'text':\s*'([^']*(?:\\'[^']*)*)'", escape_apostrophes_in_match, text)
        return fixed
    
    fixed_string_3 = fix_quotes_in_string(problematic_string)
    print(f"Fixed string: {repr(fixed_string_3)}")
    try:
        result3 = ast.literal_eval(fixed_string_3)
        print("✅ Solution 3 works!")
        print(f"Result: {result3}")
    except Exception as e:
        print(f"❌ Solution 3 failed: {e}")
    print()
    
    # More robust solution
    print("🔧 SOLUTION 4: Robust quote fixing")
    def robust_fix_quotes(text: str) -> str:
        """More robust quote fixing that handles various cases."""
        # Replace pattern: 'value with apostrophe's' with 'value with apostrophe\'s'
        # But be careful not to affect already properly escaped quotes
        
        # Find all single-quoted strings and fix apostrophes within them
        def fix_single_quoted_string(match):
            quote_start = match.start()
            quote_content = match.group(1)
            
            # If this looks like a text value (has actual content), escape internal apostrophes
            if len(quote_content) > 10:  # Likely text content, not a short key/value
                # Escape apostrophes that aren't already escaped
                fixed_content = quote_content.replace("\\'", "___TEMP_ESCAPE___")  # Temporarily protect existing escapes
                fixed_content = fixed_content.replace("'", "\\'")  # Escape unescaped apostrophes
                fixed_content = fixed_content.replace("___TEMP_ESCAPE___", "\\'")  # Restore protected escapes
                return f"'{fixed_content}'"
            else:
                return match.group(0)  # Return unchanged for short strings (likely keys)
        
        # Match single-quoted strings: 'content'
        fixed = re.sub(r"'([^']*(?:\\'[^']*)*)'", fix_single_quoted_string, text)
        return fixed
    
    fixed_string_4 = robust_fix_quotes(problematic_string)
    print(f"Fixed string: {repr(fixed_string_4)}")
    try:
        result4 = ast.literal_eval(fixed_string_4)
        print("✅ Solution 4 works!")
        print(f"Result: {result4}")
    except Exception as e:
        print(f"❌ Solution 4 failed: {e}")
    print()

def test_with_various_cases():
    """Test the solution with various problematic cases."""
    print("🧪 TESTING WITH VARIOUS CASES")
    print("=" * 50)
    
    test_cases = [
        # Case 1: Original issue
        """[{'text': 'JPMorgan Chase did not assume First Republic Bank's deposits.', 'bullet_style': 'bullet'}]""",
        
        # Case 2: Multiple apostrophes
        """[{'text': 'It's a company's responsibility to ensure customers' satisfaction.', 'bullet_style': 'bullet'}]""",
        
        # Case 3: Already escaped (should remain unchanged)
        """[{'text': 'JPMorgan Chase did not assume First Republic Bank\\'s deposits.', 'bullet_style': 'bullet'}]""",
        
        # Case 4: Mixed quotes
        """[{'text': 'The "quoted" text with Bank's apostrophe.', 'bullet_style': 'bullet'}]""",
    ]
    
    def smart_quote_fix(text: str) -> str:
        """Smart quote fixing that preserves already-escaped quotes."""
        # More sophisticated approach using tokenization-like logic
        result = []
        i = 0
        while i < len(text):
            if text[i] == "'" and i > 0:
                # Check if this apostrophe is within a text value
                # Look backwards to see if we're in a 'text': '...' context
                preceding = text[:i]
                
                # Check if we're inside a single-quoted string that started after 'text':
                text_match = re.search(r"'text':\s*'[^']*$", preceding)
                if text_match:
                    # We're inside a text value, escape this apostrophe if not already escaped
                    if i > 0 and text[i-1] != '\\':
                        result.append("\\'")  # Escape the apostrophe
                    else:
                        result.append("'")  # Keep already escaped
                else:
                    result.append("'")  # Not in text content, keep as-is
            else:
                result.append(text[i])
            i += 1
        
        return ''.join(result)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i} ---")
        print(f"Original: {repr(test_case)}")
        
        # Try the smart fix
        fixed = smart_quote_fix(test_case)
        print(f"Fixed:    {repr(fixed)}")
        
        try:
            result = ast.literal_eval(fixed)
            print(f"✅ Success: {result}")
        except Exception as e:
            print(f"❌ Failed: {e}")

if __name__ == "__main__":
    analyze_quote_issue()
    test_with_various_cases()
