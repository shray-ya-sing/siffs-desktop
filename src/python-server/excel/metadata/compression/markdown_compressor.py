from typing import Tuple, Dict, Any, Optional
from openpyxl.utils import get_column_letter

class SpreadsheetMarkdownCompressor:
    """
    Python class for compressing json metadata into spreadsheet style markdown with dependency information
    """
    def __init__(self, workbook_path: Optional[str] = None):
        """
        Initialize the markdown compressor.        
        """
        self.has_display_values = False
        self.has_dependencies = False

    def compress_to_markdown(self, metadata_tuple: Tuple[Dict[str, Any], Optional[Dict[str, str]]], output_path: Optional[str] = r'C:\Users\shrey\OneDrive\Desktop\cori outputs\appTest.txt') -> str:
        """
        Compress the metadata passed as arg into spreadsheet-style markdown for LLM analysis.
        
        Args:
            metadata_tuple: Tuple of the OpenPyxl metadata and optional Xlwings extracted display values                
            output_path: Optional path to save markdown file
        
        Returns:
            Markdown string with spreadsheet-style layout including dependency information
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

        # Check if dependencies are included
        self.has_dependencies = metadata.get('includeDependencies', False)

        markdown_lines = []
        markdown_lines.append(f"# Workbook: {metadata.get('workbookName', '')}")
        markdown_lines.append(f"Active Sheet: {metadata.get('activeSheet', '')} | Total Sheets: {metadata.get('totalSheets', 0)}")
        
        for sheet in metadata.get("sheets", []):
            if sheet.get("isEmpty", True):
                continue
                
            markdown_lines.append(f"## Sheet: {sheet.get('name', '')} ({sheet.get('rowCount', 0)}x{sheet.get('columnCount', 0)})")
            
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
            
            # Compress tables and named ranges into single lines
            tables = sheet.get("tables", [])
            if tables:
                table_list = [f"{table.get('tableName', table.get('name', ''))}({table.get('tableRange', table.get('range', ''))})" for table in tables]
                markdown_lines.append(f"**Tables:** {', '.join(table_list)}")
            
            named_ranges = sheet.get("namedRanges", [])
            if named_ranges:
                nr_list = [f"{nr.get('rangeName', nr.get('name', ''))}:{nr.get('rangeReference', nr.get('value', ''))}" for nr in named_ranges]
                markdown_lines.append(f"**Named Ranges:** {', '.join(nr_list)}")
        
        markdown_string = "\n".join(markdown_lines)

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_string)
            print(f"Metadata saved to: {output_path}")

        return markdown_string

    def _format_cell_for_spreadsheet(self, cell: Dict[str, Any], display_value: Optional[str] = None) -> str:
        """
        Format cell data with critical available properties for spreadsheet-style display,
        now including dependency information.
        
        Args:
            cell: Cell metadata dictionary
            display_value: Optional display value from xlwings (what user sees)
            
        Returns:
            Formatted string with critical cell properties including dependencies
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
                return ''  # Empty instead of 'null'
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

        def _format_dependency_list(dep_list: list, max_items: int = 3) -> str:
            """Format a list of dependencies for compact display"""
            if not dep_list:
                return ""
            
            # Show first few items, indicate if there are more
            displayed = dep_list[:max_items]
            result = ",".join(displayed)
            
            if len(dep_list) > max_items:
                result += f",+{len(dep_list) - max_items}more"
            
            return result

        try:
            properties = []
            
            # Cell location information (always first) - use shortened format
            row = cell.get("row", "")
            col = cell.get("column", "")
            address = cell.get("address", f"{get_column_letter(col)}{row}" if col and row else "")
            
            if address:
                properties.append(f'{address}')  # Remove 'addr=' prefix
            
            # Raw value - skip if null/empty
            raw_value = cell.get("value", "")
            if raw_value is not None and str(raw_value).strip():
                properties.append(f'v={_safe_format_value(str(raw_value))}')  # Shortened 'val=' to 'v='
            
            # Display value (from xlwings) - only include if provided and different
            if display_value is not None and str(display_value) != str(raw_value):
                properties.append(f'd={_safe_format_value(display_value)}')  # Shortened 'disp=' to 'd='
            
            # Formula (if present)
            formula = cell.get("formula")
            if formula and formula.startswith("="):
                # Truncate long formulas
                formula_display = formula[:30] + "..." if len(formula) > 30 else formula
                properties.append(f'f={_safe_format_value(formula_display)}')  # Shortened 'form=' to 'f='
            
            # Dependency information (if dependencies are included)
            if self.has_dependencies:
                precedent_count = cell.get("precedentCount", 0)
                dependent_count = cell.get("dependentCount", 0)
                total_connections = cell.get("totalConnections", 0)
                
                # Include counts if there are any connections
                if total_connections > 0:
                    properties.append(f'deps={precedent_count}→{dependent_count}')
                    
                    # Include actual precedents/dependents for high-value cells
                    if precedent_count > 0 and precedent_count <= 5:
                        precedents = cell.get("directPrecedents", [])
                        precedents_str = _format_dependency_list(precedents, 3)
                        if precedents_str:
                            properties.append(f'prec=[{precedents_str}]')
                    elif precedent_count > 5:
                        properties.append(f'prec=[{precedent_count}refs]')
                    
                    if dependent_count > 0 and dependent_count <= 3:
                        dependents = cell.get("directDependents", [])
                        dependents_str = _format_dependency_list(dependents, 2)
                        if dependents_str:
                            properties.append(f'dept=[{dependents_str}]')
                    elif dependent_count > 3:
                        properties.append(f'dept=[{dependent_count}refs]')
            
            # Significant formatting (only if present) - Remove default/empty formatting
            formatting = cell.get("formatting", {})
            if self._has_significant_formatting(formatting):
                format_parts = []
                
                # Font formatting
                font = formatting.get("font", {})
                if font.get("bold"):
                    format_parts.append("bold")
                if font.get("italic"):
                    format_parts.append("italic")
                font_color = font.get("color")
                if font_color and font_color not in [None, "auto", "#000000", "#00000000"]:  # Skip default/empty colors
                    format_parts.append(f"color:{font_color}")
                
                # Fill formatting - Skip default/empty fills
                fill = formatting.get("fill", {})
                fill_color = fill.get("startColor")
                if fill_color and fill_color not in [None, "auto", "#FFFFFF", "#00000000", "FFFFFF"]:
                    format_parts.append(f"fill:{fill_color}")
                
                # Borders
                borders = formatting.get("borders", {})
                border_styles = []
                for side, border in borders.items():
                    if isinstance(border, dict) and border.get("style"):
                        border_styles.append(side[:1])  # Just first letter (l,r,t,b)
                if border_styles:
                    format_parts.append(f"border:{''.join(border_styles)}")
                
                # Number format
                num_format = formatting.get("numberFormat", "")
                if num_format and num_format.lower() not in ["general", "@"]:
                    format_parts.append(f"fmt:{num_format[:10]}")
                
                # Merged cells
                merged = formatting.get("merged", {})
                if merged.get("isMerged"):
                    format_parts.append("merged")
                
                if format_parts:
                    properties.append(f'fmt=[{",".join(format_parts)}]')
            
            # Data type (only if not default string)
            data_type = formatting.get("dataType", "") if formatting else ""
            if data_type and data_type not in ["n", "", "s"]:  # Skip default types
                properties.append(f'type={data_type}')
            
            # Comments (if present)
            if formatting and formatting.get("comment"):
                comment_text = formatting["comment"].get("text", "")[:20]
                if comment_text:
                    properties.append(f'comment={_safe_format_value(comment_text)}')
            
            # Hyperlinks (if present)
            if formatting and formatting.get("hyperlink"):
                hyperlink_target = formatting["hyperlink"].get("target", "")[:30]
                if hyperlink_target:
                    properties.append(f'link={_safe_format_value(hyperlink_target)}')
            
            return ", ".join(properties) if properties else ""
                
        except Exception as e:
            return f"ERROR: {str(e)[:30]}"

    def _is_significant_cell(self, cell: Dict[str, Any]) -> bool:
        """
        Determine if a cell has significant data worth including.
        Now includes cells with dependencies even if empty.
        
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
        
        # Include if has dependencies (new condition)
        if self.has_dependencies:
            total_connections = cell.get("totalConnections", 0)
            if total_connections > 0:
                return True
        
        # Include if has significant formatting (even if empty)
        if self._has_significant_formatting(formatting):
            return True
        
        return False

    def _has_significant_formatting(self, formatting: Dict[str, Any]) -> bool:
        """Check if formatting is significant enough to include - filters out defaults/empty"""
        try:
            # Check font formatting
            font = formatting.get("font", {})
            if (font.get("bold") or font.get("italic") or 
                font.get("underline") != "none" or font.get("strikethrough") or
                font.get("vertAlign") or (font.get("size") and font.get("size") != 11) or
                (font.get("name") and font.get("name") != "Calibri")):
                return True
            
            # Check font color (skip defaults)
            font_color = font.get("color")
            if font_color and font_color not in [None, "auto", "#000000", "#00000000"]:
                return True
            
            # Check fill formatting (skip defaults/empty)
            fill = formatting.get("fill", {})
            fill_color = fill.get("startColor")
            if (fill_color and fill_color not in [None, "auto", "#FFFFFF", "#00000000", "FFFFFF"] or 
                fill.get("endColor") or fill.get("fillType") != "none" or fill.get("patternType")):
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
            
            # Check data type (skip defaults)
            data_type = formatting.get("dataType", "")
            if data_type and data_type not in ["n", "", "s"]:
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