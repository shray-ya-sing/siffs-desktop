#!/usr/bin/env python3
"""
Debug script to test AST parsing of paragraph data
"""

import ast

# The exact string from the logs
paragraph_data_str = """[{'text': 'JPMorgan Chase acquired substantial majority of assets and assumed certain liabilities of First Republic Bank from the FDIC', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet'}, {'text': '$173B of loans and $30B of securities', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet'}, {'text': 'Approximately $92B of deposits and $28B of FHLB advances', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet'}, {'text': 'JPMorgan Chase did not assume First Republic Bank\\'s corporate debt or preferred stock', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet'}, {'text': 'JPMorgan Chase will make a payment of $10.6B to the FDIC', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet'}, {'text': 'FDIC will provide loss share agreements with respect to most acquired loans', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet'}, {'text': 'Single family residential mortgages: 80% loss coverage for seven years', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet', 'indent_level': 1}, {'text': 'Commercial loans, including CRE: 80% loss coverage for five years', 'font_name': 'Arial', 'font_size': 9, 'font_color': '#000000', 'bullet_style': 'bullet', 'indent_level': 1}]"""

print("Testing AST parsing of paragraph data...")
print("String length:", len(paragraph_data_str))
print("First 200 characters:", repr(paragraph_data_str[:200]))
print("\nLooking for problematic characters...")

# Find the problematic part
problematic_part = "JPMorgan Chase did not assume First Republic Bank\\'s corporate debt"
print("Problematic part:", repr(problematic_part))

# Test parsing
try:
    result = ast.literal_eval(paragraph_data_str)
    print("✅ AST parsing successful!")
    print(f"Parsed {len(result)} paragraphs")
    for i, para in enumerate(result):
        print(f"  Paragraph {i+1}: {para['text'][:50]}...")
except (ValueError, SyntaxError) as e:
    print(f"❌ AST parsing failed: {e}")
    print(f"Error type: {type(e).__name__}")
    
    # Let's analyze character by character around the problematic area
    print("\nAnalyzing the string character by character...")
    
    # Find the position of the problematic text
    problem_pos = paragraph_data_str.find("JPMorgan Chase did not assume First Republic Bank")
    if problem_pos != -1:
        start = max(0, problem_pos - 20)
        end = min(len(paragraph_data_str), problem_pos + 100)
        segment = paragraph_data_str[start:end]
        print(f"Problematic segment: {repr(segment)}")
        
        # Show each character with its ASCII code
        print("Character analysis:")
        for i, char in enumerate(segment):
            if i > 50:  # Limit output
                break
            print(f"  {i:2d}: {repr(char):4s} (ord: {ord(char):3d})")

# Test alternative parsing methods
print("\n" + "="*50)
print("Testing alternative parsing methods...")

# Try JSON parsing
import json
try:
    # Convert single quotes to double quotes for JSON
    json_str = paragraph_data_str.replace("'", '"')
    result = json.loads(json_str)
    print("✅ JSON parsing successful!")
except json.JSONDecodeError as e:
    print(f"❌ JSON parsing failed: {e}")

# Try eval (unsafe but for debugging)
try:
    result = eval(paragraph_data_str)
    print("✅ eval() parsing successful!")
except Exception as e:
    print(f"❌ eval() parsing failed: {e}")

# Test with manual escape fixing
print("\n" + "="*50)
print("Testing with escape fixing...")

# Try fixing the escape sequence
fixed_str = paragraph_data_str.replace("\\'", "'")
print("Fixed string sample:", repr(fixed_str[400:600]))

try:
    result = ast.literal_eval(fixed_str)
    print("✅ AST parsing with escape fix successful!")
except Exception as e:
    print(f"❌ AST parsing with escape fix failed: {e}")

# Try double-escaping
double_escaped_str = paragraph_data_str.replace("\\", "\\\\")
print("Double escaped sample:", repr(double_escaped_str[400:600]))

try:
    result = ast.literal_eval(double_escaped_str)
    print("✅ AST parsing with double escape successful!")
except Exception as e:
    print(f"❌ AST parsing with double escape failed: {e}")
