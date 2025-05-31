import os
import json
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

# Handle import errors gracefully
try:
    import openpyxl
    from openpyxl.styles import Font, Fill, Border, Alignment
    from openpyxl.utils import get_column_letter
    OPENPYXL_AVAILABLE = True
except ImportError as e:
    OPENPYXL_AVAILABLE = False
    print(f"Warning: openpyxl import failed - Excel metadata extraction will not be available: {str(e)}")

try:
    import xlwings as xw
    XLWINGS_AVAILABLE = True
except ImportError:
    XLWINGS_AVAILABLE = False
    print("Warning: xlwings not available - display values will not be extracted")

class ExcelMetadataExtractor:
    def __init__(self, workbook_path: Optional[str] = None):
        """
        Initialize the metadata extractor with enhanced error handling.
        
        Args:
            workbook_path: Path to the Excel file (optional, can be set later)
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError("openpyxl is required but not installed. Please install with: pip install openpyxl")
            
        self.workbook_path = None
        self.workbook = None
        self.workbook_values = None
        self.xlwings_extractor = None
        self._initialize_xlwings()
        
        if workbook_path:
            self.open_workbook(workbook_path)

    def _initialize_xlwings(self) -> None:
        """Initialize xlwings extractor if available."""
        if not XLWINGS_AVAILABLE:
            print("Warning: xlwings not available - display values will not be extracted")
            return
            
        try:
            from .xlwings_extractor import XlwingsMetadataExtractor
            self.xlwings_extractor = XlwingsMetadataExtractor()
        except ImportError as e:
            print(f"Warning: Failed to initialize xlwings extractor: {str(e)}")
        except Exception as e:
            print(f"Warning: Unexpected error initializing xlwings: {str(e)}")
            print(traceback.format_exc())

    def open_workbook(self, workbook_path: Optional[str] = None) -> None:
        """Open the Excel workbook with comprehensive error handling."""
        try:
            if workbook_path:
                self.workbook_path = os.path.abspath(workbook_path)
                
            if not self.workbook_path:
                raise ValueError("No workbook path specified")
                
            if not os.path.exists(self.workbook_path):
                raise FileNotFoundError(f"Workbook not found: {self.workbook_path}")
                
            if not os.path.isfile(self.workbook_path):
                raise ValueError(f"Path is not a file: {self.workbook_path}")
                
            # Open workbooks with explicit error handling
            try:
                self.workbook = openpyxl.load_workbook(
                    self.workbook_path, 
                    data_only=False,
                    read_only=True,
                    keep_links=False
                )
            except Exception as e:
                raise RuntimeError(f"Failed to open workbook for formulas: {str(e)}")
                
            try:
                self.workbook_values = openpyxl.load_workbook(
                    self.workbook_path,
                    data_only=True,
                    read_only=True,
                    keep_links=False
                )
            except Exception as e:
                if self.workbook:
                    self.workbook.close()
                    self.workbook = None
                raise RuntimeError(f"Failed to open workbook for values: {str(e)}")
                
        except Exception as e:
            self.close()
            raise RuntimeError(f"Error opening workbook: {str(e)}") from e

    def close(self) -> None:
        """Safely close all open workbooks and clean up resources."""
        try:
            if self.workbook:
                self.workbook.close()
        except Exception as e:
            print(f"Warning: Error closing workbook: {str(e)}")
        finally:
            self.workbook = None
            
        try:
            if self.workbook_values:
                self.workbook_values.close()
        except Exception as e:
            print(f"Warning: Error closing values workbook: {str(e)}")
        finally:
            self.workbook_values = None

    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures resources are cleaned up."""
        self.close()
        return False  # Don't suppress exceptions

    def extract_workbook_metadata(
        self,
        workbook_path: Optional[str] = None,
        output_path: Optional[str] = None,
        max_rows_per_sheet: int = 100,
        max_cols_per_sheet: int = 50,
        include_display_values: bool = False
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Extract metadata with comprehensive error handling.
        """
        try:
            # Get metadata using openpyxl
            metadata = self.extract_workbook_metadata_openpyxl(
                workbook_path,
                max_rows_per_sheet,
                max_cols_per_sheet
            )
            
            # Get display values if requested and xlwings is available
            display_values = {}
            if include_display_values and self.xlwings_extractor:
                try:
                    display_values = self.xlwings_extractor._extract_display_values_xlwings(
                        workbook_path or self.workbook_path,
                        metadata
                    )
                except Exception as e:
                    print(f"Warning: Failed to extract display values: {str(e)}")
                    display_values = {"error": str(e)}
            
            return metadata, display_values
            
        except Exception as e:
            error_msg = f"Failed to extract workbook metadata: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            raise RuntimeError(error_msg) from e

    def extract_workbook_metadata_openpyxl(
        self,
        workbook_path: Optional[str] = None,
        max_rows_per_sheet: int = 100,
        max_cols_per_sheet: int = 50
    ) -> Dict[str, Any]:
        """
        Extract metadata using openpyxl with comprehensive error handling.
        """
        try:
            if workbook_path or not self.workbook:
                self.open_workbook(workbook_path)
                
            if not self.workbook:
                raise RuntimeError("Workbook is not open")
                
            # Get basic workbook info
            workbook_metadata = {
                "extractedAt": datetime.now().isoformat(),
                "workbookPath": self.workbook_path,
                "workbookName": os.path.basename(self.workbook_path) if self.workbook_path else "Unknown",
                "activeSheet": self.workbook.active.title if self.workbook.active else None,
                "totalSheets": len(self.workbook.worksheets),
                "sheetNames": [sheet.title for sheet in self.workbook.worksheets],
                "themeColors": self._get_theme_colors(),
                "sheets": []
            }
            
            # Extract metadata for each sheet
            for sheet in self.workbook.worksheets:
                try:
                    sheet_metadata = self._extract_sheet_metadata(
                        sheet,
                        max_rows_per_sheet,
                        max_cols_per_sheet
                    )
                    workbook_metadata["sheets"].append(sheet_metadata)
                except Exception as e:
                    error_msg = f"Error processing sheet '{sheet.title}': {str(e)}"
                    print(f"Warning: {error_msg}")
                    print(traceback.format_exc())
                    workbook_metadata["sheets"].append({
                        "name": sheet.title,
                        "error": error_msg,
                        "isEmpty": True
                    })
            
            return workbook_metadata
            
        except Exception as e:
            error_msg = f"Failed to extract workbook metadata: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            raise RuntimeError(error_msg) from e

    def _extract_sheet_metadata(
        self,
        sheet,
        max_rows: int,
        max_cols: int
    ) -> Dict[str, Any]:
        """
        Extract metadata from a single sheet with comprehensive error handling.
        """
        sheet_metadata = {
            "name": sheet.title,
            "error": None,
            "isEmpty": True,
            "rowCount": 0,
            "columnCount": 0,
            "cellData": [],
            "tables": [],
            "namedRanges": []
        }
        
        try:
            # Get actual dimensions
            actual_row_count = min(sheet.max_row or 0, 1048576)  # Excel max rows
            actual_col_count = min(sheet.max_column or 0, 16384)  # Excel max columns
            
            # Check if sheet is empty
            if actual_row_count == 0 or actual_col_count == 0:
                sheet_metadata["isEmpty"] = True
                return sheet_metadata
                
            sheet_metadata.update({
                "isEmpty": False,
                "rowCount": actual_row_count,
                "columnCount": actual_col_count,
                "extractedRowCount": min(actual_row_count, max_rows),
                "extractedColumnCount": min(actual_col_count, max_cols)
            })
            
            # Extract cell data
            try:
                sheet_metadata["cellData"] = self._extract_cell_data(
                    sheet,
                    sheet_metadata["extractedRowCount"],
                    sheet_metadata["extractedColumnCount"]
                )
            except Exception as e:
                sheet_metadata["error"] = f"Error extracting cell data: {str(e)}"
                print(f"Warning: {sheet_metadata['error']}")
                print(traceback.format_exc())
                sheet_metadata["cellData"] = []
            
            # Extract tables and named ranges
            try:
                sheet_metadata["tables"] = self._extract_tables_metadata(sheet)
            except Exception as e:
                sheet_metadata["error"] = sheet_metadata.get("error", "") + f" Tables: {str(e)}"
                print(f"Warning: Error extracting tables: {str(e)}")
                sheet_metadata["tables"] = []

            # TODO: Extract named ranges
            
            return sheet_metadata
            
        except Exception as e:
            error_msg = f"Critical error extracting sheet '{sheet.title}': {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            sheet_metadata.update({
                "error": error_msg,
                "isEmpty": True
            })
            return sheet_metadata

    def _extract_cell_data(
        self,
        sheet,
        row_count: int,
        col_count: int
    ) -> List[List[Dict[str, Any]]]:
        """
        Extract cell data with comprehensive error handling.
        """
        cell_data = []
        
        try:
            for row_idx in range(1, row_count + 1):
                row_data = []
                
                for col_idx in range(1, col_count + 1):
                    try:
                        cell = sheet.cell(row=row_idx, column=col_idx)
                        cell_metadata = self._extract_complete_cell_metadata(cell, row_idx, col_idx)
                        row_data.append(cell_metadata)
                    except Exception as e:
                        print(f"Warning: Error processing cell ({row_idx},{col_idx}): {str(e)}")
                        row_data.append({
                            "row": row_idx,
                            "column": col_idx,
                            "address": f"{get_column_letter(col_idx)}{row_idx}",
                            "error": str(e)
                        })
                
                cell_data.append(row_data)
                
        except Exception as e:
            print(f"Error extracting cell data: {str(e)}")
            print(traceback.format_exc())
            raise
            
        return cell_data

    def _extract_complete_cell_metadata(
        self,
        cell,
        row: int,
        col: int
    ) -> Dict[str, Any]:
        """
        Extract complete cell metadata with comprehensive error handling.
        """
        try:
            # Handle EmptyCell objects
            if hasattr(cell, '__class__') and cell.__class__.__name__ == 'EmptyCell':
                return {
                    "row": row,
                    "column": col,
                    "address": f"{get_column_letter(col)}{row}",
                    "value": None,
                    "formula": None,
                    "formatting": {}
                }
            # Get corresponding cell from values workbook
            value_sheet = self.workbook_values[cell.parent.title]
            value_cell = value_sheet.cell(row=row, column=col)
            
            cell_metadata = {
                "row": row,
                "column": col,
                "address": f"{get_column_letter(col)}{row}",
                "value": self._serialize_value(value_cell.value),
                "formula": self._get_cell_formula(cell),
                "formatting": self._extract_complete_cell_formatting(cell)
            }
            
            return cell_metadata
            
        except Exception as e:
            print(f"Error extracting metadata for cell ({row},{col}): {str(e)}")
            print(traceback.format_exc())
            return {
                "row": row,
                "column": col,
                "address": f"{get_column_letter(col)}{row}",
                "error": str(e)
            }

    def _get_cell_formula(self, cell) -> Optional[str]:
        """Safely get cell formula."""
        try:
            if hasattr(cell, 'value') and isinstance(cell.value, str) and cell.value.startswith('='):
                return cell.value
            return None
        except Exception:
            return None

    def _extract_complete_cell_formatting(self, cell) -> Dict[str, Any]:
        """
        Extract all cell formatting with comprehensive error handling.
        """
        formatting = {}
        
        try:
            # Font properties
            try:
                if cell.font:
                    formatting["font"] = {
                        "name": cell.font.name,
                        "size": cell.font.size,
                        "bold": cell.font.bold,
                        "italic": cell.font.italic,
                        "color": self._get_color_hex(cell.font.color),
                        "underline": cell.font.underline,
                        "strikethrough": cell.font.strikethrough,
                        "vertAlign": cell.font.vertAlign
                    }
            except Exception as e:
                formatting["font"] = {"error": str(e)}
                
            # Fill properties
            try:
                if cell.fill:
                    formatting["fill"] = {
                        "fillType": cell.fill.fill_type,
                        "startColor": self._get_color_hex(cell.fill.start_color),
                        "endColor": self._get_color_hex(cell.fill.end_color),
                        "patternType": cell.fill.patternType
                    }
            except Exception as e:
                formatting["fill"] = {"error": str(e)}
                
            # Number format
            try:
                formatting["numberFormat"] = cell.number_format
            except Exception as e:
                formatting["numberFormat"] = {"error": str(e)}
                
            # Alignment
            try:
                if cell.alignment:
                    formatting["alignment"] = {
                        "horizontal": cell.alignment.horizontal,
                        "vertical": cell.alignment.vertical,
                        "wrapText": cell.alignment.wrap_text,
                        "shrinkToFit": cell.alignment.shrink_to_fit,
                        "indent": cell.alignment.indent,
                        "textRotation": cell.alignment.text_rotation,
                        "readingOrder": cell.alignment.reading_order,
                        "justifyLastLine": cell.alignment.justify_last_line,
                        "relativeIndent": cell.alignment.relative_indent
                    }
            except Exception as e:
                formatting["alignment"] = {"error": str(e)}
                
            # Border properties
            try:
                if cell.border:
                    formatting["borders"] = {
                        "left": self._get_border_info(cell.border.left),
                        "right": self._get_border_info(cell.border.right),
                        "top": self._get_border_info(cell.border.top),
                        "bottom": self._get_border_info(cell.border.bottom),
                        "diagonal": self._get_border_info(cell.border.diagonal),
                        "diagonalUp": cell.border.diagonal_up,
                        "diagonalDown": cell.border.diagonal_down,
                        "outline": cell.border.outline,
                        "start": self._get_border_info(cell.border.start),
                        "end": self._get_border_info(cell.border.end)
                    }
            except Exception as e:
                formatting["borders"] = {"error": str(e)}
                
            # Protection
            try:
                if cell.protection:
                    formatting["protection"] = {
                        "locked": cell.protection.locked,
                        "hidden": cell.protection.hidden
                    }
            except Exception as e:
                formatting["protection"] = {"error": str(e)}
                
            # Comments
            try:
                if cell.comment:
                    formatting["comment"] = {
                        "text": cell.comment.text,
                        "author": cell.comment.author,
                        "width": cell.comment.width,
                        "height": cell.comment.height
                    }
            except Exception as e:
                formatting["comment"] = {"error": str(e)}
                
            # Hyperlink
            try:
                if cell.hyperlink:
                    formatting["hyperlink"] = {
                        "target": cell.hyperlink.target,
                        "tooltip": cell.hyperlink.tooltip,
                        "display": cell.hyperlink.display
                    }
            except Exception as e:
                formatting["hyperlink"] = {"error": str(e)}
                
            # Data type
            try:
                formatting["dataType"] = cell.data_type
            except Exception as e:
                formatting["dataType"] = {"error": str(e)}
                
            # Merged cells
            try:
                merged_ranges = cell.parent.merged_cells.ranges
                is_merged = False
                merge_range = None
                
                for merged_range in merged_ranges:
                    if cell.coordinate in merged_range:
                        is_merged = True
                        merge_range = str(merged_range)
                        break
                        
                formatting["merged"] = {
                    "isMerged": is_merged,
                    "mergeRange": merge_range
                }
            except Exception as e:
                formatting["merged"] = {"error": str(e)}
                
        except Exception as e:
            formatting["error"] = f"Error extracting formatting: {str(e)}"
            print(f"Warning: {formatting['error']}")
            print(traceback.format_exc())
            
        return formatting

    def _get_color_hex(self, color) -> Optional[str]:
        """Safely convert color to hex string."""
        if color is None:
            return None
        
        try:
            # Handle RGB object (newer openpyxl)
            if hasattr(color, 'rgb'):
                if hasattr(color, 'rgb') and color.rgb is not None:
                    # Handle RGB object directly
                    if hasattr(color.rgb, 'rgb'):
                        return f"#{color.rgb.rgb[2:]}"  # Skip alpha channel
                    # Handle string RGB
                    elif isinstance(color.rgb, str):
                        if color.rgb.startswith('FF'):
                            return f"#{color.rgb[2:]}"
                        return f"#{color.rgb}"
                return None
                
            # Handle indexed color
            if hasattr(color, 'indexed') and color.indexed is not None:
                return f"indexed_{color.indexed}"
                
            # Handle theme color
            if hasattr(color, 'theme') and color.theme is not None:
                return f"theme_{color.theme}"
                
            # Handle auto color
            if hasattr(color, 'auto') and color.auto:
                return "auto"
                
            return str(color)
        except Exception as e:
            print(f"Warning: Error converting color to hex: {str(e)}")
            return None

    def _get_border_info(self, border_side) -> Dict[str, Any]:
        """Safely get border information."""
        try:
            if not border_side:
                return {"style": None, "color": None}
                
            return {
                "style": border_side.style,
                "color": self._get_color_hex(border_side.color)
            }
        except Exception as e:
            print(f"Warning: Error getting border info: {str(e)}")
            return {"style": None, "color": None, "error": str(e)}

    def _serialize_value(self, value: Any) -> Any:
        """Safely serialize a cell value."""
        try:
            if value is None:
                return None
            elif isinstance(value, (str, int, float, bool)):
                return value
            elif hasattr(value, 'isoformat'):  # datetime objects
                return value.isoformat()
            else:
                return str(value)
        except Exception as e:
            print(f"Warning: Error serializing value: {str(e)}")
            return None

    def _extract_tables_metadata(self, sheet) -> List[Dict[str, Any]]:
        """Safely extract table metadata."""
        tables = []
        
        try:
            if not hasattr(sheet, 'tables'):
                return tables
                
            for table_name, table in sheet.tables.items():
                try:
                    table_data = {
                        "name": table_name,
                        "displayName": table.displayName,
                        "range": table.ref,
                        "tableStyleInfo": {
                            "name": table.tableStyleInfo.name if table.tableStyleInfo else None,
                            "showFirstColumn": table.tableStyleInfo.showFirstColumn if table.tableStyleInfo else None,
                            "showLastColumn": table.tableStyleInfo.showLastColumn if table.tableStyleInfo else None,
                            "showRowStripes": table.tableStyleInfo.showRowStripes if table.tableStyleInfo else None,
                            "showColumnStripes": table.tableStyleInfo.showColumnStripes if table.tableStyleInfo else None
                        }
                    }
                    
                    # Get column information
                    if hasattr(table, 'tableColumns'):
                        table_data["columns"] = []
                        for col in table.tableColumns:
                            table_data["columns"].append({
                                "name": col.name,
                                "id": col.id
                            })
                    
                    tables.append(table_data)
                    
                except Exception as e:
                    print(f"Warning: Error processing table {table_name}: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Error extracting tables: {str(e)}")
            print(traceback.format_exc())
            
        return tables

    def _extract_named_ranges(self, sheet) -> List[Dict[str, Any]]:
        """Safely extract named ranges."""
        named_ranges = []
        
        try:
            if not hasattr(self.workbook, 'defined_names') or not self.workbook.defined_names:
                return named_ranges
                
            # Handle both old and new openpyxl versions
            if hasattr(self.workbook.defined_names, 'definedName'):
                # Old openpyxl version
                names = self.workbook.defined_names.definedName
            else:
                # New openpyxl version - defined_names is already a dict-like object
                names = self.workbook.defined_names.values()
                
            for defined_name in names:
                try:
                    # Get the name and value, handling different openpyxl versions
                    name = defined_name.name if hasattr(defined_name, 'name') else defined_name
                    value = defined_name.value if hasattr(defined_name, 'value') else str(defined_name)
                    
                    if sheet.title in str(value):
                        named_range = {
                            "name": name,
                            "value": str(value)
                        }
                        
                        # Add optional fields if they exist
                        if hasattr(defined_name, 'localSheetId'):
                            named_range["localSheetId"] = defined_name.localSheetId
                        if hasattr(defined_name, 'hidden'):
                            named_range["hidden"] = defined_name.hidden
                            
                        named_ranges.append(named_range)
                        
                except Exception as e:
                    print(f"Warning: Error processing named range: {str(e)}")
                    continue
                    
        except Exception as e:
            print(f"Warning: Error extracting named ranges: {str(e)}")
            print(traceback.format_exc())
            
        return named_ranges

    def _get_theme_colors(self) -> Dict[str, str]:
        """Get theme colors with fallback to defaults."""
        try:
            # Try to get actual theme colors if available
            if hasattr(self.workbook, 'theme') and hasattr(self.workbook.theme, 'theme_elements'):
                # This is a simplified example - actual implementation would need to
                # extract colors from the theme XML
                pass
        except Exception as e:
            print(f"Warning: Error getting theme colors: {str(e)}")
        
        # Default theme colors (Office theme) as fallback
        return {
            "background1": "#FFFFFF",
            "background2": "#F2F2F2", 
            "text1": "#000000",
            "text2": "#666666",
            "accent1": "#4472C4",
            "accent2": "#ED7D31",
            "accent3": "#A5A5A5",
            "accent4": "#FFC000",
            "accent5": "#5B9BD5",
            "accent6": "#70AD47",
            "hyperlink": "#0563C1",
            "followedHyperlink": "#954F72"
        }

    def extract_to_json_str(
        self,
        workbook_path: Optional[str] = None,
        output_path: Optional[str] = None,
        max_rows_per_sheet: int = 100,
        max_cols_per_sheet: int = 50,
        **kwargs
    ) -> str:
        """
        Extract metadata and return as JSON string with comprehensive error handling.
        """
        try:
            # Extract metadata
            metadata, display_values = self.extract_workbook_metadata(
                workbook_path=workbook_path,
                max_rows_per_sheet=max_rows_per_sheet,
                max_cols_per_sheet=max_cols_per_sheet,
                **kwargs
            )
            
            # Prepare result
            result = {
                "metadata": metadata,
                "displayValues": display_values,
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
            # Convert to JSON
            json_str = json.dumps(result, indent=2, ensure_ascii=False)
            
            # Save to file if output path is provided
            if output_path:
                try:
                    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(json_str)
                    print(f"Metadata successfully saved to: {output_path}")
                except Exception as e:
                    raise IOError(f"Failed to write output file: {str(e)}")
                    
            return json_str
            
        except Exception as e:
            # Prepare error response
            error_msg = f"Failed to extract metadata to JSON: {str(e)}"
            print(error_msg)
            print(traceback.format_exc())
            
            error_result = {
                "metadata": None,
                "displayValues": None,
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            
            return json.dumps(error_result, indent=2)