from typing import Tuple, Dict, Any, Optional
from openpyxl.utils import get_column_letter

class SpreadsheetMarkdownCompressor:
    """
    Python class for compressing json metadata into spreadsheet style markdown
    """
    def __init__(self, workbook_path: Optional[str] = None):
        """
        Initialize the markdown compressor.        
        """
        self.has_display_values = False

    def compress_to_markdown(self, metadata_tuple: Tuple[Dict[str, Any], Optional[Dict[str, str]]], output_path: Optional[str] = r'C:\Users\shrey\OneDrive\Desktop\cori outputs\appTest.txt') -> str:
        """
        Compress the metadata passed as arg into spreadsheet-style markdown for LLM analysis.
        
        Args:
            metadata_tuple: Tuple of the OpenPyxl metadata and optional Xlwings extracted display values                
            output_path: Optional path to save markdown file
        
        Returns:
            Markdown string with spreadsheet-style layout
        """
        # Unpack metadata and display values (which might be None)
        if isinstance(metadata_tuple, (list, tuple)) and len(metadata_tuple) >= 2:
            metadata, display_values = metadata_tuple
            self.has_display_values = bool(display_values)
        else:
            # Handle case where only metadata is provided
            metadata = metadata_tuple if not isinstance(metadata_tuple, (list, tuple)) else metadata_tuple[0]
            display_values = {}
            self.has_display_values = False

        markdown_lines = []
        markdown_lines.append(f"# Workbook: {metadata.get('workbookName', '')}")
        markdown_lines.append(f"Active Sheet: {metadata.get('activeSheet', '')}")
        markdown_lines.append(f"Total Sheets: {metadata.get('totalSheets', 0)}")
        markdown_lines.append("")
        
        for sheet in metadata.get("sheets", []):
            if sheet.get("isEmpty", True):
                continue
                
            markdown_lines.append(f"## Sheet: {sheet.get('name', '')}")
            markdown_lines.append(f"Dimensions: {sheet.get('rowCount', 0)} rows x {sheet.get('columnCount', 0)} columns")
            markdown_lines.append("")
            
            # Create spreadsheet-style table
            cell_data = sheet.get("cellData", [])
            if cell_data:
                # Create header row with column letters
                max_cols = len(cell_data[0]) if cell_data else 0
                header_row = ["Row"] + [get_column_letter(i+1) for i in range(max_cols)]
                markdown_lines.append("| " + " | ".join(header_row) + " |")
                markdown_lines.append("|" + "---|" * len(header_row))
                
                # Add data rows
                for row_idx, row_data in enumerate(cell_data):
                    row_cells = [str(row_idx + 1)]  # Row number
                    
                    for cell in row_data:
                        # Get display value from xlwings data if available
                        display_value = None
                        if self.has_display_values and display_values:
                            sheet_name = sheet.get('name', '')
                            cell_key = f"{sheet_name}_{cell.get('row')}_{cell.get('column')}"
                            display_value = display_values.get(cell_key)
                        
                        cell_content = self._format_cell_for_spreadsheet(cell, display_value)
                        row_cells.append(cell_content)
                    
                    markdown_lines.append("| " + " | ".join(row_cells) + " |")
            
            # Rest of the method remains the same...
            tables = sheet.get("tables", [])
            if tables:
                markdown_lines.append("")
                markdown_lines.append("### Tables:")
                for table in tables:
                    table_name = table.get("tableName", table.get("name", ""))
                    table_range = table.get("tableRange", table.get("range", ""))
                    headers = table.get("headers", [])
                    markdown_lines.append(f"- **{table_name}** ({table_range}): {', '.join(headers[:5])}")
            
            named_ranges = sheet.get("namedRanges", [])
            if named_ranges:
                markdown_lines.append("")
                markdown_lines.append("### Named Ranges:")
                for nr in named_ranges:
                    range_name = nr.get("rangeName", nr.get("name", ""))
                    range_ref = nr.get("rangeReference", nr.get("value", ""))
                    markdown_lines.append(f"- **{range_name}**: {range_ref}")
            
            markdown_lines.append("")
        
        markdown_string = "\n".join(markdown_lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_string)
            print(f"Metadata saved to: {output_path}")

        return markdown_string

    def _format_cell_for_spreadsheet(self, cell: Dict[str, Any], display_value: Optional[str] = None) -> str:
        """
        Format cell data with critical available properties for spreadsheet-style display.
        
        Args:
            cell: Cell metadata dictionary
            display_value: Optional display value from xlwings (what user sees)
            
        Returns:
            Formatted string with critical cell properties
        """
        def _safe_format_value(value: Any) -> str:
            """
            Safely format values for markdown without escaping - use quotes when needed.
            
            Args:
                value: Value to format
                
            Returns:
                Safely formatted value
            """
            if value is None:
                return 'null'
            if not isinstance(value, str):
                value = str(value)
            
            # Characters that might cause issues in markdown tables
            problematic_chars = ['#', '*', '_', '`', '[', ']', '(', ')', '|', '$', '^', '~', '\\', '"', "'"]
            
            # If value contains problematic characters, wrap in quotes
            if any(char in value for char in problematic_chars):
                # Escape any existing quotes in the value
                safe_value = value.replace('"', "'")  # Replace double quotes with single quotes
                return f'"{safe_value}"'
            
            return value

        try:
            properties = []
            
            # Cell location information (always first)
            row = cell.get("row", "")
            col = cell.get("column", "")
            address = cell.get("address", f"{get_column_letter(col)}{row}" if col and row else "")
            
            if address:
                properties.append(f'address={_safe_format_value(address)}')
            if row is not None:
                properties.append(f'row={_safe_format_value(row)}')
            if col is not None:
                properties.append(f'column={_safe_format_value(col)}')
            
            # Raw value (from openpyxl)
            raw_value = cell.get("value", "")
            if raw_value is not None and str(raw_value).strip():
                properties.append(f'raw_value={_safe_format_value(str(raw_value))}')
            else:
                properties.append('raw_value=null')
            
            # Display value (from xlwings) - only include if provided
            if display_value is not None:
                properties.append(f'display_value={_safe_format_value(display_value)}')
            
            # Rest of the method remains the same...
            # [Previous code for formatting, borders, etc.]
            
            return ", ".join(properties)
                
        except Exception as e:
            return f"ERROR: {str(e)[:30]}"

    def _is_significant_cell(self, cell: Dict[str, Any]) -> bool:
        """
        Determine if a cell has significant data worth including.
        Modified to include empty cells with formatting.
        
        Args:
            cell: Cell metadata dictionary
            
        Returns:
            True if cell should be included in compressed output
        """
        value = cell.get("value")
        formula = cell.get("formula")
        formatting = cell.get("formatting", {})
        
        # Include if has non-empty value
        if value is not None and str(value).strip() != "":
            return True
        
        # Include if has formula
        if formula and formula.startswith("="):
            return True
        
        # Include if has significant formatting (even if empty)
        if self._has_significant_formatting(formatting):
            return True
        
        return False

    def _has_significant_formatting(self, formatting: Dict[str, Any]) -> bool:
        """Check if formatting is significant enough to include - comprehensive version"""
        try:
            # Check font formatting
            font = formatting.get("font", {})
            if (font.get("bold") or font.get("italic") or font.get("color") or 
                font.get("underline") != "none" or font.get("strikethrough") or
                font.get("vertAlign") or (font.get("size") and font.get("size") != 11) or
                (font.get("name") and font.get("name") != "Calibri")):
                return True
            
            # Check fill formatting
            fill = formatting.get("fill", {})
            if (fill.get("startColor") or fill.get("endColor") or 
                fill.get("fillType") != "none" or fill.get("patternType")):
                return True
            
            # Check borders
            borders = formatting.get("borders", {})
            for border in borders.values():
                if isinstance(border, dict) and border.get("style"):
                    return True
            if borders.get("diagonalUp") or borders.get("diagonalDown") or borders.get("outline"):
                return True
            
            # Check alignment
            alignment = formatting.get("alignment", {})
            if (alignment.get("horizontal") or alignment.get("vertical") or
                alignment.get("wrapText") or alignment.get("shrinkToFit") or
                alignment.get("indent") != 0 or alignment.get("textRotation") != 0 or
                alignment.get("readingOrder") != 0 or alignment.get("justifyLastLine") or
                alignment.get("relativeIndent") != 0):
                return True
            
            # Check number format (if not general)
            number_format = formatting.get("numberFormat")
            if number_format and number_format.lower() not in ["general", "@"]:
                return True
            
            # Check protection
            protection = formatting.get("protection", {})
            if protection.get("locked") is False or protection.get("hidden"):
                return True
            
            # Check data type
            data_type = formatting.get("dataType", "")
            if data_type and data_type != "n":
                return True
            
            # Check merged cells
            merged = formatting.get("merged", {})
            if merged.get("isMerged"):
                return True
            
            # Check hyperlink
            if formatting.get("hyperlink"):
                return True
            
            # Check comment
            if formatting.get("comment"):
                return True
            
            return False
        except:
            return False


    def _escape_special_chars(self, text: str) -> str:
        """
        Escape special characters that could interfere with markdown parsing.
        
        Args:
            text: Text to escape
            
        Returns:
            Escaped text safe for markdown
        """
        if not isinstance(text, str):
            text = str(text)
        
        # Replace problematic characters
        replacements = {
            '#': '\\#',      # Markdown headers
            '*': '\\*',      # Markdown bold/italic
            '_': '\\_',      # Markdown italic/underline
            '`': '\\`',      # Markdown code
            '[': '\\[',      # Markdown links
            ']': '\\]',      # Markdown links
            '(': '\\(',      # Markdown links
            ')': '\\)',      # Markdown links
            '|': '\\|',      # Markdown tables
            '$': '\\$',      # LaTeX math
            '^': '\\^',      # Superscript
            '~': '\\~',      # Subscript
            '\\': '\\\\'     # Backslash
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
