#!/usr/bin/env python
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.append('.')
sys.path.append(str(Path(__file__).parent))

from ai_services.tools.read_write_functions.word.word_edit_tools import parse_word_markdown
import json

def test_parse_word_markdown():
    test_input = '''page_1| paragraph1, font_col="#000000", b="true", i="false", u="false", s="false", font="Calibri", sz="14" | paragraph2, font_col="#333333", b="false", i="true", u="false", s="false", font="Arial", sz="12"'''
    
    print("Testing Word markdown parser...")
    print(f"Input: {test_input}")
    print()
    
    result = parse_word_markdown(test_input)
    if result:
        print("Parse test successful!")
        print("Parsed result:")
        print(json.dumps(result, indent=2))
        return True
    else:
        print("Parse test failed!")
        return False

if __name__ == "__main__":
    test_parse_word_markdown()
