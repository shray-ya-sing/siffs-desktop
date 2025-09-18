# Siffs - Fast File Search Desktop Application
# Copyright (C) 2025  Siffs
# 
# Contact: github.suggest277@passinbox.com
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
import os
import sys
from pathlib import Path

def find_non_ascii_chars(directory):
    """
    Recursively search through .py files in the given directory
    and report any non-ASCII characters found.
    """
    root_dir = Path(directory)
    results = []
    
    for py_file in root_dir.rglob('*.py'):
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    # Check each character in the line
                    for col_num, char in enumerate(line, 1):
                        # Skip ASCII characters (0-127)
                        if ord(char) > 127:
                            results.append((
                                str(py_file.relative_to(root_dir)),
                                line_num,
                                col_num,
                                char,
                                repr(char),
                                line.strip()
                            ))
        except UnicodeDecodeError:
            results.append((str(py_file.relative_to(root_dir)), 
                          "ERROR", "ERROR", 
                          "Could not decode file", "", ""))
    
    return results

def print_results(results):
    """Print the results in a readable format."""
    if not results:
        print("No non-ASCII characters found.")
        return
    
    print(f"Found {len(results)} non-ASCII characters:")
    print("-" * 80)
    for file_path, line_num, col_num, char, char_repr, line in results:
        print(f"File: {file_path}")
        print(f"Line: {line_num}, Column: {col_num}")
        print(f"Character: {char_repr} (U+{ord(char):04x})")
        print(f"Context: {line[:col_num-1]}>>>{char}<<<{line[col_num:].rstrip()}")
        print("-" * 80)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python find_non_ascii.py <directory>")
        sys.exit(1)
    
    directory = sys.argv[1]
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        sys.exit(1)
    
    results = find_non_ascii_chars(directory)
    print_results(results)